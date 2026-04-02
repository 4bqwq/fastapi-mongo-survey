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
    await db.users.delete_many({"username": "test_filler"})
    await db.surveys.delete_many({})
    await db.answers.delete_many({})
    yield
    await close_mongo_connection()

@pytest.mark.anyio
async def test_filling_validation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Setup user and published survey
        await ac.post("/api/v1/auth/register", json={"username": "test_filler", "password": "password"})
        login_resp = await ac.post("/api/v1/auth/login", json={"username": "test_filler", "password": "password"})
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        create_resp = await ac.post("/api/v1/surveys", json={"title": "Fill Test"}, headers=headers)
        survey_id = create_resp.json()["data"]["survey_id"]
        
        # Add questions: q1(Required), q2(Number 1-10)
        schema = {
            "questions": [
                {"questionId": "q1", "type": "TextQuestion", "orderIndex": 1, "isRequired": True, "title": "Req Q"},
                {"questionId": "q2", "type": "NumberQuestion", "orderIndex": 2, "isRequired": False, "minValue": 1, "maxValue": 10, "title": "Num Q"}
            ],
            "logic_rules": []
        }
        await ac.put(f"/api/v1/surveys/{survey_id}/schema", json=schema, headers=headers)
        
        # Must publish first
        await ac.patch(f"/api/v1/surveys/{survey_id}/status", json={"status": "PUBLISHED"}, headers=headers)

        # 2. Submit with missing required question
        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {"q2": 5}}, headers=headers)
        assert resp.status_code == 422
        assert "必答题" in resp.json()["detail"]["message"]

        # 3. Submit with number out of range
        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {"q1": "hello", "q2": 15}}, headers=headers)
        assert resp.status_code == 422
        assert "值过大" in resp.json()["detail"]["message"]

        # 4. Successful submission
        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {"q1": "hello", "q2": 5}}, headers=headers)
        assert resp.status_code == 200
        assert "answer_id" in resp.json()["data"]
        
        # 5. Submit to closed survey
        await ac.patch(f"/api/v1/surveys/{survey_id}/status", json={"status": "CLOSED"}, headers=headers)
        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {"q1": "hello"}}, headers=headers)
        assert resp.status_code == 403
