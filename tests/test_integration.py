import pytest
import sqlite3
import os
from httpx import AsyncClient, ASGITransport
from main import app, get_article_service
from services.article_service import ArticleService
from models.article import Article

TEST_DB = "integration_test_articles.db"

@pytest.fixture
def integration_service():
    # Setup: Create a temporary database for integration testing
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        
    conn = sqlite3.connect(TEST_DB)
    conn.execute(
        """
        CREATE TABLE articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            url TEXT UNIQUE,
            title TEXT,
            author TEXT,
            article_text TEXT,
            core_thesis TEXT,
            detailed_abstract TEXT,
            supporting_data_quotes TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()

    service = ArticleService(db_path=TEST_DB)
    return service

@pytest.mark.asyncio
async def test_full_flow_scraper_to_api(integration_service):
    # 1. Simulate Scraper: Insert an article directly into the DB
    conn = sqlite3.connect(TEST_DB)
    conn.execute("""
        INSERT INTO articles (source, url, title, author, article_text, core_thesis, detailed_abstract, supporting_data_quotes)
        VALUES ('FA', 'https://test.com/integration', 'Integration Title', 'Author', 'Body', 'Thesis', 'Abstract', 'Quotes')
    """)
    conn.commit()
    conn.close()

    # 2. Configure app to use the integration database
    async def override_get_article_service():
        return integration_service

    app.dependency_overrides[get_article_service] = override_get_article_service

    # 3. Call the API and verify the data
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/articles")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["title"] == "Integration Title"
    assert data[0]["source"] == "FA"

    # Cleanup
    app.dependency_overrides.clear()
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
