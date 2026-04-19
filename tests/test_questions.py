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
    await db.users.delete_many({"username": "test_question_owner"})
    await db.questions.delete_many({})
    await db.surveys.delete_many({})
    yield
    await close_mongo_connection()


@pytest.mark.anyio
async def test_question_version_chain_and_survey_snapshot_isolation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/v1/auth/register", json={"username": "test_question_owner", "password": "password"})
        login_resp = await ac.post("/api/v1/auth/login", json={"username": "test_question_owner", "password": "password"})
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        create_question_resp = await ac.post(
            "/api/v1/questions",
            json={"type": "TextQuestion", "title": "原始题目", "minLength": 2, "maxLength": 10},
            headers=headers,
        )
        assert create_question_resp.status_code == 200
        question_id = create_question_resp.json()["data"]["question_id"]

        create_version_resp = await ac.post(
            f"/api/v1/questions/{question_id}/versions",
            json={"base_version": 1, "type": "TextQuestion", "title": "升级后题目", "minLength": 4, "maxLength": 12},
            headers=headers,
        )
        assert create_version_resp.status_code == 200
        assert create_version_resp.json()["data"]["version"] == 2

        versions_resp = await ac.get(f"/api/v1/questions/{question_id}", headers=headers)
        assert versions_resp.status_code == 200
        versions = versions_resp.json()["data"]["versions"]
        assert [version["version"] for version in versions] == [1, 2]

        detail_resp = await ac.get(f"/api/v1/questions/{question_id}/versions/2", headers=headers)
        assert detail_resp.status_code == 200
        assert detail_resp.json()["data"]["title"] == "升级后题目"

        survey_a_resp = await ac.post("/api/v1/surveys", json={"title": "问卷A"}, headers=headers)
        survey_b_resp = await ac.post("/api/v1/surveys", json={"title": "问卷B"}, headers=headers)
        survey_a_id = survey_a_resp.json()["data"]["survey_id"]
        survey_b_id = survey_b_resp.json()["data"]["survey_id"]

        save_a_resp = await ac.put(
            f"/api/v1/surveys/{survey_a_id}/schema",
            json={"questions": [{"questionId": question_id, "version": 1, "orderIndex": 1}], "logic_rules": []},
            headers=headers,
        )
        save_b_resp = await ac.put(
            f"/api/v1/surveys/{survey_b_id}/schema",
            json={"questions": [{"questionId": question_id, "version": 2, "orderIndex": 1}], "logic_rules": []},
            headers=headers,
        )
        assert save_a_resp.status_code == 200
        assert save_b_resp.status_code == 200

        db = get_database()
        survey_a = await db.surveys.find_one({"_id": ObjectId(survey_a_id)})
        survey_b = await db.surveys.find_one({"_id": ObjectId(survey_b_id)})

        assert survey_a["questions"][0]["version"] == 1
        assert survey_a["questions"][0]["snapshot"]["title"] == "原始题目"
        assert survey_a["questions"][0]["snapshot"]["minLength"] == 2

        assert survey_b["questions"][0]["version"] == 2
        assert survey_b["questions"][0]["snapshot"]["title"] == "升级后题目"
        assert survey_b["questions"][0]["snapshot"]["minLength"] == 4
