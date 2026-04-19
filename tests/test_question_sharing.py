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
        {"username": {"$in": ["share_owner", "share_recipient", "share_stranger"]}}
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
async def test_question_sharing_and_usage_query():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        owner_token = await register_and_login(ac, "share_owner")
        recipient_token = await register_and_login(ac, "share_recipient")
        stranger_token = await register_and_login(ac, "share_stranger")

        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        recipient_headers = {"Authorization": f"Bearer {recipient_token}"}
        stranger_headers = {"Authorization": f"Bearer {stranger_token}"}

        create_resp = await ac.post(
            "/api/v1/questions",
            json={"type": "TextQuestion", "title": "共享题", "minLength": 2, "maxLength": 20},
            headers=owner_headers,
        )
        assert create_resp.status_code == 200
        question_id = create_resp.json()["data"]["question_id"]

        version_resp = await ac.post(
            f"/api/v1/questions/{question_id}/versions",
            json={"base_version": 1, "type": "TextQuestion", "title": "共享题 v2", "minLength": 4, "maxLength": 30},
            headers=owner_headers,
        )
        assert version_resp.status_code == 200

        stranger_detail_resp = await ac.get(
            f"/api/v1/questions/{question_id}/versions/1",
            headers=stranger_headers,
        )
        assert stranger_detail_resp.status_code == 404

        share_resp = await ac.post(
            f"/api/v1/questions/{question_id}/shares",
            json={"username": "share_recipient"},
            headers=owner_headers,
        )
        assert share_resp.status_code == 200
        assert share_resp.json()["data"]["shared_with"][0]["username"] == "share_recipient"

        shares_resp = await ac.get(f"/api/v1/questions/{question_id}/shares", headers=owner_headers)
        assert shares_resp.status_code == 200
        assert shares_resp.json()["data"]["shared_with"][0]["username"] == "share_recipient"

        recipient_versions_resp = await ac.get(f"/api/v1/questions/{question_id}", headers=recipient_headers)
        assert recipient_versions_resp.status_code == 200
        assert [item["version"] for item in recipient_versions_resp.json()["data"]["versions"]] == [1, 2]

        recipient_detail_resp = await ac.get(
            f"/api/v1/questions/{question_id}/versions/2",
            headers=recipient_headers,
        )
        assert recipient_detail_resp.status_code == 200
        assert recipient_detail_resp.json()["data"]["title"] == "共享题 v2"

        recipient_create_version_resp = await ac.post(
            f"/api/v1/questions/{question_id}/versions",
            json={"base_version": 2, "type": "TextQuestion", "title": "不该成功", "minLength": 1, "maxLength": 5},
            headers=recipient_headers,
        )
        assert recipient_create_version_resp.status_code == 404

        recipient_shares_resp = await ac.get(f"/api/v1/questions/{question_id}/shares", headers=recipient_headers)
        assert recipient_shares_resp.status_code == 403

        owner_survey_resp = await ac.post("/api/v1/surveys", json={"title": "Owner Survey"}, headers=owner_headers)
        recipient_survey_resp = await ac.post("/api/v1/surveys", json={"title": "Recipient Survey"}, headers=recipient_headers)
        stranger_survey_resp = await ac.post("/api/v1/surveys", json={"title": "Stranger Survey"}, headers=stranger_headers)
        owner_survey_id = owner_survey_resp.json()["data"]["survey_id"]
        recipient_survey_id = recipient_survey_resp.json()["data"]["survey_id"]
        stranger_survey_id = stranger_survey_resp.json()["data"]["survey_id"]

        owner_save_resp = await ac.put(
            f"/api/v1/surveys/{owner_survey_id}/schema",
            json={"questions": [{"questionId": question_id, "version": 1, "orderIndex": 1}], "logic_rules": []},
            headers=owner_headers,
        )
        assert owner_save_resp.status_code == 200

        recipient_save_resp = await ac.put(
            f"/api/v1/surveys/{recipient_survey_id}/schema",
            json={"questions": [{"questionId": question_id, "version": 2, "orderIndex": 1}], "logic_rules": []},
            headers=recipient_headers,
        )
        assert recipient_save_resp.status_code == 200

        stranger_save_resp = await ac.put(
            f"/api/v1/surveys/{stranger_survey_id}/schema",
            json={"questions": [{"questionId": question_id, "version": 1, "orderIndex": 1}], "logic_rules": []},
            headers=stranger_headers,
        )
        assert stranger_save_resp.status_code == 422

        owner_usage_resp = await ac.get(f"/api/v1/questions/{question_id}/usage", headers=owner_headers)
        assert owner_usage_resp.status_code == 200
        owner_usages = owner_usage_resp.json()["data"]["usages"]
        assert len(owner_usages) == 2
        assert {usage["survey_title"] for usage in owner_usages} == {"Owner Survey", "Recipient Survey"}
        assert {usage["question_version"] for usage in owner_usages} == {1, 2}
        assert {usage["survey_owner_username"] for usage in owner_usages} == {"share_owner", "share_recipient"}

        recipient_usage_resp = await ac.get(f"/api/v1/questions/{question_id}/usage", headers=recipient_headers)
        assert recipient_usage_resp.status_code == 200
        assert len(recipient_usage_resp.json()["data"]["usages"]) == 2

        stranger_usage_resp = await ac.get(f"/api/v1/questions/{question_id}/usage", headers=stranger_headers)
        assert stranger_usage_resp.status_code == 404
