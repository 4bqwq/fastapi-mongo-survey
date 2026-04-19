import pytest
from bson import ObjectId
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
    await db.users.delete_many({"username": "test_editor_user"})
    await db.questions.delete_many({})
    await db.surveys.delete_many({})
    yield
    await close_mongo_connection()


async def create_question(ac: AsyncClient, headers: dict, payload: dict) -> tuple[str, int]:
    response = await ac.post("/api/v1/questions", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    return data["question_id"], data["version"]


@pytest.mark.anyio
async def test_update_schema_polymorphism():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/v1/auth/register", json={"username": "test_editor_user", "password": "password"})
        login_resp = await ac.post("/api/v1/auth/login", json={"username": "test_editor_user", "password": "password"})
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        q1_id, q1_version = await create_question(
            ac,
            headers,
            {"type": "ChoiceQuestion", "title": "第1题", "options": ["A", "B"], "maxSelect": 2},
        )
        q2_id, q2_version = await create_question(
            ac,
            headers,
            {"type": "NumberQuestion", "title": "第2题", "minValue": 10.5, "maxValue": 100.0, "mustBeInteger": True},
        )
        q3_id, q3_version = await create_question(
            ac,
            headers,
            {"type": "TextQuestion", "title": "第3题", "minLength": 5, "maxLength": 500},
        )

        create_resp = await ac.post("/api/v1/surveys", json={"title": "Editor Test"}, headers=headers)
        survey_id = create_resp.json()["data"]["survey_id"]

        schema_payload = {
            "questions": [
                {"questionId": q1_id, "version": q1_version, "orderIndex": 1},
                {"questionId": q2_id, "version": q2_version, "orderIndex": 2},
                {"questionId": q3_id, "version": q3_version, "orderIndex": 3},
            ],
            "logic_rules": [
                {
                    "ruleId": "r1",
                    "sourceQuestionId": q1_id,
                    "targetQuestionId": q3_id,
                    "triggerCondition": "1",
                }
            ],
        }

        put_resp = await ac.put(f"/api/v1/surveys/{survey_id}/schema", json=schema_payload, headers=headers)
        assert put_resp.status_code == 200

        db = get_database()
        survey = await db.surveys.find_one({"_id": ObjectId(survey_id)})
        assert len(survey["questions"]) == 3

        q1 = next(q for q in survey["questions"] if q["questionId"] == q1_id)
        assert q1["version"] == q1_version
        assert q1["snapshot"]["type"] == "ChoiceQuestion"
        assert q1["snapshot"]["maxSelect"] == 2

        q2 = next(q for q in survey["questions"] if q["questionId"] == q2_id)
        assert q2["snapshot"]["minValue"] == 10.5
        assert q2["snapshot"]["mustBeInteger"] is True

        q3 = next(q for q in survey["questions"] if q["questionId"] == q3_id)
        assert q3["snapshot"]["title"] == "第3题"
        assert q3["snapshot"]["minLength"] == 5
        assert q3["snapshot"]["maxLength"] == 500

        assert len(survey["logicRules"]) == 1
        assert survey["logicRules"][0]["triggerCondition"] == "1"

        invalid_resp = await ac.put(
            f"/api/v1/surveys/{survey_id}/schema",
            json={
                "questions": [
                    {"questionId": q1_id, "version": q1_version, "orderIndex": 1},
                    {"questionId": q3_id, "version": q3_version, "orderIndex": 2},
                ],
                "logic_rules": [
                    {
                        "ruleId": "r2",
                        "sourceQuestionId": q1_id,
                        "targetQuestionId": q3_id,
                        "triggerCondition": "1 1",
                    }
                ],
            },
            headers=headers,
        )
        assert invalid_resp.status_code == 422
        assert "重复行号" in invalid_resp.json()["detail"]["message"]
