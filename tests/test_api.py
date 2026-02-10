import sqlite3

import json
import sqlite3

from fastapi.testclient import TestClient

import app as flask_app_module
from main import app as fastapi_app, get_article_service
from services.article_service import ArticleService


def _build_test_db(db_path):
    conn = sqlite3.connect(db_path)
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
    conn.execute(
        """
        INSERT INTO articles
            (source, url, title, author, article_text, core_thesis, detailed_abstract, supporting_data_quotes, date_added)
        VALUES
            ('FA', 'https://fa.com/1', 'Older title', 'Author 1', 'Text 1', 'Thesis 1', 'Abstract 1', 'Quotes 1', '2023-01-01 10:00:00'),
            ('FP', 'https://fp.com/2', 'Newest title', 'Author 2', 'Text 2', 'Thesis 2', 'Abstract 2', 'Quotes 2', '2023-01-02 10:00:00')
        """
    )
    conn.commit()
    conn.close()


def test_api_articles_ordering(client, tmp_path, monkeypatch):
    db_path = tmp_path / "articles.db"
    _build_test_db(db_path)

    real_connect = sqlite3.connect
    monkeypatch.setattr(flask_app_module.sqlite3, "connect", lambda _: real_connect(db_path))

    response = client.get("/api/articles")
    assert response.status_code == 200

    data = json.loads(response.data)
    assert [article["title"] for article in data] == ["Newest title", "Older title"]


def test_flask_home_page_top_card_uses_newest_first(client, monkeypatch):
    monkeypatch.setattr(
        flask_app_module,
        "get_latest_articles",
        lambda limit=20: [
            {
                "id": 2,
                "source": "FP",
                "url": "https://fp.com/2",
                "title": "Newest title",
                "author": "Author 2",
                "article_text": "Text 2",
                "core_thesis": "Thesis 2",
                "detailed_abstract": "Abstract 2",
                "supporting_data_quotes": "Quotes 2",
                "date_added": "2023-01-02 10:00:00",
            },
            {
                "id": 1,
                "source": "FA",
                "url": "https://fa.com/1",
                "title": "Older title",
                "author": "Author 1",
                "article_text": "Text 1",
                "core_thesis": "Thesis 1",
                "detailed_abstract": "Abstract 1",
                "supporting_data_quotes": "Quotes 1",
                "date_added": "2023-01-01 10:00:00",
            },
        ],
    )

    response = client.get("/")
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
