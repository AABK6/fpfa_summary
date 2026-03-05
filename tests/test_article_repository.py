from __future__ import annotations

from services.article_repository import ArticleRepository, resolve_database_url


def test_resolve_database_url_prefers_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/runtime.db")
    assert resolve_database_url() == "sqlite:////tmp/runtime.db"


def test_resolve_database_url_falls_back_to_sqlite_path(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    expected = f"sqlite:///{(tmp_path / 'local.db').resolve()}"
    assert resolve_database_url(str(tmp_path / "local.db")) == expected


def test_repository_insert_get_latest_and_dedupe(tmp_path):
    repo = ArticleRepository(sqlite_path=str(tmp_path / "repo.db"))
    try:
        first_insert = repo.insert_article(
            source="Foreign Affairs",
            url="https://fa.com/one",
            title="One",
            author="Author A",
            article_text="Text",
            core_thesis="Core",
            detailed_abstract="Abstract",
            supporting_data_quotes="Quote",
            publication_date="2024-01-01",
        )
        duplicate_insert = repo.insert_article(
            source="Foreign Affairs",
            url="https://fa.com/one",
            title="Duplicate",
            author="Author B",
            article_text="Text",
            core_thesis="Core",
            detailed_abstract="Abstract",
            supporting_data_quotes="Quote",
            publication_date="2024-01-01",
        )
        second_insert = repo.insert_article(
            source="Foreign Policy",
            url="https://fp.com/two",
            title="Two",
            author="Author C",
            article_text="Text 2",
            core_thesis="Core 2",
            detailed_abstract="Abstract 2",
            supporting_data_quotes="Quote 2",
            publication_date=None,
        )

        latest = repo.get_latest_articles(limit=10)
    finally:
        repo.close()

    assert first_insert is True
    assert duplicate_insert is False
    assert second_insert is True
    assert len(latest) == 2
    assert latest[0]["title"] == "Two"
    assert latest[1]["title"] == "One"

    by_url = ArticleRepository(sqlite_path=str(tmp_path / "repo.db"))
    try:
        row = by_url.get_article_by_url("https://fa.com/one")
    finally:
        by_url.close()

    assert row is not None
    assert row["title"] == "One"
