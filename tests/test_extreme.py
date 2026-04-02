import asyncio

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.database import connect_to_mongo, close_mongo_connection, get_database


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module", autouse=True)
async def manage_db():
    await connect_to_mongo()
    db = get_database()
    await db.users.delete_many(
        {"username": {"$in": ["edge_owner", "pressure_owner", "pressure_filler"]}}
    )
    await db.surveys.delete_many({})
    await db.answers.delete_many({})
    yield
    await close_mongo_connection()


async def register_and_login(client: AsyncClient, username: str, password: str) -> str:
    await client.post("/api/v1/auth/register", json={"username": username, "password": password})
    login_resp = await client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert login_resp.status_code == 200
    return login_resp.json()["data"]["access_token"]


@pytest.mark.anyio
async def test_boundary_values_are_accepted():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        token = await register_and_login(client, "edge_owner", "password123")
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await client.post("/api/v1/surveys", json={"title": "Boundary Survey"}, headers=headers)
        assert create_resp.status_code == 200
        survey_id = create_resp.json()["data"]["survey_id"]

        schema_resp = await client.put(
            f"/api/v1/surveys/{survey_id}/schema",
            json={
                "questions": [
                    {
                        "questionId": "q1",
                        "type": "ChoiceQuestion",
                        "title": "多选边界题",
                        "orderIndex": 1,
                        "isRequired": True,
                        "options": ["A", "B", "C"],
                        "minSelect": 2,
                        "maxSelect": 3,
                    },
                    {
                        "questionId": "q2",
                        "type": "TextQuestion",
                        "title": "文本边界题",
                        "orderIndex": 2,
                        "isRequired": True,
                        "minLength": 2,
                        "maxLength": 4,
                    },
                    {
                        "questionId": "q3",
                        "type": "NumberQuestion",
                        "title": "数字边界题",
                        "orderIndex": 3,
                        "isRequired": True,
                        "minValue": 1.5,
                        "maxValue": 9.5,
                        "mustBeInteger": False,
                    },
                ],
                "logic_rules": [],
            },
            headers=headers,
        )
        assert schema_resp.status_code == 200

        publish_resp = await client.patch(
            f"/api/v1/surveys/{survey_id}/status",
            json={"status": "PUBLISHED"},
            headers=headers,
        )
        assert publish_resp.status_code == 200

        min_boundary_resp = await client.post(
            f"/api/v1/surveys/{survey_id}/answers",
            json={"payloads": {"q1": ["A", "B"], "q2": "边界", "q3": 1.5}},
            headers=headers,
        )
        assert min_boundary_resp.status_code == 200

        max_boundary_resp = await client.post(
            f"/api/v1/surveys/{survey_id}/answers",
            json={"payloads": {"q1": ["A", "B", "C"], "q2": "四字文本", "q3": 9.5}},
            headers=headers,
        )
        assert max_boundary_resp.status_code == 200


@pytest.mark.anyio
async def test_concurrent_submissions_keep_statistics_consistent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        owner_token = await register_and_login(client, "pressure_owner", "password123")
        filler_token = await register_and_login(client, "pressure_filler", "password123")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        filler_headers = {"Authorization": f"Bearer {filler_token}"}

        create_resp = await client.post("/api/v1/surveys", json={"title": "Pressure Survey"}, headers=owner_headers)
        assert create_resp.status_code == 200
        survey_id = create_resp.json()["data"]["survey_id"]

        schema_resp = await client.put(
            f"/api/v1/surveys/{survey_id}/schema",
            json={
                "questions": [
                    {
                        "questionId": "q1",
                        "type": "ChoiceQuestion",
                        "title": "二选一",
                        "orderIndex": 1,
                        "isRequired": True,
                        "options": ["A", "B"],
                        "minSelect": 1,
                        "maxSelect": 1,
                    },
                    {
                        "questionId": "q2",
                        "type": "NumberQuestion",
                        "title": "评分",
                        "orderIndex": 2,
                        "isRequired": True,
                        "minValue": 0,
                        "maxValue": 100,
                        "mustBeInteger": False,
                    },
                    {
                        "questionId": "q3",
                        "type": "TextQuestion",
                        "title": "意见",
                        "orderIndex": 3,
                        "isRequired": True,
                        "minLength": 2,
                        "maxLength": 20,
                    },
                ],
                "logic_rules": [],
            },
            headers=owner_headers,
        )
        assert schema_resp.status_code == 200

        publish_resp = await client.patch(
            f"/api/v1/surveys/{survey_id}/status",
            json={"status": "PUBLISHED"},
            headers=owner_headers,
        )
        assert publish_resp.status_code == 200

        async def submit_one(index: int):
            payload = {
                "q1": ["A"] if index % 2 == 0 else ["B"],
                "q2": float(index),
                "q3": f"反馈{index}",
            }
            return await client.post(
                f"/api/v1/surveys/{survey_id}/answers",
                json={"payloads": payload},
                headers=filler_headers,
            )

        total_submissions = 60
        responses = await asyncio.gather(*(submit_one(i) for i in range(1, total_submissions + 1)))
        assert all(response.status_code == 200 for response in responses)

        stats_resp = await client.get(f"/api/v1/surveys/{survey_id}/statistics", headers=owner_headers)
        assert stats_resp.status_code == 200
        data = stats_resp.json()["data"]

        assert data["macro_stats"]["total_respondents"] == total_submissions

        q1_stats = data["micro_stats"]["q1"]
        assert q1_stats["distribution"]["A"] == total_submissions // 2
        assert q1_stats["distribution"]["B"] == total_submissions // 2

        q2_stats = data["micro_stats"]["q2"]
        assert q2_stats["valid_answers"] == total_submissions
        assert q2_stats["average_value"] == 30.5
        assert len(q2_stats["text_list"]) == 50
        numeric_details = {float(value) for value in q2_stats["text_list"]}
        assert len(numeric_details) == 50
        assert numeric_details.issubset({float(i) for i in range(1, total_submissions + 1)})

        q3_stats = data["micro_stats"]["q3"]
        assert q3_stats["total_answers"] == 20
        assert len(q3_stats["text_list"]) == 20
        assert all(item.startswith("反馈") for item in q3_stats["text_list"])
