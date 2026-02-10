from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from models.article import Article


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_get_articles_endpoint_ordering():
    mock_service = MagicMock()
    mock_articles = [
        Article(
            id=2,
            source="FP",
            url="https://fp.com/2",
            title="Newest title",
            author="Author 2",
            article_text="Text",
            core_thesis="Thesis",
            detailed_abstract="Abstract",
            supporting_data_quotes="Quotes",
            date_added="2023-01-02",
        ),
        Article(
            id=1,
            source="FA",
            url="https://fa.com/1",
            title="Older title",
            author="Author 1",
            article_text="Text",
            core_thesis="Thesis",
            detailed_abstract="Abstract",
            supporting_data_quotes="Quotes",
            date_added="2023-01-01",
        ),
    ]
    mock_service.get_latest_articles.return_value = mock_articles

    from main import get_article_service

    async def override_get_article_service():
        return mock_service

    app.dependency_overrides[get_article_service] = override_get_article_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/articles")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert [article["title"] for article in response.json()] == ["Newest title", "Older title"]


@pytest.mark.asyncio
async def test_root_html_top_card_uses_first_article():
    mock_service = MagicMock()
    mock_articles = [
        Article(
            id=2,
            source="FP",
            url="https://fp.com/2",
            title="Newest title",
            author="Author 2",
            article_text="Text",
            core_thesis="Thesis",
            detailed_abstract="Abstract",
            supporting_data_quotes="Quotes",
            date_added="2023-01-02",
        ),
        Article(
            id=1,
            source="FA",
            url="https://fa.com/1",
            title="Older title",
            author="Author 1",
            article_text="Text",
            core_thesis="Thesis",
            detailed_abstract="Abstract",
            supporting_data_quotes="Quotes",
            date_added="2023-01-01",
        ),
    ]
    mock_service.get_latest_articles.return_value = mock_articles

    from main import get_article_service

    async def override_get_article_service():
        return mock_service

    app.dependency_overrides[get_article_service] = override_get_article_service

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert response.text.index("Newest title") < response.text.index("Older title")


@pytest.mark.asyncio
async def test_docs_accessible():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response_docs = await ac.get("/docs")
        response_redoc = await ac.get("/redoc")
        response_openapi = await ac.get("/openapi.json")

    assert response_docs.status_code == 200
    assert response_redoc.status_code == 200
    assert response_openapi.status_code == 200
    assert "FPFA Summary API" in response_openapi.json()["info"]["title"]


def test_get_article_service_uses_env_override(monkeypatch, tmp_path):
    from main import get_article_service

    custom_db = tmp_path / "main_override.db"
    monkeypatch.setenv("ARTICLES_DB_PATH", str(custom_db))

    service = get_article_service()
    assert service.db_path == str(custom_db)
