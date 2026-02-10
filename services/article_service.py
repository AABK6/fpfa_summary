from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from models.article import Article
from models.sources import normalize_article_source


def resolve_articles_db_path() -> str:
    """Resolve the SQLite DB path with new and legacy env-var overrides."""
    # Prefer the newer variable, but keep legacy compatibility.
    env_path = os.getenv("ARTICLES_DB_PATH") or os.getenv("FPFA_DB_PATH")
    if env_path:
        return env_path

    repo_root = Path(__file__).resolve().parents[1]
    return str(repo_root / "articles.db")


class ArticleService:
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or resolve_articles_db_path()

    def get_latest_articles(self, limit: int = 10) -> list[Article]:
        """Fetch latest articles sorted by date_added DESC."""
        if limit <= 0 or not os.path.exists(self.db_path):
            return []

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute("PRAGMA table_info(articles)")
            available_columns = {row[1] for row in cursor.fetchall()}
            publication_date_expr = (
                "publication_date"
                if "publication_date" in available_columns
                else "NULL AS publication_date"
            )

            cursor.execute(
                """
                SELECT
                    id, source, url, title, author, article_text,
                    core_thesis, detailed_abstract, supporting_data_quotes,
                    {publication_date_expr}, date_added
                FROM articles
                ORDER BY datetime(date_added) DESC
                LIMIT ?
                """.format(publication_date_expr=publication_date_expr),
                (limit,),
            )
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            return []
        finally:
            conn.close()

        articles: list[Article] = []
        for row in rows:
            data = dict(row)
            try:
                data["source"] = normalize_article_source(data["source"])
            except ValueError:
                # Leave unknown source values untouched so one bad row doesn't break the API.
                pass
            articles.append(Article(**data))

        return articles
