import sqlite3
from pathlib import Path
from urllib.parse import urlparse

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import app as flask_app_module
from main import app as fastapi_app
from main import get_article_service
from services.article_service import ArticleService

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
def temp_articles_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "articles_test.db"
    conn = sqlite3.connect(db_path)
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
            date_added TEXT
        )
        """
    )
    conn.commit()
    conn.close()
    return db_path


@pytest.fixture
def seeded_articles_db(temp_articles_db: Path) -> Path:
    conn = sqlite3.connect(temp_articles_db)
    conn.executemany(
        """
        INSERT INTO articles (
            source, url, title, author, article_text,
            core_thesis, detailed_abstract, supporting_data_quotes, date_added
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                "Foreign Affairs",
                "https://example.com/fa-1",
                "Alpha",
                "Author A",
                "Body A",
                "Thesis A",
                "Abstract A",
                "*Quote A",
                "2024-01-01 10:00:00",
            ),
            (
                "Foreign Policy",
                "https://example.com/fp-2",
                "Beta",
                "Author B",
                "Body B",
                "Thesis B",
                "Abstract B",
                "*Quote B",
                "2024-01-02 10:00:00",
            ),
            (
                "Foreign Affairs",
                "https://example.com/fa-3",
                "Gamma",
                "Author C",
                "Body C",
                "Thesis C",
                "Abstract C",
                "*Quote C",
                "2024-01-03 10:00:00",
            ),
        ],
    )
    conn.commit()
    conn.close()
    return temp_articles_db


@pytest.fixture
def flask_client_with_db(monkeypatch: pytest.MonkeyPatch, seeded_articles_db: Path):
    original_connect = flask_app_module.sqlite3.connect

    def connect_override(_: str):
        return original_connect(seeded_articles_db)

    monkeypatch.setattr(flask_app_module.sqlite3, "connect", connect_override)
    flask_app_module.app.config["TESTING"] = True
    with flask_app_module.app.test_client() as client:
        yield client


@pytest.fixture
def flask_client_empty_db(monkeypatch: pytest.MonkeyPatch, temp_articles_db: Path):
    original_connect = flask_app_module.sqlite3.connect

    def connect_override(_: str):
        return original_connect(temp_articles_db)

    monkeypatch.setattr(flask_app_module.sqlite3, "connect", connect_override)
    flask_app_module.app.config["TESTING"] = True
    with flask_app_module.app.test_client() as client:
        yield client


@pytest_asyncio.fixture
async def fastapi_client_with_seeded_db(seeded_articles_db: Path):
    service = ArticleService(db_path=str(seeded_articles_db))

    async def override_get_article_service():
        return service

    fastapi_app.dependency_overrides[get_article_service] = override_get_article_service
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def fastapi_client_with_empty_db(temp_articles_db: Path):
    service = ArticleService(db_path=str(temp_articles_db))

    async def override_get_article_service():
        return service

    fastapi_app.dependency_overrides[get_article_service] = override_get_article_service
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def fastapi_client_with_missing_table_db(tmp_path: Path):
    db_path = tmp_path / "missing_table.db"
    sqlite3.connect(db_path).close()
    service = ArticleService(db_path=str(db_path))

    async def override_get_article_service():
        return service

    fastapi_app.dependency_overrides[get_article_service] = override_get_article_service
    async with AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


def test_flask_api_articles_non_empty_and_required_keys(flask_client_with_db):
    response = flask_client_with_db.get("/api/articles")

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert data, "Expected fixture-seeded results, got empty list"
    assert REQUIRED_ARTICLE_KEYS.issubset(data[0].keys())


def test_flask_api_articles_deterministic_order_by_date_added(flask_client_with_db):
    response = flask_client_with_db.get("/api/articles")
    data = response.get_json()

    # Flask app reverses SQL DESC order before returning; assert that behavior is deterministic.
    assert [item["title"] for item in data] == ["Alpha", "Beta", "Gamma"]
    assert [item["date_added"] for item in data] == sorted(item["date_added"] for item in data)


def test_flask_api_articles_contract_url_serializable(flask_client_with_db):
    response = flask_client_with_db.get("/api/articles")
    data = response.get_json()

    for item in data:
        url = item["url"]
        parsed = urlparse(url)
        assert parsed.scheme in {"http", "https"}
        assert parsed.netloc


def test_flask_home_page_renders_key_content(flask_client_with_db):
    response = flask_client_with_db.get("/")

    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert '<div class="deck">' in body
    assert "Alpha" in body
    assert "styles.css" in body
    assert "script.js" in body


def test_flask_health_route_not_found():
    # Flask app intentionally does not expose /health route.
    flask_app_module.app.config["TESTING"] = True
    with flask_app_module.app.test_client() as client:
        response = client.get("/health")
    assert response.status_code == 404


def test_flask_empty_db_returns_empty_articles(flask_client_empty_db):
    response = flask_client_empty_db.get("/api/articles")

    assert response.status_code == 200
    assert response.get_json() == []


def test_flask_missing_table_returns_500(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "missing_table_flask.db"
    sqlite3.connect(db_path).close()

    original_connect = flask_app_module.sqlite3.connect

    def connect_override(_: str):
        return original_connect(db_path)

    monkeypatch.setattr(flask_app_module.sqlite3, "connect", connect_override)
    flask_app_module.app.config["TESTING"] = False

    with flask_app_module.app.test_client() as client:
        response = client.get("/api/articles")

    assert response.status_code == 500


@pytest.mark.asyncio
async def test_fastapi_api_articles_non_empty_and_required_keys(fastapi_client_with_seeded_db):
    response = await fastapi_client_with_seeded_db.get("/api/articles")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data, "Expected fixture-seeded results, got empty list"
    assert REQUIRED_ARTICLE_KEYS.issubset(data[0].keys())


@pytest.mark.asyncio
async def test_fastapi_api_articles_deterministic_order_by_date_added(fastapi_client_with_seeded_db):
    response = await fastapi_client_with_seeded_db.get("/api/articles")
    data = response.json()

    assert [item["title"] for item in data] == ["Gamma", "Beta", "Alpha"]
    assert [item["date_added"] for item in data] == sorted(
        (item["date_added"] for item in data), reverse=True
    )


@pytest.mark.asyncio
async def test_fastapi_api_articles_contract_url_valid_and_json_serializable(
    fastapi_client_with_seeded_db,
):
    response = await fastapi_client_with_seeded_db.get("/api/articles")
    data = response.json()

    for item in data:
        url = item["url"]
        parsed = urlparse(url)
        assert parsed.scheme in {"http", "https"}
        assert parsed.netloc

    assert "https://example.com/fa-1" in response.text


@pytest.mark.asyncio
async def test_fastapi_health_and_root_key_content(fastapi_client_with_seeded_db):
    health_response = await fastapi_client_with_seeded_db.get("/health")
    root_response = await fastapi_client_with_seeded_db.get("/")

    assert health_response.status_code == 200
    assert health_response.json()["status"] == "healthy"

    assert root_response.status_code == 200
    assert "text/html" in root_response.headers["content-type"]
    assert '<div class="deck">' in root_response.text
    assert "Gamma" in root_response.text
    assert "styles.css" in root_response.text


@pytest.mark.asyncio
async def test_fastapi_empty_db_returns_empty_articles(fastapi_client_with_empty_db):
    response = await fastapi_client_with_empty_db.get("/api/articles")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_fastapi_missing_table_returns_empty_articles(fastapi_client_with_missing_table_db):
    response = await fastapi_client_with_missing_table_db.get("/api/articles")

    assert response.status_code == 200
    assert response.json() == []
