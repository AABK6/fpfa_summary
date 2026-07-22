import os
import sqlite3

import pytest

import services.article_service as article_service_module
from models.article import Article, ArticleSummary
from models.sources import ArticleSource
from services.article_service import ArticleService, sanitize_generated_text

TEST_DB = "test_articles.db"


@pytest.fixture
def article_service():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

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
            publication_date TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.executemany(
        """
        INSERT INTO articles (
            source,
            url,
            title,
            author,
            article_text,
            core_thesis,
            detailed_abstract,
            supporting_data_quotes,
            publication_date,
            date_added
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                ArticleSource.FOREIGN_AFFAIRS.value,
                "https://fa.com/1",
                "Title 1",
                "Author 1",
                "Text 1",
                "Thesis 1",
                "Abstract 1",
                "Quotes 1",
                "2022-12-25",
                "2023-01-01 10:00:00",
            ),
            (
                ArticleSource.FOREIGN_POLICY.value,
                "https://fp.com/2",
                "Title 2",
                "Author 2",
                "Text 2",
                "Thesis 2",
                "Abstract 2",
                "Quotes 2",
                None,
                "2023-01-02 10:00:00",
            ),
        ],
    )
    conn.commit()
    conn.close()

    service = ArticleService(db_path=TEST_DB)
    yield service

    service.close()
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_get_latest_articles(article_service):
    articles = article_service.get_latest_articles(limit=10)

    assert len(articles) == 2
    assert articles[0].title == "Title 2"
    assert articles[1].title == "Title 1"
    assert isinstance(articles[0], Article)
    assert [article.title for article in articles] == ["Title 2", "Title 1"]


def test_get_latest_articles_empty_db():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    conn = sqlite3.connect(TEST_DB)
    conn.execute("CREATE TABLE articles (id int)")
    conn.close()

    os.remove(TEST_DB)
    service = ArticleService(db_path=TEST_DB)
    articles = service.get_latest_articles()
    assert articles == []
    service.close()
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_get_latest_articles_includes_publication_date(article_service):
    articles = article_service.get_latest_articles(limit=10)

    assert articles[1].publication_date == "2022-12-25"
    assert articles[0].publication_date is None


def test_get_latest_article_summaries_excludes_body(article_service):
    summaries = article_service.get_latest_article_summaries(limit=10)

    assert len(summaries) == 2
    assert isinstance(summaries[0], ArticleSummary)
    assert "article_text" not in summaries[0].model_dump()


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("**Core Thesis:** A clear claim.", "A clear claim."),
        ("```markdown\nDetailed Abstract: Useful detail.\n```", "Useful detail."),
        ("Here is a summary of the article: Direct prose.", "Direct prose."),
    ],
)
def test_sanitize_generated_text_removes_wrappers(raw, expected):
    assert sanitize_generated_text(raw) == expected


def test_get_latest_articles_deduplicates_newest_title_and_url(article_service):
    conn = sqlite3.connect(TEST_DB)
    conn.executemany(
        """
        INSERT INTO articles (
            source, url, title, author, article_text, core_thesis,
            detailed_abstract, supporting_data_quotes, publication_date, date_added
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                ArticleSource.FOREIGN_POLICY.value,
                "https://fp.com/duplicate?utm_source=test",
                "Repeated Title",
                "Author",
                "Text",
                "Core Thesis: Newest version",
                "Abstract",
                "Quotes",
                None,
                "2023-01-05 10:00:00",
            ),
            (
                ArticleSource.FOREIGN_POLICY.value,
                "https://fp.com/duplicate",
                "Repeated Title",
                "Author",
                "Text",
                "Older version",
                "Abstract",
                "Quotes",
                None,
                "2023-01-04 10:00:00",
            ),
        ],
    )
    conn.commit()
    conn.close()

    articles = article_service.get_latest_articles(limit=10)

    repeated = [article for article in articles if article.title == "Repeated Title"]
    assert len(repeated) == 1
    assert repeated[0].core_thesis == "Newest version"


def test_cached_service_closes_previous_repository_when_configuration_changes(monkeypatch):
    created = []

    class FakeService:
        def __init__(self):
            self.closed = False
            created.append(self)

        def close(self):
            self.closed = True

    for variable in (
        "DATABASE_URL",
        "ARTICLES_DB_PATH",
        "FPFA_DB_PATH",
        "ARTICLE_STORE",
        "FIRESTORE_PROJECT_ID",
        "ARTICLES_COLLECTION",
    ):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(article_service_module, "ArticleService", FakeService)
    monkeypatch.setattr(article_service_module, "_cached_service", None)
    monkeypatch.setattr(article_service_module, "_cached_key", None)

    first = article_service_module.get_cached_article_service()
    same = article_service_module.get_cached_article_service()
    monkeypatch.setenv("ARTICLES_COLLECTION", "replacement")
    replacement = article_service_module.get_cached_article_service()

    assert same is first
    assert replacement is not first
    assert first.closed is True
    assert replacement.closed is False
    assert len(created) == 2
