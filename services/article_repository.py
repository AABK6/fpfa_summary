from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, quote_plus, unquote_plus, urlparse

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


def _pyodbc_usable() -> bool:
    try:
        import pyodbc  # noqa: F401
    except Exception:
        return False
    return True


def _is_firestore_url(value: str | None) -> bool:
    return bool(value and value.strip().startswith("firestore://"))


def _should_use_firestore(database_url: str | None) -> bool:
    if _is_firestore_url(database_url):
        return True
    return os.getenv("ARTICLE_STORE", "").strip().lower() == "firestore"


def _resolve_firestore_target(database_url: str | None = None) -> tuple[str, str]:
    project_id = os.getenv("FIRESTORE_PROJECT_ID", "").strip()
    collection = os.getenv("ARTICLES_COLLECTION", "articles").strip() or "articles"

    if _is_firestore_url(database_url):
        parsed = urlparse(str(database_url))
        if parsed.netloc:
            project_id = parsed.netloc
        if parsed.path.strip("/"):
            collection = parsed.path.strip("/")

    if not project_id:
        raise ValueError("FIRESTORE_PROJECT_ID is required when ARTICLE_STORE=firestore.")

    return project_id, collection


def normalize_database_url(raw_url: str) -> str:
    """Normalize common SQL Server connection-string formats to SQLAlchemy URLs."""
    value = raw_url.strip()
    if _is_firestore_url(value):
        return value

    def _build_pymssql_url(
        *,
        host: str,
        database: str,
        username: str | None = None,
        password: str | None = None,
        port: str | None = None,
    ) -> str:
        host = host.strip()
        if not host:
            raise ValueError("Database host cannot be empty.")

        auth = ""
        if username:
            auth = quote(username, safe="")
            if password is not None:
                auth += ":" + quote(password, safe="")
            auth += "@"

        host_port = host
        if port:
            host_port = f"{host}:{port}"

        return f"mssql+pymssql://{auth}{host_port}/{quote(database.strip('/'), safe='')}"

    def _server_to_host_port(server: str | None) -> tuple[str | None, str | None]:
        if not server:
            return None, None
        normalized = server.strip()
        if normalized.lower().startswith("tcp:"):
            normalized = normalized[4:]
        if "," in normalized:
            host, port = normalized.rsplit(",", 1)
            return host.strip() or None, port.strip() or None
        return normalized or None, None

    def _connection_string_parts(connection_string: str) -> dict[str, str]:
        parts: dict[str, str] = {}
        for segment in connection_string.split(";"):
            if "=" not in segment:
                continue
            key, part_value = segment.split("=", 1)
            parts[key.strip().lower()] = part_value.strip()
        return parts

    def _pymssql_url_from_connection_string(connection_string: str) -> str | None:
        parts = _connection_string_parts(connection_string)
        host, port = _server_to_host_port(
            parts.get("server")
            or parts.get("data source")
            or parts.get("address")
            or parts.get("addr")
            or parts.get("network address")
        )
        database = parts.get("database") or parts.get("initial catalog")
        username = (
            parts.get("uid")
            or parts.get("user id")
            or parts.get("user")
            or parts.get("username")
        )
        password = parts.get("pwd") or parts.get("password")
        if not host or not database:
            return None
        return _build_pymssql_url(
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
        )

    if value.startswith("mssql+pyodbc:///?odbc_connect="):
        if _pyodbc_usable():
            return value
        parsed = urlparse(value)
        encoded_connection_string = parse_qs(parsed.query).get("odbc_connect", [None])[0]
        if encoded_connection_string:
            converted = _pymssql_url_from_connection_string(unquote_plus(encoded_connection_string))
            if converted:
                return converted

    if value.startswith("sqlserver://"):
        if _pyodbc_usable():
            return "mssql+pyodbc://" + value[len("sqlserver://") :]
        parsed = urlparse(value)
        if parsed.hostname and parsed.path:
            return _build_pymssql_url(
                host=parsed.hostname,
                port=str(parsed.port) if parsed.port else None,
                database=parsed.path.lstrip("/"),
                username=parsed.username,
                password=parsed.password,
            )

    if value.startswith("mssql+pyodbc://"):
        if _pyodbc_usable():
            return value
        parsed = urlparse(value)
        if parsed.hostname and parsed.path:
            return _build_pymssql_url(
                host=parsed.hostname,
                port=str(parsed.port) if parsed.port else None,
                database=parsed.path.lstrip("/"),
                username=parsed.username,
                password=parsed.password,
            )

    if "://" in value:
        return value

    if "Server=" in value and "Database=" in value:
        if _pyodbc_usable():
            return f"mssql+pyodbc:///?odbc_connect={quote_plus(value)}"
        converted = _pymssql_url_from_connection_string(value)
        if converted:
            return converted
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


