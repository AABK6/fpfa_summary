from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    insert,
    select,
    update,
)
from sqlalchemy.exc import IntegrityError

from services.article_repository import (
    _create_firestore_client,
    _get_firestore_already_exists_exception,
    _resolve_firestore_target,
    _should_use_firestore,
    resolve_database_url,
)


PREPARED = "PREPARED"
COMPLETED = "COMPLETED"
COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
FAILED = "FAILED"

PROVIDER_OPEN_STATES = frozenset(
    {
        "JOB_STATE_UNSPECIFIED",
        "JOB_STATE_QUEUED",
        "JOB_STATE_PENDING",
        "JOB_STATE_RUNNING",
        "JOB_STATE_CANCELLING",
        "JOB_STATE_PAUSED",
        "JOB_STATE_UPDATING",
    }
)
PROVIDER_TERMINAL_STATES = frozenset(
    {
        "JOB_STATE_SUCCEEDED",
        "JOB_STATE_FAILED",
        "JOB_STATE_CANCELLED",
        "JOB_STATE_EXPIRED",
        "JOB_STATE_PARTIALLY_SUCCEEDED",
    }
)
# Provider-terminal jobs stay reconcilable until their outputs (or failure) have
# been committed locally. This closes the crash window between API retrieval and
# final article writes.
RECONCILABLE_STATES = (
    frozenset({PREPARED}) | PROVIDER_OPEN_STATES | PROVIDER_TERMINAL_STATES
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def stable_url_id(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PendingArticle:
    source: str
    url: str
    title: str
    author: str
    text: str
    publication_date: str | None = None

    @classmethod
    def from_mapping(cls, value: dict[str, Any], *, source: str) -> "PendingArticle":
        return cls(
            source=source,
            url=str(value["url"]),
            title=str(value["title"]),
            author=str(value["author"]),
            text=str(value["text"]),
            publication_date=(
                str(value["publication_date"])
                if value.get("publication_date")
                else None
            ),
        )


@dataclass(frozen=True)
class SummaryBatchJob:
    id: str
    display_name: str
    model: str
    state: str
    request_count: int
    provider_batch_name: str = ""
    last_error: str = ""


@dataclass(frozen=True)
class SummaryBatchItem:
    id: str
    batch_id: str
    position: int
    request_key: str
    request_hash: str
    status: str
    article: PendingArticle


batch_metadata = MetaData()

summary_batch_jobs = Table(
    "gemini_summary_batches",
    batch_metadata,
    # The identifier is generated before any network call and is also used in
    # the provider display name. This is the anchor for interrupted submissions.
    # String lengths are deliberately conservative for SQL Server compatibility.
    Column("id", String(64), primary_key=True),
    Column("display_name", String(128), nullable=False, unique=True),
    Column("model", String(160), nullable=False),
    Column("state", String(48), nullable=False),
    Column("request_count", Integer, nullable=False),
    Column("provider_batch_name", String(256), nullable=False, default=""),
    Column("last_error", String(160), nullable=False, default=""),
    Column("created_at", DateTime, nullable=False),
    Column("updated_at", DateTime, nullable=False),
)

summary_batch_items = Table(
    "gemini_summary_batch_items",
    batch_metadata,
    Column("id", String(96), primary_key=True),
    Column("batch_id", String(64), nullable=False, index=True),
    Column("position", Integer, nullable=False),
    Column("request_key", String(96), nullable=False),
    Column("request_hash", String(64), nullable=False),
    Column("status", String(32), nullable=False),
    Column("url", String(2048), nullable=False),
    Column("article_json", Text, nullable=False),
)


def _article_json(article: PendingArticle) -> str:
    return json.dumps(asdict(article), ensure_ascii=False, sort_keys=True)


def _article_from_json(value: str) -> PendingArticle:
    return PendingArticle(**json.loads(value))


def _job_from_mapping(value: dict[str, Any]) -> SummaryBatchJob:
    return SummaryBatchJob(
        id=str(value["id"]),
        display_name=str(value["display_name"]),
        model=str(value["model"]),
        state=str(value["state"]),
        request_count=int(value["request_count"]),
        provider_batch_name=str(value.get("provider_batch_name") or ""),
        last_error=str(value.get("last_error") or ""),
    )


class _SqlSummaryBatchRepository:
    def __init__(self, *, database_url: str | None, sqlite_path: str | None):
        resolved_url = database_url or resolve_database_url(sqlite_path)
        self.engine = create_engine(resolved_url, pool_pre_ping=True)
        batch_metadata.create_all(self.engine)

    def close(self) -> None:
        self.engine.dispose()

    def prepare_batch(
        self,
        job: SummaryBatchJob,
        items: Iterable[SummaryBatchItem],
    ) -> bool:
        now = utc_now().replace(tzinfo=None)
        item_values = [
            {
                "id": item.id,
                "batch_id": item.batch_id,
                "position": item.position,
                "request_key": item.request_key,
                "request_hash": item.request_hash,
                "status": item.status,
                "url": item.article.url,
                "article_json": _article_json(item.article),
            }
            for item in items
        ]
        try:
            with self.engine.begin() as conn:
                conn.execute(
                    insert(summary_batch_jobs).values(
                        id=job.id,
                        display_name=job.display_name,
                        model=job.model,
                        state=job.state,
                        request_count=job.request_count,
                        provider_batch_name=job.provider_batch_name,
                        last_error=job.last_error,
                        created_at=now,
                        updated_at=now,
                    )
                )
                if item_values:
                    conn.execute(insert(summary_batch_items), item_values)
        except IntegrityError:
            return False
        return True

    def list_reconcilable_jobs(self) -> list[SummaryBatchJob]:
        stmt = (
            select(summary_batch_jobs)
            .where(summary_batch_jobs.c.state.in_(tuple(RECONCILABLE_STATES)))
            .order_by(summary_batch_jobs.c.created_at.asc())
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [_job_from_mapping(dict(row)) for row in rows]

    def get_items(self, batch_id: str) -> list[SummaryBatchItem]:
        stmt = (
            select(summary_batch_items)
            .where(summary_batch_items.c.batch_id == batch_id)
            .order_by(summary_batch_items.c.position.asc())
        )
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).mappings().all()
        return [
            SummaryBatchItem(
                id=str(row["id"]),
                batch_id=str(row["batch_id"]),
                position=int(row["position"]),
                request_key=str(row["request_key"]),
                request_hash=str(row["request_hash"]),
                status=str(row["status"]),
                article=_article_from_json(str(row["article_json"])),
            )
            for row in rows
        ]

    def update_provider(
        self,
        batch_id: str,
        *,
        provider_batch_name: str,
        state: str,
    ) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                update(summary_batch_jobs)
                .where(summary_batch_jobs.c.id == batch_id)
                .values(
                    provider_batch_name=provider_batch_name,
                    state=state,
                    last_error="",
                    updated_at=utc_now().replace(tzinfo=None),
                )
            )

    def record_check_error(self, batch_id: str, code: str) -> None:
        with self.engine.begin() as conn:
            conn.execute(
                update(summary_batch_jobs)
                .where(summary_batch_jobs.c.id == batch_id)
                .values(
                    last_error=code[:160], updated_at=utc_now().replace(tzinfo=None)
                )
            )

    def finalize(
        self,
        batch_id: str,
        *,
        state: str,
        item_statuses: dict[str, str],
        error: str = "",
    ) -> None:
        now = utc_now().replace(tzinfo=None)
        with self.engine.begin() as conn:
            for item_id, item_status in item_statuses.items():
                conn.execute(
                    update(summary_batch_items)
                    .where(summary_batch_items.c.id == item_id)
                    .values(status=item_status)
                )
            conn.execute(
                update(summary_batch_jobs)
                .where(summary_batch_jobs.c.id == batch_id)
                .values(state=state, last_error=error[:160], updated_at=now)
            )


class _FirestoreSummaryBatchRepository:
    def __init__(self, *, database_url: str | None):
        project_id, articles_collection = _resolve_firestore_target(database_url)
        self.client, _ = _create_firestore_client(project_id)
        prefix = os.getenv("FPFA_BATCH_COLLECTION_PREFIX", articles_collection).strip()
        prefix = prefix or articles_collection
        self.jobs = self.client.collection(f"{prefix}_gemini_batches")
        self.items = self.client.collection(f"{prefix}_gemini_batch_items")
        self._already_exists = _get_firestore_already_exists_exception()

    def close(self) -> None:
        return None

    @staticmethod
    def _job(snapshot: Any) -> SummaryBatchJob:
        payload = dict(snapshot.to_dict() or {})
        payload.setdefault("id", snapshot.id)
        return _job_from_mapping(payload)

    @staticmethod
    def _item(snapshot: Any) -> SummaryBatchItem:
        payload = dict(snapshot.to_dict() or {})
        article = PendingArticle(**dict(payload["article"]))
        return SummaryBatchItem(
            id=str(payload.get("id") or snapshot.id),
            batch_id=str(payload["batch_id"]),
            position=int(payload["position"]),
            request_key=str(payload["request_key"]),
            request_hash=str(payload["request_hash"]),
            status=str(payload["status"]),
            article=article,
        )

    def prepare_batch(
        self,
        job: SummaryBatchJob,
        items: Iterable[SummaryBatchItem],
    ) -> bool:
        now = utc_now()
        write_batch = self.client.batch()
        write_batch.create(
            self.jobs.document(job.id),
            {
                **asdict(job),
                "created_at": now,
                "updated_at": now,
            },
        )
        for item in items:
            write_batch.create(
                self.items.document(item.id),
                {
                    "id": item.id,
                    "batch_id": item.batch_id,
                    "position": item.position,
                    "request_key": item.request_key,
                    "request_hash": item.request_hash,
                    "status": item.status,
                    "url": item.article.url,
                    "article": asdict(item.article),
                },
            )
        try:
            write_batch.commit()
        except self._already_exists:
            return False
        return True

    def list_reconcilable_jobs(self) -> list[SummaryBatchJob]:
        snapshots = self.jobs.where(
            "state",
            "in",
            sorted(RECONCILABLE_STATES),
        ).stream()
        jobs = [self._job(snapshot) for snapshot in snapshots]
        return sorted(jobs, key=lambda job: job.id)

    def get_items(self, batch_id: str) -> list[SummaryBatchItem]:
        snapshots = self.items.where("batch_id", "==", batch_id).stream()
        return sorted(
            (self._item(snapshot) for snapshot in snapshots),
            key=lambda item: item.position,
        )

    def update_provider(
        self,
        batch_id: str,
        *,
        provider_batch_name: str,
        state: str,
    ) -> None:
        self.jobs.document(batch_id).update(
            {
                "provider_batch_name": provider_batch_name,
                "state": state,
                "last_error": "",
                "updated_at": utc_now(),
            }
        )

    def record_check_error(self, batch_id: str, code: str) -> None:
        self.jobs.document(batch_id).update(
            {"last_error": code[:160], "updated_at": utc_now()}
        )

    def finalize(
        self,
        batch_id: str,
        *,
        state: str,
        item_statuses: dict[str, str],
        error: str = "",
    ) -> None:
        write_batch = self.client.batch()
        for item_id, item_status in item_statuses.items():
            write_batch.update(self.items.document(item_id), {"status": item_status})
        write_batch.update(
            self.jobs.document(batch_id),
            {"state": state, "last_error": error[:160], "updated_at": utc_now()},
        )
        write_batch.commit()


class SummaryBatchRepository:
    """Persistent control ledger for asynchronous Gemini summary batches."""

    def __init__(
        self,
        database_url: str | None = None,
        sqlite_path: str | None = None,
    ):
        if _should_use_firestore(database_url):
            self._backend: _SqlSummaryBatchRepository | _FirestoreSummaryBatchRepository
            self._backend = _FirestoreSummaryBatchRepository(database_url=database_url)
        else:
            self._backend = _SqlSummaryBatchRepository(
                database_url=database_url,
                sqlite_path=sqlite_path,
            )

    def close(self) -> None:
        self._backend.close()

    def prepare_batch(
        self,
        job: SummaryBatchJob,
        items: Iterable[SummaryBatchItem],
    ) -> bool:
        return self._backend.prepare_batch(job, items)

    def list_reconcilable_jobs(self) -> list[SummaryBatchJob]:
        return self._backend.list_reconcilable_jobs()

    def get_items(self, batch_id: str) -> list[SummaryBatchItem]:
        return self._backend.get_items(batch_id)

    def open_urls(self) -> set[str]:
        urls: set[str] = set()
        for job in self.list_reconcilable_jobs():
            urls.update(item.article.url for item in self.get_items(job.id))
        return urls

    def update_provider(
        self,
        batch_id: str,
        *,
        provider_batch_name: str,
        state: str,
    ) -> None:
        self._backend.update_provider(
            batch_id,
            provider_batch_name=provider_batch_name,
            state=state,
        )

    def record_check_error(self, batch_id: str, code: str) -> None:
        self._backend.record_check_error(batch_id, code)

    def finalize(
        self,
        batch_id: str,
        *,
        state: str,
        item_statuses: dict[str, str],
        error: str = "",
    ) -> None:
        self._backend.finalize(
            batch_id,
            state=state,
            item_statuses=item_statuses,
            error=error,
        )
