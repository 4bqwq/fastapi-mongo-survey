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
    await db.users.delete_many({"username": "test_stats_user"})
    await db.surveys.delete_many({})
    await db.answers.delete_many({})
    yield
    await close_mongo_connection()

@pytest.mark.anyio
async def test_statistics_aggregation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Setup user and survey
        await ac.post("/api/v1/auth/register", json={"username": "test_stats_user", "password": "password"})
        login_resp = await ac.post("/api/v1/auth/login", json={"username": "test_stats_user", "password": "password"})
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        create_resp = await ac.post("/api/v1/surveys", json={"title": "Stats Test"}, headers=headers)
        survey_id = create_resp.json()["data"]["survey_id"]
        
        schema = {
            "questions": [
                {"questionId": "q1", "type": "ChoiceQuestion", "options": ["A", "B"], "orderIndex": 1, "title": "Choice"},
                {"questionId": "q2", "type": "NumberQuestion", "orderIndex": 2, "title": "Num"}
            ]
        }
        await ac.put(f"/api/v1/surveys/{survey_id}/schema", json=schema, headers=headers)
        await ac.patch(f"/api/v1/surveys/{survey_id}/status", json={"status": "PUBLISHED"}, headers=headers)

        # 2. Insert 10 mock answers
        # 6 select A, 4 select B
        # Numbers: 10, 20, 30, 40, 50, 60, 70, 80, 90, 100 (Avg should be 55.0)
        for i in range(10):
            payload = {
                "q1": ["A"] if i < 6 else ["B"],
                "q2": (i + 1) * 10
            }
            await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": payload}, headers=headers)

        # 3. Call Statistics API
        stats_resp = await ac.get(f"/api/v1/surveys/{survey_id}/statistics", headers=headers)
        assert stats_resp.status_code == 200
        data = stats_resp.json()["data"]
        
        assert data["macro_stats"]["total_respondents"] == 10
        
        q1_stats = data["micro_stats"]["q1"]
        assert q1_stats["distribution"]["A"] == 6
        assert q1_stats["distribution"]["B"] == 4
        
        q2_stats = data["micro_stats"]["q2"]
        assert q2_stats["average_value"] == 55.0
        assert q2_stats["valid_answers"] == 10
        assert q2_stats["text_list"] == ["10", "20", "30", "40", "50", "60", "70", "80", "90", "100"]
