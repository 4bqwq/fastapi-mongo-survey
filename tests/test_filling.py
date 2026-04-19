from datetime import timedelta

import pytest
from bson import ObjectId
from httpx import AsyncClient, ASGITransport

from app.api.answers import get_effective_questions
from app.core.time import utc_now
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.main import app


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="module", autouse=True)
async def manage_db():
    await connect_to_mongo()
    db = get_database()
    await db.users.delete_many({"username": "test_filler"})
    await db.questions.delete_many({})
    await db.surveys.delete_many({})
    await db.answers.delete_many({})
    yield
    await close_mongo_connection()


async def create_question(ac: AsyncClient, headers: dict, payload: dict) -> tuple[str, int]:
    response = await ac.post("/api/v1/questions", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()["data"]
    return data["question_id"], data["version"]


@pytest.mark.anyio
async def test_filling_validation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/v1/auth/register", json={"username": "test_filler", "password": "password"})
        login_resp = await ac.post("/api/v1/auth/login", json={"username": "test_filler", "password": "password"})
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        q1_id, q1_version = await create_question(
            ac, headers, {"type": "TextQuestion", "title": "Req Q", "isRequired": True, "minLength": 2, "maxLength": 5}
        )
        q2_id, q2_version = await create_question(
            ac, headers, {"type": "NumberQuestion", "title": "Num Q", "minValue": 1, "maxValue": 10, "mustBeInteger": True}
        )

        create_resp = await ac.post("/api/v1/surveys", json={"title": "Fill Test"}, headers=headers)
        survey_id = create_resp.json()["data"]["survey_id"]

        await ac.put(
            f"/api/v1/surveys/{survey_id}/schema",
            json={
                "questions": [
                    {"questionId": q1_id, "version": q1_version, "orderIndex": 1},
                    {"questionId": q2_id, "version": q2_version, "orderIndex": 2},
                ],
                "logic_rules": [],
            },
            headers=headers,
        )
        await ac.patch(f"/api/v1/surveys/{survey_id}/status", json={"status": "PUBLISHED"}, headers=headers)

        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {q2_id: 5}}, headers=headers)
        assert resp.status_code == 422
        assert "第1题" in resp.json()["detail"]["message"]
        assert "必答题" in resp.json()["detail"]["message"]

        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {q1_id: "a", q2_id: 5}}, headers=headers)
        assert resp.status_code == 422
        assert "至少需要输入 2 个字" in resp.json()["detail"]["message"]

        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {q1_id: "hello", q2_id: 1.5}}, headers=headers)
        assert resp.status_code == 422
        assert "第2题" in resp.json()["detail"]["message"]
        assert "整数" in resp.json()["detail"]["message"]

        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {q1_id: "hello", q2_id: 15}}, headers=headers)
        assert resp.status_code == 422
        assert "不能大于 10" in resp.json()["detail"]["message"]

        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {q1_id: "hello", q2_id: 5}}, headers=headers)
        assert resp.status_code == 200

        db = get_database()
        saved_answer = await db.answers.find_one({"_id": ObjectId(resp.json()["data"]["answer_id"])})
        assert saved_answer["respondentId"] != "-1"
        assert saved_answer["isAnonymousSubmission"] is False

        patch_resp = await ac.patch(f"/api/v1/surveys/{survey_id}", json={"is_anonymous": True}, headers=headers)
        assert patch_resp.status_code == 200

        resp = await ac.post(
            f"/api/v1/surveys/{survey_id}/answers",
            json={"submit_as_anonymous": True, "payloads": {q1_id: "hello", q2_id: 6}},
            headers=headers,
        )
        assert resp.status_code == 200
        anonymous_answer = await db.answers.find_one({"_id": ObjectId(resp.json()["data"]["answer_id"])})
        assert anonymous_answer["respondentId"] == "-1"
        assert anonymous_answer["isAnonymousSubmission"] is True

        expired_time = (utc_now() - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
        patch_resp = await ac.patch(f"/api/v1/surveys/{survey_id}", json={"end_time": expired_time}, headers=headers)
        assert patch_resp.status_code == 200

        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {q1_id: "hello", q2_id: 5}}, headers=headers)
        assert resp.status_code == 403
        assert "已截止" in resp.json()["detail"]["message"]

        await ac.patch(f"/api/v1/surveys/{survey_id}/status", json={"status": "CLOSED"}, headers=headers)
        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {q1_id: "hello"}}, headers=headers)
        assert resp.status_code == 403


@pytest.mark.anyio
async def test_number_question_allows_decimal_when_not_integer_only():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login_resp = await ac.post("/api/v1/auth/login", json={"username": "test_filler", "password": "password"})
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        q1_id, q1_version = await create_question(
            ac, headers, {"type": "NumberQuestion", "title": "小数题", "minValue": 0, "maxValue": 10, "mustBeInteger": False}
        )
        create_resp = await ac.post("/api/v1/surveys", json={"title": "Decimal Allowed"}, headers=headers)
        survey_id = create_resp.json()["data"]["survey_id"]

        schema_resp = await ac.put(
            f"/api/v1/surveys/{survey_id}/schema",
            json={"questions": [{"questionId": q1_id, "version": q1_version, "orderIndex": 1}], "logic_rules": []},
            headers=headers,
        )
        assert schema_resp.status_code == 200

        await ac.patch(f"/api/v1/surveys/{survey_id}/status", json={"status": "PUBLISHED"}, headers=headers)
        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {q1_id: 1.5}}, headers=headers)
        assert resp.status_code == 200


@pytest.mark.anyio
async def test_choice_logic_requires_exact_match():
    questions = [
        {
            "questionId": "q1",
            "orderIndex": 1,
            "snapshot": {"type": "ChoiceQuestion", "title": "多选题", "options": ["A", "B", "C"], "minSelect": 1, "maxSelect": 2},
        },
        {"questionId": "q2", "orderIndex": 2, "snapshot": {"type": "TextQuestion", "title": "组合命中题"}},
        {"questionId": "q3", "orderIndex": 3, "snapshot": {"type": "TextQuestion", "title": "单项命中题"}},
        {"questionId": "q4", "orderIndex": 4, "snapshot": {"type": "TextQuestion", "title": "结束题"}},
    ]
    logic_rules = [
        {"ruleId": "r1", "sourceQuestionId": "q1", "targetQuestionId": "q3", "triggerCondition": "1"},
        {"ruleId": "r2", "sourceQuestionId": "q1", "targetQuestionId": "q4", "triggerCondition": "1 2"},
    ]

    effective_ids = get_effective_questions(questions, logic_rules, {"q1": ["A", "B"]})
    assert effective_ids == {"q1", "q4"}

    single_effective_ids = get_effective_questions(questions, logic_rules, {"q1": ["A"]})
    assert single_effective_ids == {"q1", "q3", "q4"}