def _parse_date_added(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        text_value = str(value).strip()
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
            try:
                parsed = datetime.strptime(text_value, fmt)
                break
            except ValueError:
                continue
        else:
            parsed = datetime.fromisoformat(text_value)

    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed.replace(microsecond=0)


def _firestore_timestamp(value: Any) -> datetime:
    parsed = _parse_date_added(value) or datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
    return parsed.replace(tzinfo=timezone.utc)


def _format_date_added(value: Any) -> str | None:
    parsed = _parse_date_added(value)
    if parsed is None:
        return None
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def _stable_article_id(url: str) -> int:
    # Keep IDs JSON-safe for JS clients by staying under 53 bits.
    return int(hashlib.sha256(url.encode("utf-8")).hexdigest()[:13], 16)


def _firestore_document_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _create_firestore_client(project_id: str) -> tuple[Any, Any]:
    from google.cloud import firestore

    return firestore.Client(project=project_id), firestore


def _get_firestore_already_exists_exception():
    from google.api_core.exceptions import AlreadyExists

    return AlreadyExists


class _SqlArticleRepository:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine: Engine = create_engine(database_url, future=True, pool_pre_ping=True)
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
        date_added: Any = None,
    ) -> bool:
        payload = {
            "source": source,
            "url": url,
            "title": title,
            "author": author,
            "article_text": article_text,
            "core_thesis": core_thesis,
            "detailed_abstract": detailed_abstract,
            "supporting_data_quotes": supporting_data_quotes,
            "publication_date": coerce_publication_date(publication_date, url=url),
        }
        parsed_date_added = _parse_date_added(date_added)
        if parsed_date_added is not None:
            payload["date_added"] = parsed_date_added
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

    def update_article_date_added_by_url(self, url: str, date_added: Any) -> None:
        parsed_date_added = _parse_date_added(date_added)
        if parsed_date_added is None:
            return
        with self.engine.begin() as conn:
            conn.execute(
                update(articles_table)
                .where(articles_table.c.url == url)
                .values(date_added=parsed_date_added)
            )


