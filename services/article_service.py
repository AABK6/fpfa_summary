from __future__ import annotations

import os
import logging
import re
import unicodedata
from urllib.parse import urlsplit

from pydantic import ValidationError

from models.article import Article, ArticleSummary
from models.sources import normalize_article_source
from services.article_repository import (
    ArticleRepository,
    resolve_articles_db_path as _resolve_articles_db_path,
)
from services.content_quality import sanitize_generated_text


logger = logging.getLogger(__name__)


def _normalized_title(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "")).casefold()
    return re.sub(r"[^a-z0-9]+", "", normalized)


def _canonical_url(value: object) -> str:
    parsed = urlsplit(str(value or "").strip())
    host = (parsed.hostname or "").casefold()
    if host.startswith("www."):
        host = host[4:]
    path = re.sub(r"/+", "/", parsed.path).rstrip("/").casefold()
    return f"{host}{path}"


def resolve_articles_db_path() -> str:
    return _resolve_articles_db_path()


class ArticleService:
    def __init__(self, db_path: str | None = None, database_url: str | None = None):
        self.repository = ArticleRepository(database_url=database_url, sqlite_path=db_path)

    def close(self) -> None:
        self.repository.close()

    def get_latest_articles(self, limit: int = 10) -> list[Article]:
        """Fetch, sanitize, and deduplicate newest-first articles."""
        bounded_limit = min(max(limit, 0), 50)
        if bounded_limit == 0:
            return []

        # Fetch beyond the requested page so duplicates and malformed rows do not
        # leave a short response. Repository ordering keeps the newest copy.
        fetch_limit = min(max(bounded_limit * 3, bounded_limit), 150)
        rows = self.repository.get_latest_articles(limit=fetch_limit)

        articles: list[Article] = []
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        for row in rows:
            data = dict(row)
            try:
                data["source"] = normalize_article_source(data["source"])
            except ValueError:
                logger.warning(
                    "Skipping article with unsupported source: %r",
                    data.get("source"),
                )
                continue

            data["title"] = re.sub(r"\s+", " ", str(data.get("title") or "")).strip()
            data["author"] = re.sub(r"\s+", " ", str(data.get("author") or "")).strip()
            for field in ("core_thesis", "detailed_abstract", "supporting_data_quotes"):
                data[field] = sanitize_generated_text(data.get(field))

            canonical_url = _canonical_url(data.get("url"))
            title_key = f"{data['source']}:{_normalized_title(data.get('title'))}"
            if canonical_url in seen_urls or title_key in seen_titles:
                continue

            try:
                article = Article(**data)
            except ValidationError as exc:
                logger.warning("Skipping malformed article row %r: %s", data.get("id"), exc)
                continue

            seen_urls.add(canonical_url)
            seen_titles.add(title_key)
            articles.append(article)
            if len(articles) == bounded_limit:
                break

        return articles

    def get_latest_article_summaries(self, limit: int = 10) -> list[ArticleSummary]:
        """Fetch the public projection without loading copyrighted body text."""
        bounded_limit = min(max(limit, 0), 50)
        if bounded_limit == 0:
            return []
        fetch_limit = min(max(bounded_limit * 3, bounded_limit), 150)
        rows = self.repository.get_latest_article_summaries(limit=fetch_limit)
        summaries: list[ArticleSummary] = []
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()
        for row in rows:
            data = dict(row)
            try:
                data["source"] = normalize_article_source(data["source"])
            except ValueError:
                logger.warning("Skipping article with unsupported source: %r", data.get("source"))
                continue
            data["title"] = re.sub(r"\s+", " ", str(data.get("title") or "")).strip()
            data["author"] = re.sub(r"\s+", " ", str(data.get("author") or "")).strip()
            for field in ("core_thesis", "detailed_abstract", "supporting_data_quotes"):
                data[field] = sanitize_generated_text(data.get(field))
            canonical_url = _canonical_url(data.get("url"))
            title_key = f"{data['source']}:{_normalized_title(data.get('title'))}"
            if canonical_url in seen_urls or title_key in seen_titles:
                continue
            try:
                summary = ArticleSummary(**data)
            except ValidationError as exc:
                logger.warning("Skipping malformed public article row %r: %s", data.get("id"), exc)
                continue
            seen_urls.add(canonical_url)
            seen_titles.add(title_key)
            summaries.append(summary)
            if len(summaries) == bounded_limit:
                break
        return summaries


_cached_service: ArticleService | None = None
_cached_key: tuple[str | None, str | None, str | None, str | None, str | None, str | None] | None = None


def get_cached_article_service() -> ArticleService:
    global _cached_key, _cached_service
    key = (
        os.getenv("DATABASE_URL"),
        os.getenv("ARTICLES_DB_PATH"),
        os.getenv("FPFA_DB_PATH"),
        os.getenv("ARTICLE_STORE"),
        os.getenv("FIRESTORE_PROJECT_ID"),
        os.getenv("ARTICLES_COLLECTION"),
    )
    if _cached_service is None or _cached_key != key:
        new_service = ArticleService()
        previous_service = _cached_service
        _cached_service = new_service
        _cached_key = key
        if previous_service is not None:
            try:
                previous_service.close()
            except Exception:
                logger.exception("Failed to close the previous article service")
    return _cached_service
