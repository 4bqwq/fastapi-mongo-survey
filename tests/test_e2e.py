import pytest
from httpx import AsyncClient, ASGITransport

from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.main import app


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module", autouse=True)
async def manage_db():
    await connect_to_mongo()
    db = get_database()
    await db.users.delete_many({"username": {"$in": ["e2e_owner", "e2e_filler_a", "e2e_filler_b"]}})
    await db.questions.delete_many({})
    await db.surveys.delete_many({})
    await db.answers.delete_many({})
    yield
    await close_mongo_connection()


async def register_and_login(client: AsyncClient, username: str, password: str) -> str:
    await client.post("/api/v1/auth/register", json={"username": username, "password": password})
    login_resp = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert login_resp.status_code == 200
    return login_resp.json()["data"]["access_token"]


async def create_question(client: AsyncClient, headers: dict, payload: dict) -> tuple[str, int]:
    response = await client.post("/api/v1/questions", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    return data["question_id"], data["version"]


@pytest.mark.anyio
async def test_e2e_full_user_path():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        owner_token = await register_and_login(client, "e2e_owner", "password123")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}

        q1_id, q1_version = await create_question(
            client,
            owner_headers,
            {"type": "ChoiceQuestion", "title": "流程选择", "isRequired": True, "options": ["直接填写数字题", "继续填写文本题"], "minSelect": 1, "maxSelect": 1},
        )
        q2_id, q2_version = await create_question(
            client,
            owner_headers,
            {"type": "TextQuestion", "title": "文本反馈", "isRequired": True, "minLength": 2, "maxLength": 20},
        )
        q3_id, q3_version = await create_question(
            client,
            owner_headers,
            {"type": "NumberQuestion", "title": "数字评分", "isRequired": True, "minValue": 1, "maxValue": 5, "mustBeInteger": False},
        )

        create_resp = await client.post(
            "/api/v1/surveys",
            json={"title": "E2E 问卷", "description": "覆盖完整用户路径", "is_anonymous": True, "end_time": "2030-12-31T23:59:59Z"},
            headers=owner_headers,
        )
        assert create_resp.status_code == 200
        survey_id = create_resp.json()["data"]["survey_id"]

        schema_resp = await client.put(
            f"/api/v1/surveys/{survey_id}/schema",
            json={
                "questions": [
                    {"questionId": q1_id, "version": q1_version, "orderIndex": 1},
                    {"questionId": q2_id, "version": q2_version, "orderIndex": 2},
                    {"questionId": q3_id, "version": q3_version, "orderIndex": 3},
                ],
                "logic_rules": [{"ruleId": "r1", "sourceQuestionId": q1_id, "targetQuestionId": q3_id, "triggerCondition": "1"}],
            },
            headers=owner_headers,
        )
        assert schema_resp.status_code == 200

        publish_resp = await client.patch(f"/api/v1/surveys/{survey_id}/status", json={"status": "PUBLISHED"}, headers=owner_headers)
        assert publish_resp.status_code == 200

        filler_a_token = await register_and_login(client, "e2e_filler_a", "password123")
        filler_a_headers = {"Authorization": f"Bearer {filler_a_token}"}
        fill_a_resp = await client.post(
            f"/api/v1/surveys/{survey_id}/answers",
            json={"submit_as_anonymous": True, "payloads": {q1_id: ["直接填写数字题"], q3_id: 3.5}},
            headers=filler_a_headers,
        )
        assert fill_a_resp.status_code == 200

        filler_b_token = await register_and_login(client, "e2e_filler_b", "password123")
        filler_b_headers = {"Authorization": f"Bearer {filler_b_token}"}
        fill_b_resp = await client.post(
            f"/api/v1/surveys/{survey_id}/answers",
            json={"payloads": {q1_id: ["继续填写文本题"], q2_id: "很好", q3_id: 4.0}},
            headers=filler_b_headers,
        )
        assert fill_b_resp.status_code == 200

        stats_resp = await client.get(f"/api/v1/surveys/{survey_id}/statistics", headers=owner_headers)
        assert stats_resp.status_code == 200
        stats = stats_resp.json()["data"]

        assert stats["macro_stats"]["total_respondents"] == 2
        assert stats["micro_stats"][q1_id]["distribution"]["直接填写数字题"] == 1
        assert stats["micro_stats"][q1_id]["distribution"]["继续填写文本题"] == 1
        assert stats["micro_stats"][q2_id]["text_list"] == ["很好"]
        assert stats["micro_stats"][q2_id]["total_answers"] == 1
        assert stats["micro_stats"][q3_id]["average_value"] == 3.75
        assert stats["micro_stats"][q3_id]["valid_answers"] == 2
        assert stats["micro_stats"][q3_id]["text_list"] == ["3.5", "4.0"]
