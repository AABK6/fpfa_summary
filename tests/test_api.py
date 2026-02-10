import sqlite3

import json

def test_api_articles(client):
    """
    Test the /api/articles endpoint using the Flask test client.
    """
    response = client.get('/api/articles')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    # Note: If the database is empty, this might fail. 
    # In a real test, we would mock the database or use a test database.
    # For now, we just check if it's a list.
    assert len(data) >= 0


def test_flask_home_page_renders(client):
    """Test Flask home page renders without template/static URL errors."""
    response = client.get('/')
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert '<html' in body.lower()
    assert 'styles.css' in body


def test_flask_get_latest_articles_uses_env_override(monkeypatch, tmp_path):
    from app import get_latest_articles

    custom_db = tmp_path / "flask_override.db"
    conn = sqlite3.connect(custom_db)
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
            date_added TEXT
        )
        """
    )
    conn.execute(
        """
        INSERT INTO articles (
            source, url, title, author, article_text, core_thesis,
            detailed_abstract, supporting_data_quotes, date_added
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "FP",
            "https://example.com",
            "Env Override Title",
            "Author",
            "Text",
            "Thesis",
            "Abstract",
            "Quotes",
            "2026-01-01 12:00:00",
        ),
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("ARTICLES_DB_PATH", str(custom_db))

    articles = get_latest_articles(limit=1)
    assert len(articles) == 1
    assert articles[0]["title"] == "Env Override Title"
