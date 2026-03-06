from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy import DateTime, Index, Integer, MetaData, String, Table, Text
from sqlalchemy import Column, create_engine, func, insert, inspect, select, text, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

from services.publication_dates import coerce_publication_date


metadata = MetaData()

articles_table = Table(
    "articles",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("source", String(128), nullable=False),
    Column("url", String(2048), nullable=False, unique=True),
    Column("title", Text, nullable=False),
    Column("author", Text, nullable=False),
    Column("article_text", Text, nullable=False),
    Column("core_thesis", Text, nullable=False),
    Column("detailed_abstract", Text, nullable=False),
    Column("supporting_data_quotes", Text, nullable=False),
    Column("publication_date", String(128), nullable=True),
    Column("date_added", DateTime, nullable=False, server_default=func.current_timestamp()),
    sqlite_autoincrement=True,
)
Index("idx_articles_date", articles_table.c.date_added)


def resolve_articles_db_path() -> str:
    """Resolve SQLite DB path with new and legacy env-var overrides."""
    env_path = os.getenv("ARTICLES_DB_PATH") or os.getenv("FPFA_DB_PATH")
    if env_path:
        return env_path
    repo_root = Path(__file__).resolve().parents[1]
    return str(repo_root / "articles.db")


def normalize_database_url(raw_url: str) -> str:
    """Normalize common SQL Server connection-string formats to SQLAlchemy URLs."""
    value = raw_url.strip()
    if value.startswith("sqlserver://"):
        return "mssql+pyodbc://" + value[len("sqlserver://") :]
    if "://" in value:
        return value
    if "Server=" in value and "Database=" in value:
        return f"mssql+pyodbc:///?odbc_connect={quote_plus(value)}"
    return value


def resolve_database_url(sqlite_path: str | None = None) -> str:
    """Resolve runtime DB URL using DATABASE_URL first, else local SQLite path."""
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return normalize_database_url(database_url)

    db_path = sqlite_path or resolve_articles_db_path()
    return f"sqlite:///{Path(db_path).resolve()}"


def _serialize_value(value: Any, *, field: str) -> Any:
    if value is None:
        return None
    if isinstance(value, datetime):
        if field == "date_added":
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return value.isoformat()
    return value


class ArticleRepository:
    def __init__(self, database_url: str | None = None, sqlite_path: str | None = None):
        resolved_url = normalize_database_url(database_url) if database_url else resolve_database_url(sqlite_path)
        self.database_url = resolved_url
        self.engine: Engine = create_engine(resolved_url, future=True, pool_pre_ping=True)
        self.ensure_schema()

    def close(self) -> None:
        self.engine.dispose()

    def ensure_schema(self) -> None:
        metadata.create_all(self.engine, checkfirst=True)
        inspector = inspect(self.engine)
        if "articles" not in inspector.get_table_names():
            return

        existing_columns = {column["name"] for column in inspector.get_columns("articles")}
        if "publication_date" in existing_columns:
            return

        dialect = self.engine.dialect.name
        alter_sql = "ALTER TABLE articles ADD COLUMN publication_date TEXT NULL"
        if dialect.startswith("mssql"):
            alter_sql = "ALTER TABLE articles ADD publication_date NVARCHAR(128) NULL"

        with self.engine.begin() as conn:
            conn.execute(text(alter_sql))

    def get_latest_articles(self, limit: int = 20) -> list[dict[str, Any]]:
        if limit <= 0:
            return []
        stmt = (
            select(
                articles_table.c.id,
                articles_table.c.source,
                articles_table.c.url,
                articles_table.c.title,
                articles_table.c.author,
                articles_table.c.article_text,
                articles_table.c.core_thesis,
                articles_table.c.detailed_abstract,
                articles_table.c.supporting_data_quotes,
                articles_table.c.publication_date,
                articles_table.c.date_added,
            )
            .order_by(articles_table.c.date_added.desc())
            .limit(limit)
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()

        serialized: list[dict[str, Any]] = []
        for row in rows:
            payload = dict(row)
            payload["date_added"] = _serialize_value(payload.get("date_added"), field="date_added")
            payload["publication_date"] = coerce_publication_date(
                _serialize_value(payload.get("publication_date"), field="publication_date"),
                url=payload.get("url"),
            )
            serialized.append(payload)
        return serialized

    def get_article_by_url(self, url: str) -> dict[str, Any] | None:
        stmt = select(articles_table).where(articles_table.c.url == url).limit(1)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).mappings().first()
        if row is None:
            return None
        payload = dict(row)
        payload["date_added"] = _serialize_value(payload.get("date_added"), field="date_added")
        payload["publication_date"] = coerce_publication_date(
            _serialize_value(payload.get("publication_date"), field="publication_date"),
            url=payload.get("url"),
        )
        return payload

    def insert_article(
        self,
        *,
        source: str,
        url: str,
        title: str,
        author: str,
        article_text: str,
        core_thesis: str,
        detailed_abstract: str,
        supporting_data_quotes: str,
        publication_date: str | None = None,
    ) -> bool:
        normalized_publication_date = coerce_publication_date(publication_date, url=url)
        payload = {
            "source": source,
            "url": url,
            "title": title,
            "author": author,
            "article_text": article_text,
            "core_thesis": core_thesis,
            "detailed_abstract": detailed_abstract,
            "supporting_data_quotes": supporting_data_quotes,
            "publication_date": normalized_publication_date,
        }
        try:
            with self.engine.begin() as conn:
                conn.execute(insert(articles_table).values(**payload))
        except IntegrityError:
            return False
        return True

    def list_articles_with_publication_dates(self) -> list[dict[str, Any]]:
        stmt = (
            select(
                articles_table.c.id,
                articles_table.c.source,
                articles_table.c.url,
                articles_table.c.title,
                articles_table.c.publication_date,
            )
            .where(articles_table.c.publication_date.is_not(None))
            .order_by(articles_table.c.id.asc())
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [dict(row) for row in rows]

    def update_article_publication_date(self, article_id: int, publication_date: str | None) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                update(articles_table)
                .where(articles_table.c.id == article_id)
                .values(publication_date=publication_date)
            )
