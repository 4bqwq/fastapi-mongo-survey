import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from bson import ObjectId

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="module", autouse=True)
async def manage_db():
    await connect_to_mongo()
    db = get_database()
    await db.users.delete_many({"username": "test_editor_user"})
    await db.surveys.delete_many({})
    yield
    await close_mongo_connection()

@pytest.mark.anyio
async def test_update_schema_polymorphism():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Setup user and survey
        await ac.post("/api/v1/auth/register", json={"username": "test_editor_user", "password": "password"})
        login_resp = await ac.post("/api/v1/auth/login", json={"username": "test_editor_user", "password": "password"})
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        create_resp = await ac.post("/api/v1/surveys", json={"title": "Editor Test"}, headers=headers)
        survey_id = create_resp.json()["data"]["survey_id"]
        
        # 2. Update schema with multiple question types
        schema_payload = {
            "questions": [
                {
                    "questionId": "q1",
                    "type": "ChoiceQuestion",
                    "title": "第1题",
                    "orderIndex": 1,
                    "options": ["A", "B"],
                    "maxSelect": 2
                },
                {
                    "questionId": "q2",
                    "type": "NumberQuestion",
                    "title": "第2题",
                    "orderIndex": 2,
                    "minValue": 10.5,
                    "maxValue": 100.0,
                    "mustBeInteger": True
                },
                {
                    "questionId": "q3",
                    "type": "TextQuestion",
                    "title": "第3题",
                    "orderIndex": 3,
                    "minLength": 5,
                    "maxLength": 500
                }
            ],
            "logic_rules": [
                {
                    "ruleId": "r1",
                    "sourceQuestionId": "q1",
                    "targetQuestionId": "q3",
                    "triggerCondition": "1"
                }
            ]
        }
        
        put_resp = await ac.put(f"/api/v1/surveys/{survey_id}/schema", json=schema_payload, headers=headers)
        assert put_resp.status_code == 200
        
        # 3. Verify in MongoDB
        db = get_database()
        survey = await db.surveys.find_one({"_id": ObjectId(survey_id)})
        assert len(survey["questions"]) == 3
        
        q1 = next(q for q in survey["questions"] if q["questionId"] == "q1")
        assert q1["maxSelect"] == 2
        assert q1["type"] == "ChoiceQuestion"
        
        q2 = next(q for q in survey["questions"] if q["questionId"] == "q2")
        assert q2["minValue"] == 10.5
        assert q2["mustBeInteger"] is True
        
        q3 = next(q for q in survey["questions"] if q["questionId"] == "q3")
        assert q3["title"] == "第3题"
        assert q3["minLength"] == 5
        assert q3["maxLength"] == 500
        
        assert len(survey["logicRules"]) == 1
        assert survey["logicRules"][0]["triggerCondition"] == "1"

        invalid_schema_payload = {
            "questions": [
                {
                    "questionId": "q1",
                    "type": "ChoiceQuestion",
                    "title": "第1题",
                    "orderIndex": 1,
                    "options": ["A", "B"],
                    "maxSelect": 2
                },
                {
                    "questionId": "q2",
                    "type": "TextQuestion",
                    "title": "第2题",
                    "orderIndex": 2
                }
            ],
            "logic_rules": [
                {
                    "ruleId": "r2",
                    "sourceQuestionId": "q1",
                    "targetQuestionId": "q2",
                    "triggerCondition": "1 1"
                }
            ]
        }
        invalid_resp = await ac.put(f"/api/v1/surveys/{survey_id}/schema", json=invalid_schema_payload, headers=headers)
        assert invalid_resp.status_code == 422
        assert "重复行号" in invalid_resp.json()["detail"]["message"]
