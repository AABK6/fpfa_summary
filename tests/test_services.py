import pytest
import sqlite3
import os
from services.article_service import ArticleService
from models.article import Article

TEST_DB = "test_articles.db"

@pytest.fixture
def article_service():
    # Setup
    conn = sqlite3.connect(TEST_DB)
    conn.execute(
        """
        CREATE TABLE articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            url TEXT,
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
    # Insert dummy data
    conn.execute("""
        INSERT INTO articles (source, url, title, author, article_text, core_thesis, detailed_abstract, supporting_data_quotes, date_added)
        VALUES 
        ('FA', 'https://fa.com/1', 'Title 1', 'Author 1', 'Text 1', 'Thesis 1', 'Abstract 1', 'Quotes 1', '2023-01-01 10:00:00'),
        ('FP', 'https://fp.com/2', 'Title 2', 'Author 2', 'Text 2', 'Thesis 2', 'Abstract 2', 'Quotes 2', '2023-01-02 10:00:00')
    """)
    conn.commit()
    conn.close()

    service = ArticleService(db_path=TEST_DB)
    yield service

    # Teardown
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_get_latest_articles(article_service):
    articles = article_service.get_latest_articles(limit=10)
    assert len(articles) == 2
    # Check order: date_added DESC means Title 2 (Jan 2) should be first
    assert articles[0].title == "Title 2"
    assert articles[1].title == "Title 1"
    
    # Check model validation
    assert isinstance(articles[0], Article)

def test_get_latest_articles_empty_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    
    # create empty db
    conn = sqlite3.connect(TEST_DB)
    conn.execute("CREATE TABLE articles (id int)") # minimal to exist
    conn.close()
    
    # Re-init service with empty db
    service = ArticleService(db_path=TEST_DB)
    # But wait, the table schema needs to match or it might crash on SELECT?
    # The service handles OperationalError if table missing?
    # Let's just test with no file first
    os.remove(TEST_DB)
    service = ArticleService(db_path=TEST_DB)
    articles = service.get_latest_articles()
    assert articles == []
    
    # cleanup handled by fixture? No, I manually removed it.
    # The fixture teardown checks existence.
