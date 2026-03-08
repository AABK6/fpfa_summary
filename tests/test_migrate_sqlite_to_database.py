from __future__ import annotations

import sqlite3

from scripts.migrate_sqlite_to_database import migrate_rows, read_sqlite_rows
from services.article_repository import ArticleRepository


def _seed_source_db(path: str) -> None:
    conn = sqlite3.connect(path)
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
            publication_date TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        INSERT INTO articles (
            source, url, title, author, article_text,
            core_thesis, detailed_abstract, supporting_data_quotes, publication_date, date_added
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Foreign Affairs",
            "https://fa.com/migrate",
            "Migration Title",
            "Migration Author",
            "Migration text",
            "Migration core",
            "Migration abstract",
            "Migration quotes",
            "2024-03-03",
            "2024-03-04 05:06:07",
        ),
    )
    conn.commit()
    conn.close()


def test_migrate_rows_idempotent(tmp_path):
    source_db = tmp_path / "source.db"
    target_db = tmp_path / "target.db"
    _seed_source_db(str(source_db))

    rows = read_sqlite_rows(str(source_db))
    repo = ArticleRepository(sqlite_path=str(target_db))
    try:
        inserted, skipped = migrate_rows(rows, repo)
        inserted_second, skipped_second = migrate_rows(rows, repo)
        migrated = repo.get_article_by_url("https://fa.com/migrate")
    finally:
        repo.close()

    assert len(rows) == 1
    assert inserted == 1
    assert skipped == 0
    assert inserted_second == 0
    assert skipped_second == 1
    assert migrated is not None
    assert migrated["title"] == "Migration Title"


def test_migrate_rows_normalizes_future_publication_date_from_url(tmp_path):
    source_db = tmp_path / "source.db"
    target_db = tmp_path / "target.db"
    _seed_source_db(str(source_db))

    conn = sqlite3.connect(source_db)
    conn.execute(
        """
        INSERT INTO articles (
            source, url, title, author, article_text,
            core_thesis, detailed_abstract, supporting_data_quotes, publication_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "Foreign Policy",
            "https://foreignpolicy.com/2024/03/04/future-migrate",
            "Future Migration Title",
            "Migration Author",
            "Migration text",
            "Migration core",
            "Migration abstract",
            "Migration quotes",
            "2099-01-01",
        ),
    )
    conn.commit()
    conn.close()

    rows = read_sqlite_rows(str(source_db))
    repo = ArticleRepository(sqlite_path=str(target_db))
    try:
        migrate_rows(rows, repo)
        migrated = repo.get_article_by_url("https://foreignpolicy.com/2024/03/04/future-migrate")
    finally:
        repo.close()

    assert migrated is not None
    assert migrated["publication_date"] == "2024-03-04"


def test_migrate_rows_preserves_date_added(tmp_path):
    source_db = tmp_path / "source.db"
    target_db = tmp_path / "target.db"
    _seed_source_db(str(source_db))

    rows = read_sqlite_rows(str(source_db))
    repo = ArticleRepository(sqlite_path=str(target_db))
    try:
        migrate_rows(rows, repo)
        migrated = repo.get_article_by_url("https://fa.com/migrate")
    finally:
        repo.close()

    assert migrated is not None
    assert migrated["date_added"] == "2024-03-04 05:06:07"
