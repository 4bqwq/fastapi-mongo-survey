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
        {
            "username": {
                "$in": [
                    "cross_owner",
                    "cross_recipient",
                    "cross_stranger",
                    "cross_filler_a",
                    "cross_filler_b",
                ]
            }
        }
    )
    await db.questions.delete_many({})
    await db.surveys.delete_many({})
    await db.answers.delete_many({})
    yield
    await close_mongo_connection()


async def register_and_login(ac: AsyncClient, username: str) -> str:
    await ac.post("/api/v1/auth/register", json={"username": username, "password": "password"})
    login_resp = await ac.post("/api/v1/auth/login", json={"username": username, "password": "password"})
    assert login_resp.status_code == 200
    return login_resp.json()["data"]["access_token"]


async def create_question(ac: AsyncClient, headers: dict, payload: dict) -> tuple[str, int]:
    resp = await ac.post("/api/v1/questions", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    return data["question_id"], data["version"]


async def create_survey_with_question(ac: AsyncClient, headers: dict, title: str, question_id: str, version: int) -> str:
    create_resp = await ac.post("/api/v1/surveys", json={"title": title}, headers=headers)
    assert create_resp.status_code == 200
    survey_id = create_resp.json()["data"]["survey_id"]
    save_resp = await ac.put(
        f"/api/v1/surveys/{survey_id}/schema",
        json={"questions": [{"questionId": question_id, "version": version, "orderIndex": 1}], "logic_rules": []},
        headers=headers,
    )
    assert save_resp.status_code == 200
    publish_resp = await ac.patch(f"/api/v1/surveys/{survey_id}/status", json={"status": "PUBLISHED"}, headers=headers)
    assert publish_resp.status_code == 200
    return survey_id


@pytest.mark.anyio
async def test_cross_survey_statistics_and_permissions():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        owner_token = await register_and_login(ac, "cross_owner")
        recipient_token = await register_and_login(ac, "cross_recipient")
        stranger_token = await register_and_login(ac, "cross_stranger")
        filler_a_token = await register_and_login(ac, "cross_filler_a")
        filler_b_token = await register_and_login(ac, "cross_filler_b")

        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        recipient_headers = {"Authorization": f"Bearer {recipient_token}"}
        stranger_headers = {"Authorization": f"Bearer {stranger_token}"}
        filler_a_headers = {"Authorization": f"Bearer {filler_a_token}"}
        filler_b_headers = {"Authorization": f"Bearer {filler_b_token}"}

        choice_id, choice_version = await create_question(
            ac, owner_headers, {"type": "ChoiceQuestion", "title": "跨问卷选择题", "options": ["A", "B"], "minSelect": 1, "maxSelect": 1}
        )
        share_resp = await ac.post(
            f"/api/v1/questions/{choice_id}/shares",
            json={"username": "cross_recipient"},
            headers=owner_headers,
        )
        assert share_resp.status_code == 200

        owner_choice_survey = await create_survey_with_question(ac, owner_headers, "Choice Owner", choice_id, choice_version)
        recipient_choice_survey = await create_survey_with_question(ac, recipient_headers, "Choice Recipient", choice_id, choice_version)

        for headers, survey_id, payload in [
            (filler_a_headers, owner_choice_survey, {choice_id: ["A"]}),
            (filler_b_headers, owner_choice_survey, {choice_id: ["B"]}),
            (recipient_headers, recipient_choice_survey, {choice_id: ["A"]}),
        ]:
            resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": payload}, headers=headers)
            assert resp.status_code == 200

        choice_stats_owner = await ac.get(f"/api/v1/questions/{choice_id}/statistics", headers=owner_headers)
        assert choice_stats_owner.status_code == 200
        choice_data = choice_stats_owner.json()["data"]
        assert choice_data["type"] == "ChoiceQuestion"
        assert choice_data["survey_count"] == 2
        assert choice_data["total_answers"] == 3
        assert choice_data["distribution"]["A"] == 2
        assert choice_data["distribution"]["B"] == 1

        choice_stats_recipient = await ac.get(f"/api/v1/questions/{choice_id}/statistics", headers=recipient_headers)
        assert choice_stats_recipient.status_code == 200

        choice_stats_stranger = await ac.get(f"/api/v1/questions/{choice_id}/statistics", headers=stranger_headers)
        assert choice_stats_stranger.status_code == 404

        number_id, number_version = await create_question(
            ac, owner_headers, {"type": "NumberQuestion", "title": "跨问卷数字题", "minValue": 0, "maxValue": 100, "mustBeInteger": True}
        )
        number_survey_a = await create_survey_with_question(ac, owner_headers, "Number A", number_id, number_version)
        number_survey_b = await create_survey_with_question(ac, owner_headers, "Number B", number_id, number_version)

        for survey_id, value in [(number_survey_a, 10), (number_survey_a, 20), (number_survey_b, 30)]:
            resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {number_id: value}}, headers=filler_a_headers)
            assert resp.status_code == 200

        number_stats_resp = await ac.get(f"/api/v1/questions/{number_id}/statistics", headers=owner_headers)
        assert number_stats_resp.status_code == 200
        number_data = number_stats_resp.json()["data"]
        assert number_data["type"] == "NumberQuestion"
        assert number_data["survey_count"] == 2
        assert number_data["valid_answers"] == 3
        assert number_data["average_value"] == 20.0
        assert number_data["distribution"]["10"] == 1
        assert number_data["distribution"]["20"] == 1
        assert number_data["distribution"]["30"] == 1

        text_id, text_version = await create_question(
            ac, owner_headers, {"type": "TextQuestion", "title": "跨问卷文本题", "minLength": 1, "maxLength": 50}
        )
        text_survey_a = await create_survey_with_question(ac, owner_headers, "Text A", text_id, text_version)
        text_survey_b = await create_survey_with_question(ac, owner_headers, "Text B", text_id, text_version)
        for survey_id, value in [(text_survey_a, "foo"), (text_survey_b, "bar")]:
            resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {text_id: value}}, headers=filler_b_headers)
            assert resp.status_code == 200

        text_stats_resp = await ac.get(f"/api/v1/questions/{text_id}/statistics", headers=owner_headers)
        assert text_stats_resp.status_code == 200
        text_data = text_stats_resp.json()["data"]
        assert text_data["type"] == "TextQuestion"
        assert text_data["survey_count"] == 2
        assert text_data["total_answers"] == 2
        assert set(text_data["text_list"]) == {"foo", "bar"}

        mixed_id, mixed_v1 = await create_question(
            ac, owner_headers, {"type": "TextQuestion", "title": "混合题型题", "minLength": 1, "maxLength": 20}
        )
        mixed_v2_resp = await ac.post(
            f"/api/v1/questions/{mixed_id}/versions",
            json={"base_version": mixed_v1, "type": "NumberQuestion", "title": "混合题型题 v2", "minValue": 0, "maxValue": 10},
            headers=owner_headers,
        )
        assert mixed_v2_resp.status_code == 200
        mixed_v2 = mixed_v2_resp.json()["data"]["version"]

        mixed_survey_a = await create_survey_with_question(ac, owner_headers, "Mixed A", mixed_id, mixed_v1)
        mixed_survey_b = await create_survey_with_question(ac, owner_headers, "Mixed B", mixed_id, mixed_v2)

        resp = await ac.post(f"/api/v1/surveys/{mixed_survey_a}/answers", json={"payloads": {mixed_id: "text"}}, headers=filler_a_headers)
        assert resp.status_code == 200
        resp = await ac.post(f"/api/v1/surveys/{mixed_survey_b}/answers", json={"payloads": {mixed_id: 5}}, headers=filler_b_headers)
        assert resp.status_code == 200

        mixed_stats_resp = await ac.get(f"/api/v1/questions/{mixed_id}/statistics", headers=owner_headers)
        assert mixed_stats_resp.status_code == 422
        assert "多种题型版本" in mixed_stats_resp.json()["detail"]["message"]
