from __future__ import annotations

from sqlalchemy import insert

from services.article_repository import ArticleRepository, normalize_database_url, resolve_database_url
from services.article_repository import articles_table


def test_resolve_database_url_prefers_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/runtime.db")
    assert resolve_database_url() == "sqlite:////tmp/runtime.db"


def test_normalize_database_url_converts_sqlserver_url_to_pymssql():
    assert (
        normalize_database_url(
            "sqlserver://user:pass@example.database.windows.net:1433/fpfa"
            "?driver=ODBC+Driver+18+for+SQL+Server"
        )
        == "mssql+pymssql://user:pass@example.database.windows.net:1433/fpfa"
    )


def test_normalize_database_url_converts_connection_string_to_pymssql():
    assert (
        normalize_database_url(
            "Server=tcp:example.database.windows.net,1433;Database=fpfa;"
            "Uid=user;Pwd=pass;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
        )
        == "mssql+pymssql://user:pass@example.database.windows.net:1433/fpfa"
    )


def test_normalize_database_url_converts_odbc_connect_wrapper_to_pymssql():
    assert (
        normalize_database_url(
            "mssql+pyodbc:///?odbc_connect="
            "Server%3Dtcp%3Aexample.database.windows.net%2C1433%3B"
            "Database%3Dfpfa%3BUid%3Duser%3BPwd%3Dpass%3BEncrypt%3Dyes%3B"
        )
        == "mssql+pymssql://user:pass@example.database.windows.net:1433/fpfa"
    )


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


def test_repository_normalizes_publication_date_and_repairs_future_values(tmp_path):
    repo = ArticleRepository(sqlite_path=str(tmp_path / "repo.db"))
    try:
        inserted_iso = repo.insert_article(
            source="Foreign Affairs",
            url="https://fa.com/iso",
            title="ISO",
            author="Author A",
            article_text="Text",
            core_thesis="Core",
            detailed_abstract="Abstract",
            supporting_data_quotes="Quote",
            publication_date="2024-01-01T00:00:00-05:00",
        )
        inserted_future = repo.insert_article(
            source="Foreign Policy",
            url="https://foreignpolicy.com/2024/01/02/future-date/",
            title="Future",
            author="Author B",
            article_text="Text",
            core_thesis="Core",
            detailed_abstract="Abstract",
            supporting_data_quotes="Quote",
            publication_date="2099-01-01",
        )
        iso_row = repo.get_article_by_url("https://fa.com/iso")
        future_row = repo.get_article_by_url("https://foreignpolicy.com/2024/01/02/future-date/")
    finally:
        repo.close()

    assert inserted_iso is True
    assert inserted_future is True
    assert iso_row is not None
    assert future_row is not None
    assert iso_row["publication_date"] == "2024-01-01"
    assert future_row["publication_date"] == "2024-01-02"


def test_repository_normalizes_legacy_publication_dates_on_read(tmp_path):
    repo = ArticleRepository(sqlite_path=str(tmp_path / "repo.db"))
    try:
        with repo.engine.begin() as conn:
            conn.execute(
                insert(articles_table).values(
                    source="Foreign Policy",
                    url="https://foreignpolicy.com/2024/01/02/legacy-future/",
                    title="Legacy",
                    author="Author",
                    article_text="Text",
                    core_thesis="Core",
                    detailed_abstract="Abstract",
                    supporting_data_quotes="Quote",
                    publication_date="2099-01-01",
                )
            )
        row = repo.get_article_by_url("https://foreignpolicy.com/2024/01/02/legacy-future/")
    finally:
        repo.close()

    assert row is not None
    assert row["publication_date"] == "2024-01-02"