class _FirestoreArticleRepository:
    def __init__(self, *, project_id: str, collection_name: str):
        self.project_id = project_id
        self.collection_name = collection_name
        self.client, self._firestore = _create_firestore_client(project_id)
        self.collection = self.client.collection(collection_name)
        self._already_exists = _get_firestore_already_exists_exception()

    def close(self) -> None:
        return None

    def ensure_schema(self) -> None:
        return None

    def _payload_from_doc(self, data: dict[str, Any]) -> dict[str, Any]:
        url = str(data.get("url") or "")
        payload = {
            "id": data.get("id") or _stable_article_id(url),
            "source": data.get("source"),
            "url": url,
            "title": data.get("title"),
            "author": data.get("author"),
            "article_text": data.get("article_text"),
            "core_thesis": data.get("core_thesis"),
            "detailed_abstract": data.get("detailed_abstract"),
            "supporting_data_quotes": data.get("supporting_data_quotes"),
            "publication_date": coerce_publication_date(data.get("publication_date"), url=url),
            "date_added": data.get("date_added") or _format_date_added(data.get("date_added_ts")),
        }
        return payload

    def get_latest_articles(self, limit: int = 20) -> list[dict[str, Any]]:
        if limit <= 0:
            return []

        docs = (
            self.collection
            .order_by("date_added_ts", direction=self._firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        return [self._payload_from_doc(doc.to_dict() or {}) for doc in docs]

    def get_article_by_url(self, url: str) -> dict[str, Any] | None:
        doc = self.collection.document(_firestore_document_id(url)).get()
        if doc.exists:
            return self._payload_from_doc(doc.to_dict() or {})

        matches = list(self.collection.where("url", "==", url).limit(1).stream())
        if not matches:
            return None
        return self._payload_from_doc(matches[0].to_dict() or {})

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
        date_added: Any = None,
    ) -> bool:
        payload = {
            "id": _stable_article_id(url),
            "source": source,
            "url": url,
            "title": title,
            "author": author,
            "article_text": article_text,
            "core_thesis": core_thesis,
            "detailed_abstract": detailed_abstract,
            "supporting_data_quotes": supporting_data_quotes,
            "publication_date": coerce_publication_date(publication_date, url=url),
            "date_added": _format_date_added(date_added)
            or _format_date_added(datetime.now(timezone.utc)),
            "date_added_ts": _firestore_timestamp(date_added),
        }
        try:
            self.collection.document(_firestore_document_id(url)).create(payload)
        except self._already_exists:
            return False
        return True

    def list_articles_with_publication_dates(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for doc in self.collection.stream():
            payload = self._payload_from_doc(doc.to_dict() or {})
            if payload.get("publication_date") is None:
                continue
            rows.append(
                {
                    "id": payload["id"],
                    "source": payload["source"],
                    "url": payload["url"],
                    "title": payload["title"],
                    "publication_date": payload["publication_date"],
                }
            )
        rows.sort(key=lambda item: int(item["id"]))
        return rows

    def _doc_for_article_id(self, article_id: int):
        matches = list(self.collection.where("id", "==", article_id).limit(1).stream())
        if not matches:
            return None
        return matches[0].reference

    def update_article_publication_date(self, article_id: int, publication_date: str | None) -> None:
        doc_ref = self._doc_for_article_id(article_id)
        if doc_ref is None:
            return
        doc_ref.update({"publication_date": publication_date})

    def update_article_date_added_by_url(self, url: str, date_added: Any) -> None:
        doc_ref = self.collection.document(_firestore_document_id(url))
        if not doc_ref.get().exists:
            return
        doc_ref.update(
            {
                "date_added": _format_date_added(date_added),
                "date_added_ts": _firestore_timestamp(date_added),
            }
        )


class ArticleRepository:
    def __init__(self, database_url: str | None = None, sqlite_path: str | None = None):
        if _should_use_firestore(database_url):
            project_id, collection_name = _resolve_firestore_target(database_url)
            self.database_url = f"firestore://{project_id}/{collection_name}"
            self.engine: Engine | None = None
            self._backend: _SqlArticleRepository | _FirestoreArticleRepository = _FirestoreArticleRepository(
                project_id=project_id,
                collection_name=collection_name,
            )
            self.ensure_schema()
            return

        resolved_url = normalize_database_url(database_url) if database_url else resolve_database_url(sqlite_path)
        self.database_url = resolved_url
        self._backend = _SqlArticleRepository(resolved_url)
        self.engine = self._backend.engine

    def close(self) -> None:
        self._backend.close()

    def ensure_schema(self) -> None:
        self._backend.ensure_schema()

    def get_latest_articles(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._backend.get_latest_articles(limit=limit)

    def get_article_by_url(self, url: str) -> dict[str, Any] | None:
        return self._backend.get_article_by_url(url)

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
        date_added: Any = None,
    ) -> bool:
        return self._backend.insert_article(
            source=source,
            url=url,
            title=title,
            author=author,
            article_text=article_text,
            core_thesis=core_thesis,
            detailed_abstract=detailed_abstract,
            supporting_data_quotes=supporting_data_quotes,
            publication_date=publication_date,
            date_added=date_added,
        )

    def list_articles_with_publication_dates(self) -> list[dict[str, Any]]:
        return self._backend.list_articles_with_publication_dates()

    def update_article_publication_date(self, article_id: int, publication_date: str | None) -> None:
        self._backend.update_article_publication_date(article_id, publication_date)

    def update_article_date_added_by_url(self, url: str, date_added: Any) -> None:
        self._backend.update_article_date_added_by_url(url, date_added)
