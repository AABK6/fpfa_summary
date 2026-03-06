#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.article_repository import ArticleRepository, articles_table, resolve_articles_db_path
from services.publication_dates import coerce_publication_date


SELECT_BASE = """
SELECT
    source,
    url,
    title,
    author,
    article_text,
    core_thesis,
    detailed_abstract,
    supporting_data_quotes,
    {publication_date_expr}
FROM articles
"""


def read_sqlite_rows(source_path: str) -> list[dict[str, Any]]:
    conn = sqlite3.connect(source_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(articles)")
    columns = {row[1] for row in cursor.fetchall()}
    publication_date_expr = "publication_date" if "publication_date" in columns else "NULL AS publication_date"

    cursor.execute(SELECT_BASE.format(publication_date_expr=publication_date_expr))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": str(row.get("source") or ""),
        "url": str(row.get("url") or ""),
        "title": str(row.get("title") or ""),
        "author": str(row.get("author") or ""),
        "article_text": str(row.get("article_text") or ""),
        "core_thesis": str(row.get("core_thesis") or ""),
        "detailed_abstract": str(row.get("detailed_abstract") or ""),
        "supporting_data_quotes": str(row.get("supporting_data_quotes") or ""),
        "publication_date": coerce_publication_date(
            row.get("publication_date"),
            url=str(row.get("url") or ""),
        ),
    }


def migrate_rows(rows: list[dict[str, Any]], repo: ArticleRepository, batch_size: int = 500) -> tuple[int, int]:
    inserted = 0
    skipped = 0

    normalized_rows = [_normalize_row(row) for row in rows]

    with repo.engine.begin() as conn:
        for start in range(0, len(normalized_rows), batch_size):
            chunk = normalized_rows[start : start + batch_size]
            try:
                conn.execute(insert(articles_table), chunk)
                inserted += len(chunk)
                continue
            except IntegrityError:
                pass

            # Fallback for duplicate-heavy chunks: retry row-by-row to keep progress.
            for payload in chunk:
                try:
                    conn.execute(insert(articles_table), payload)
                    inserted += 1
                except IntegrityError:
                    skipped += 1
    return inserted, skipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate local SQLite articles DB rows to DATABASE_URL target."
    )
    parser.add_argument(
        "--source",
        default=resolve_articles_db_path(),
        help="Path to source SQLite database (default: resolved articles DB path).",
    )
    parser.add_argument(
        "--target-url",
        default=os.getenv("DATABASE_URL"),
        help="Target database URL. If omitted, uses DATABASE_URL from environment.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target_url = args.target_url
    if not target_url:
        print("Error: target database URL missing. Set DATABASE_URL or pass --target-url.")
        return 1

    rows = read_sqlite_rows(args.source)
    repo = ArticleRepository(database_url=target_url)
    try:
        inserted, skipped = migrate_rows(rows, repo)
    finally:
        repo.close()

    print(
        f"Migration completed. Source rows={len(rows)}, inserted={inserted}, "
        f"skipped(existing/duplicate)={skipped}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
