from __future__ import annotations

import os

from models.article import Article
from models.sources import normalize_article_source
from services.article_repository import ArticleRepository, resolve_articles_db_path as _resolve_articles_db_path


def resolve_articles_db_path() -> str:
    return _resolve_articles_db_path()


class ArticleService:
    def __init__(self, db_path: str | None = None, database_url: str | None = None):
        self.repository = ArticleRepository(database_url=database_url, sqlite_path=db_path)

    def get_latest_articles(self, limit: int = 10) -> list[Article]:
        """Fetch latest articles sorted by date_added DESC."""
        rows = self.repository.get_latest_articles(limit=limit)

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


_cached_service: ArticleService | None = None
_cached_key: tuple[str | None, str | None, str | None] | None = None


def get_cached_article_service() -> ArticleService:
    global _cached_key, _cached_service
    key = (
        os.getenv("DATABASE_URL"),
        os.getenv("ARTICLES_DB_PATH"),
        os.getenv("FPFA_DB_PATH"),
    )
    if _cached_service is None or _cached_key != key:
        _cached_service = ArticleService()
        _cached_key = key
    return _cached_service
