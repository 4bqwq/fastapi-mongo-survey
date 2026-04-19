import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
import asyncio

@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"

@pytest.fixture(scope="module", autouse=True)
async def manage_db():
    await connect_to_mongo()
    db = get_database()
    # Clean up
    await db.users.delete_many({"username": {"$regex": "^test_.*"}})
    await db.questions.delete_many({})
    await db.surveys.delete_many({})
    yield
    await close_mongo_connection()

async def get_token(ac, username, password):
    await ac.post("/api/v1/auth/register", json={"username": username, "password": password})
    resp = await ac.post("/api/v1/auth/login", json={"username": username, "password": password})
    return resp.json()["data"]["access_token"]

@pytest.mark.anyio
async def test_survey_crud_and_isolation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Create two users
        token_a = await get_token(ac, "test_user_a", "pass123")
        token_b = await get_token(ac, "test_user_b", "pass123")
        
        # 2. User A creates a survey
        headers_a = {"Authorization": f"Bearer {token_a}"}
        create_resp = await ac.post(
            "/api/v1/surveys",
            json={"title": "Survey A", "is_anonymous": False, "end_time": "2030-01-01T00:00:00Z"},
            headers=headers_a,
        )
        assert create_resp.status_code == 200
        survey_id = create_resp.json()["data"]["survey_id"]
        
        # 3. User B tries to list surveys (should be empty)
        headers_b = {"Authorization": f"Bearer {token_b}"}
        list_b = await ac.get("/api/v1/surveys", headers=headers_b)
        assert len(list_b.json()["data"]) == 0
        
        # 4. User B tries to update User A's survey status (should be 403)
        update_b = await ac.patch(f"/api/v1/surveys/{survey_id}/status", json={"status": "PUBLISHED"}, headers=headers_b)
        assert update_b.status_code == 403
        assert update_b.json()["detail"]["code"] == 40301
        
        # 5. User A updates their own survey status
        update_a = await ac.patch(f"/api/v1/surveys/{survey_id}/status", json={"status": "PUBLISHED"}, headers=headers_a)
        assert update_a.status_code == 200
        assert update_a.json()["data"]["status"] == "PUBLISHED"
        
        # 6. Verify User A sees the survey in list
        list_a = await ac.get("/api/v1/surveys", headers=headers_a)
        assert len(list_a.json()["data"]) == 1
        assert list_a.json()["data"][0]["title"] == "Survey A"
        assert list_a.json()["data"][0]["end_time"] is not None

        # 7. User A updates survey metadata
        metadata_resp = await ac.patch(
            f"/api/v1/surveys/{survey_id}",
            json={"title": "Survey A v2", "is_anonymous": True, "end_time": None},
            headers=headers_a,
        )
        assert metadata_resp.status_code == 200
        assert metadata_resp.json()["data"]["title"] == "Survey A v2"
        assert metadata_resp.json()["data"]["is_anonymous"] is True
        assert metadata_resp.json()["data"]["end_time"] is None
