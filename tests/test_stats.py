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
    await db.users.delete_many({"username": "test_stats_user"})
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
async def test_statistics_aggregation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post("/api/v1/auth/register", json={"username": "test_stats_user", "password": "password"})
        login_resp = await ac.post("/api/v1/auth/login", json={"username": "test_stats_user", "password": "password"})
        token = login_resp.json()["data"]["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        q1_id, q1_version = await create_question(ac, headers, {"type": "ChoiceQuestion", "title": "Choice", "options": ["A", "B"]})
        q2_id, q2_version = await create_question(ac, headers, {"type": "NumberQuestion", "title": "Num"})

        create_resp = await ac.post("/api/v1/surveys", json={"title": "Stats Test"}, headers=headers)
        survey_id = create_resp.json()["data"]["survey_id"]

        await ac.put(
            f"/api/v1/surveys/{survey_id}/schema",
            json={
                "questions": [
                    {"questionId": q1_id, "version": q1_version, "orderIndex": 1},
                    {"questionId": q2_id, "version": q2_version, "orderIndex": 2},
                ]
            },
            headers=headers,
        )
        await ac.patch(f"/api/v1/surveys/{survey_id}/status", json={"status": "PUBLISHED"}, headers=headers)

        for i in range(10):
            payload = {q1_id: ["A"] if i < 6 else ["B"], q2_id: (i + 1) * 10}
            await ac.post(f"/api/v1/surveys/{survey_id}/answers", json={"payloads": payload}, headers=headers)

        stats_resp = await ac.get(f"/api/v1/surveys/{survey_id}/statistics", headers=headers)
        assert stats_resp.status_code == 200
        data = stats_resp.json()["data"]

        assert data["macro_stats"]["total_respondents"] == 10

        q1_stats = data["micro_stats"][q1_id]
        assert q1_stats["distribution"]["A"] == 6
        assert q1_stats["distribution"]["B"] == 4

        q2_stats = data["micro_stats"][q2_id]
        assert q2_stats["average_value"] == 55.0
        assert q2_stats["valid_answers"] == 10
        assert q2_stats["text_list"] == ["10", "20", "30", "40", "50", "60", "70", "80", "90", "100"]
