import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.fixture(scope="module")
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_editor_page_contains_library_picker():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/editor/test-survey-id")
        assert response.status_code == 200
        assert "从题库选择题目" in response.text
        assert "从题库选题" in response.text
        assert "新建题目" in response.text
        assert "保存到题库" in response.text
        assert "分享给..." in response.text
        assert "版本历史" in response.text
        assert "查看使用情况" in response.text
        assert "移出题库" in response.text


@pytest.mark.anyio
async def test_stats_page_contains_cross_survey_entry():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/stats/test-survey-id")
        assert response.status_code == 200
        assert "跨问卷统计" in response.text
