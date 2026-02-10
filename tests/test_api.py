import sqlite3
from urllib.parse import urlparse

import pytest

from models.sources import ArticleSource

REQUIRED_ARTICLE_KEYS = {
    "id",
    "source",
    "url",
    "title",
    "author",
    "article_text",
    "core_thesis",
    "detailed_abstract",
    "supporting_data_quotes",
    "date_added",
}


@pytest.fixture
def flask_client_with_db(tmp_path, monkeypatch):
    db_path = tmp_path / "flask_test_articles.db"
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
            date_added TEXT
        )
        """
    )
    conn.executemany(
        """
        INSERT INTO articles (
            source, url, title, author, article_text, core_thesis,
            detailed_abstract, supporting_data_quotes, date_added
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            ("FA", "https://fa.com/alpha", "Alpha", "A", "Text", "Thesis", "Abstract", "Quotes", "2023-01-03 10:00:00"),
            (ArticleSource.FOREIGN_POLICY.value, "https://fp.com/beta", "Beta", "B", "Text", "Thesis", "Abstract", "Quotes", "2023-01-02 10:00:00"),
            (ArticleSource.FOREIGN_AFFAIRS.value, "https://fa.com/gamma", "Gamma", "C", "Text", "Thesis", "Abstract", "Quotes", "2023-01-01 10:00:00"),
        ],
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv("ARTICLES_DB_PATH", str(db_path))

    from app import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_flask_health_endpoint(flask_client_with_db):
    response = flask_client_with_db.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}


def test_flask_api_articles_contract(flask_client_with_db):
    response = flask_client_with_db.get("/api/articles")
    assert response.status_code == 200

    data = response.get_json()
    assert isinstance(data, list)
    assert data, "Expected fixture-seeded results, got empty list"
    assert REQUIRED_ARTICLE_KEYS.issubset(data[0].keys())


def test_flask_api_articles_order_and_source_normalization(flask_client_with_db):
    response = flask_client_with_db.get("/api/articles")
    data = response.get_json()

    assert [item["title"] for item in data] == ["Alpha", "Beta", "Gamma"]
    assert [item["date_added"] for item in data] == [
        "2023-01-03 10:00:00",
        "2023-01-02 10:00:00",
        "2023-01-01 10:00:00",
    ]
    assert data[0]["source"] == ArticleSource.FOREIGN_AFFAIRS.value


def test_flask_api_articles_contract_url_serializable(flask_client_with_db):
    response = flask_client_with_db.get("/api/articles")
    data = response.get_json()

    for item in data:
        parsed = urlparse(item["url"])
        assert parsed.scheme in {"http", "https"}
        assert parsed.netloc


def test_flask_home_page_renders_key_content(flask_client_with_db):
    response = flask_client_with_db.get("/")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "<html" in body.lower()
    assert "styles.css" in body


@pytest.mark.parametrize(
    "date_added, expected_display",
    [
        ("2023-01-01 12:34:56", "January 1"),
        (None, "Unknown date"),
        ("not-a-date", "Unknown date"),
    ],
)
def test_flask_home_page_date_rendering(client, monkeypatch, date_added, expected_display):
    sample_articles = [
        {
            "id": 1,
            "source": "Foreign Policy",
            "url": "https://example.com/article",
            "title": "Sample Title",
            "author": "Sample Author",
            "article_text": "Text",
            "core_thesis": "Thesis",
            "detailed_abstract": "Abstract",
            "supporting_data_quotes": "Quote",
            "date_added": date_added,
        }
    ]

    monkeypatch.setattr("app.get_latest_articles", lambda limit=20: sample_articles)

    response = client.get("/")
    assert response.status_code == 200
    assert expected_display in response.get_data(as_text=True)
