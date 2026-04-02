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
    # Clean up test users
    await db.users.delete_many({"username": {"$regex": "^test_.*"}})
    yield
    # Clean up after tests
    await db.users.delete_many({"username": {"$regex": "^test_.*"}})
    await close_mongo_connection()

@pytest.mark.anyio
async def test_register_and_login():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Register a new user
        reg_payload = {"username": "test_user_1", "password": "password123"}
        response = await ac.post("/api/v1/auth/register", json=reg_payload)
        assert response.status_code == 200
        assert response.json()["message"] == "success"
        
        # 2. Register the same user (expect 400)
        response = await ac.post("/api/v1/auth/register", json=reg_payload)
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == 40001
        
        # 3. Login with correct credentials
        login_payload = {"username": "test_user_1", "password": "password123"}
        response = await ac.post("/api/v1/auth/login", json=login_payload)
        assert response.status_code == 200
        assert "access_token" in response.json()["data"]
        
        # 4. Login with wrong password
        wrong_login = {"username": "test_user_1", "password": "wrongpassword"}
        response = await ac.post("/api/v1/auth/login", json=wrong_login)
        assert response.status_code == 401
        assert response.json()["detail"]["code"] == 40101
