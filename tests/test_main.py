import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from unittest.mock import MagicMock
from models.article import Article

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

@pytest.mark.asyncio
async def test_get_articles_endpoint():
    # Mock the ArticleService
    mock_service = MagicMock()
    mock_articles = [
        Article(
            id=1, source="Test", url="https://test.com", title="Title 1", author="Author 1",
            article_text="Text", core_thesis="Thesis", detailed_abstract="Abstract",
            supporting_data_quotes="Quotes", date_added="2023-01-01"
        )
    ]
    mock_service.get_latest_articles.return_value = mock_articles
    
    # Override the dependency with an async callable to avoid threadpool
    # handoff issues under strict asyncio test mode.
    from main import get_article_service
    async def override_get_article_service():
        return mock_service

    app.dependency_overrides[get_article_service] = override_get_article_service
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/articles")
    
    # Cleanup override
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Title 1"

@pytest.mark.asyncio
async def test_root_html():
    # Mock the ArticleService
    mock_service = MagicMock()
    mock_articles = [
        Article(
            id=1, source="Test", url="https://test.com", title="Title 1", author="Author 1",
            article_text="Text", core_thesis="Thesis", detailed_abstract="Abstract",
            supporting_data_quotes="Quotes", date_added="2023-01-01"
        )
    ]
    mock_service.get_latest_articles.return_value = mock_articles
    
    from main import get_article_service
    async def override_get_article_service():
        return mock_service

    app.dependency_overrides[get_article_service] = override_get_article_service

    # We expect the root to return HTML
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
    
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Title 1" in response.text # Check if content is rendered

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
