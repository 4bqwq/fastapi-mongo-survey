import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.api.answers import get_effective_questions
from bson import ObjectId
from datetime import datetime, timedelta

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
                {"questionId": "q1", "type": "TextQuestion", "orderIndex": 1, "isRequired": True, "title": "Req Q", "minLength": 2, "maxLength": 5},
                {"questionId": "q2", "type": "NumberQuestion", "orderIndex": 2, "isRequired": False, "minValue": 1, "maxValue": 10, "mustBeInteger": True, "title": "Num Q"}
            ],
            "logic_rules": []
        }
        await ac.put(f"/api/v1/surveys/{survey_id}/schema", json=schema, headers=headers)
        
        # Must publish first
        await ac.patch(f"/api/v1/surveys/{survey_id}/status", json={"status": "PUBLISHED"}, headers=headers)

        # 2. Submit with missing required question
        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {"q2": 5}}, headers=headers)
        assert resp.status_code == 422
        assert "第1题" in resp.json()["detail"]["message"]
        assert "必答题" in resp.json()["detail"]["message"]

        # 3. Submit with text too short
        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {"q1": "a", "q2": 5}}, headers=headers)
        assert resp.status_code == 422
        assert "第1题" in resp.json()["detail"]["message"]
        assert "至少需要输入 2 个字" in resp.json()["detail"]["message"]

        # 4. Submit with decimal for integer-only number
        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {"q1": "hello", "q2": 1.5}}, headers=headers)
        assert resp.status_code == 422
        assert "第2题" in resp.json()["detail"]["message"]
        assert "整数" in resp.json()["detail"]["message"]

        # 5. Submit with number out of range
        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {"q1": "hello", "q2": 15}}, headers=headers)
        assert resp.status_code == 422
        assert "第2题" in resp.json()["detail"]["message"]
        assert "不能大于 10" in resp.json()["detail"]["message"]

        # 6. Successful real-name submission
        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {"q1": "hello", "q2": 5}}, headers=headers)
        assert resp.status_code == 200
        assert "answer_id" in resp.json()["data"]

        db = get_database()
        saved_answer = await db.answers.find_one({"_id": ObjectId(resp.json()["data"]["answer_id"])})
        assert saved_answer["respondentId"] != "-1"
        assert saved_answer["isAnonymousSubmission"] is False

        # 7. Enable anonymous option and submit anonymously
        patch_resp = await ac.patch(
            f"/api/v1/surveys/{survey_id}",
            json={"is_anonymous": True},
            headers=headers,
        )
        assert patch_resp.status_code == 200

        resp = await ac.post(
            f"/api/v1/surveys/{survey_id}/answers",
            json={"submit_as_anonymous": True, "payloads": {"q1": "hello", "q2": 6}},
            headers=headers,
        )
        assert resp.status_code == 200
        anonymous_answer = await db.answers.find_one({"_id": ObjectId(resp.json()["data"]["answer_id"])})
        assert anonymous_answer["respondentId"] == "-1"
        assert anonymous_answer["isAnonymousSubmission"] is True

        # 8. Set survey expired and reject submission
        expired_time = (datetime.utcnow() - timedelta(minutes=5)).isoformat() + "Z"
        patch_resp = await ac.patch(
            f"/api/v1/surveys/{survey_id}",
            json={"end_time": expired_time},
            headers=headers,
        )
        assert patch_resp.status_code == 200

        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {"q1": "hello", "q2": 5}}, headers=headers)
        assert resp.status_code == 403
        assert "已截止" in resp.json()["detail"]["message"]

        # 9. Submit to closed survey
        await ac.patch(f"/api/v1/surveys/{survey_id}/status", json={"status": "CLOSED"}, headers=headers)
        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {"q1": "hello"}}, headers=headers)
        assert resp.status_code == 403

@pytest.mark.anyio
async def test_number_question_allows_decimal_when_not_integer_only():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        login_resp = await ac.post("/api/v1/auth/login", json={"username": "test_filler", "password": "password"})
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        create_resp = await ac.post("/api/v1/surveys", json={"title": "Decimal Allowed"}, headers=headers)
        survey_id = create_resp.json()["data"]["survey_id"]

        schema = {
            "questions": [
                {"questionId": "q1", "type": "NumberQuestion", "orderIndex": 1, "isRequired": True, "title": "小数题", "minValue": 0, "maxValue": 10, "mustBeInteger": False}
            ],
            "logic_rules": []
        }
        schema_resp = await ac.put(f"/api/v1/surveys/{survey_id}/schema", json=schema, headers=headers)
        assert schema_resp.status_code == 200

        await ac.patch(f"/api/v1/surveys/{survey_id}/status", json={"status": "PUBLISHED"}, headers=headers)

        resp = await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": {"q1": 1.5}}, headers=headers)
        assert resp.status_code == 200

@pytest.mark.anyio
async def test_choice_logic_requires_exact_match():
    questions = [
        {
            "questionId": "q1",
            "type": "ChoiceQuestion",
            "orderIndex": 1,
            "title": "多选题",
            "options": ["A", "B", "C"],
            "minSelect": 1,
            "maxSelect": 2
        },
        {"questionId": "q2", "type": "TextQuestion", "orderIndex": 2, "title": "组合命中题"},
        {"questionId": "q3", "type": "TextQuestion", "orderIndex": 3, "title": "单项命中题"},
        {"questionId": "q4", "type": "TextQuestion", "orderIndex": 4, "title": "结束题"}
    ]
    logic_rules = [
        {"ruleId": "r1", "sourceQuestionId": "q1", "targetQuestionId": "q3", "triggerCondition": "1"},
        {"ruleId": "r2", "sourceQuestionId": "q1", "targetQuestionId": "q4", "triggerCondition": "1 2"}
    ]

    effective_ids = get_effective_questions(questions, logic_rules, {"q1": ["A", "B"]})
    assert effective_ids == {"q1", "q4"}

    single_effective_ids = get_effective_questions(questions, logic_rules, {"q1": ["A"]})
    assert single_effective_ids == {"q1", "q3", "q4"}
