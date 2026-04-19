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
    await db.users.delete_many(
        {"username": {"$in": ["library_owner", "library_recipient", "library_stranger"]}}
    )
    await db.questions.delete_many({})
    await db.surveys.delete_many({})
    yield
    await close_mongo_connection()


async def register_and_login(ac: AsyncClient, username: str) -> str:
    await ac.post("/api/v1/auth/register", json={"username": username, "password": "password"})
    login_resp = await ac.post("/api/v1/auth/login", json={"username": username, "password": "password"})
    assert login_resp.status_code == 200
    return login_resp.json()["data"]["access_token"]


@pytest.mark.anyio
async def test_library_add_remove_and_browse():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        owner_token = await register_and_login(ac, "library_owner")
        recipient_token = await register_and_login(ac, "library_recipient")
        stranger_token = await register_and_login(ac, "library_stranger")

        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        recipient_headers = {"Authorization": f"Bearer {recipient_token}"}
        stranger_headers = {"Authorization": f"Bearer {stranger_token}"}

        own_question_resp = await ac.post(
            "/api/v1/questions",
            json={"type": "TextQuestion", "title": "我的收藏题", "minLength": 2, "maxLength": 20},
            headers=owner_headers,
        )
        assert own_question_resp.status_code == 200
        own_question_id = own_question_resp.json()["data"]["question_id"]

        shared_question_resp = await ac.post(
            "/api/v1/questions",
            json={"type": "NumberQuestion", "title": "共享收藏题", "minValue": 0, "maxValue": 100},
            headers=owner_headers,
        )
        assert shared_question_resp.status_code == 200
        shared_question_id = shared_question_resp.json()["data"]["question_id"]

        share_resp = await ac.post(
            f"/api/v1/questions/{shared_question_id}/shares",
            json={"username": "library_recipient"},
            headers=owner_headers,
        )
        assert share_resp.status_code == 200

        add_own_resp = await ac.post(f"/api/v1/questions/{own_question_id}/library", headers=owner_headers)
        assert add_own_resp.status_code == 200
        assert add_own_resp.json()["data"]["in_library"] is True

        add_shared_resp = await ac.post(f"/api/v1/questions/{shared_question_id}/library", headers=recipient_headers)
        assert add_shared_resp.status_code == 200
        assert add_shared_resp.json()["data"]["in_library"] is True

        stranger_add_resp = await ac.post(f"/api/v1/questions/{shared_question_id}/library", headers=stranger_headers)
        assert stranger_add_resp.status_code == 404

        owner_library_resp = await ac.get("/api/v1/questions/library", headers=owner_headers)
        assert owner_library_resp.status_code == 200
        owner_questions = owner_library_resp.json()["data"]["questions"]
        assert len(owner_questions) == 1
        assert owner_questions[0]["question_id"] == own_question_id
        assert owner_questions[0]["owner_username"] == "library_owner"
        assert owner_questions[0]["is_shared"] is False
        assert owner_questions[0]["in_library"] is True

        recipient_library_resp = await ac.get("/api/v1/questions/library", headers=recipient_headers)
        assert recipient_library_resp.status_code == 200
        recipient_questions = recipient_library_resp.json()["data"]["questions"]
        assert len(recipient_questions) == 1
        assert recipient_questions[0]["question_id"] == shared_question_id
        assert recipient_questions[0]["owner_username"] == "library_owner"
        assert recipient_questions[0]["is_shared"] is True
        assert recipient_questions[0]["in_library"] is True

        remove_shared_resp = await ac.delete(f"/api/v1/questions/{shared_question_id}/library", headers=recipient_headers)
        assert remove_shared_resp.status_code == 200
        assert remove_shared_resp.json()["data"]["in_library"] is False

        recipient_library_after_remove = await ac.get("/api/v1/questions/library", headers=recipient_headers)
        assert recipient_library_after_remove.status_code == 200
        assert recipient_library_after_remove.json()["data"]["questions"] == []

        recipient_can_still_read = await ac.get(f"/api/v1/questions/{shared_question_id}", headers=recipient_headers)
        assert recipient_can_still_read.status_code == 200

        recipient_survey_resp = await ac.post("/api/v1/surveys", json={"title": "Library Shared Survey"}, headers=recipient_headers)
        recipient_survey_id = recipient_survey_resp.json()["data"]["survey_id"]
        save_shared_resp = await ac.put(
            f"/api/v1/surveys/{recipient_survey_id}/schema",
            json={"questions": [{"questionId": shared_question_id, "version": 1, "orderIndex": 1}], "logic_rules": []},
            headers=recipient_headers,
        )
        assert save_shared_resp.status_code == 200

        db = get_database()
        recipient_user = await db.users.find_one({"username": "library_recipient"})
        shared_versions = await db.questions.find({"questionId": shared_question_id}).to_list(length=20)
        assert all(
            not any(grant["userId"] == recipient_user["_id"] for grant in doc.get("libraryMembers", []))
            for doc in shared_versions
        )

        own_versions = await db.questions.find({"questionId": own_question_id}).to_list(length=20)
        owner_user = await db.users.find_one({"username": "library_owner"})
        assert all(
            any(grant["userId"] == owner_user["_id"] for grant in doc.get("libraryMembers", []))
            for doc in own_versions
        )
