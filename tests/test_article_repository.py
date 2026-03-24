from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import insert

from services.article_repository import ArticleRepository, normalize_database_url, resolve_database_url
from services.article_repository import articles_table


def test_resolve_database_url_prefers_database_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/runtime.db")
    assert resolve_database_url() == "sqlite:////tmp/runtime.db"


def test_normalize_database_url_uses_pyodbc_for_sqlserver_url_when_available(monkeypatch):
    monkeypatch.setattr("services.article_repository._pyodbc_usable", lambda: True)
    assert (
        normalize_database_url(
            "sqlserver://user:pass@example.database.windows.net:1433/fpfa"
            "?driver=ODBC+Driver+18+for+SQL+Server"
        )
        == "mssql+pyodbc://user:pass@example.database.windows.net:1433/fpfa"
        "?driver=ODBC+Driver+18+for+SQL+Server"
    )


def test_normalize_database_url_converts_sqlserver_url_to_pymssql_when_pyodbc_unavailable(monkeypatch):
    monkeypatch.setattr("services.article_repository._pyodbc_usable", lambda: False)
    assert (
        normalize_database_url(
            "sqlserver://user:pass@example.database.windows.net:1433/fpfa"
            "?driver=ODBC+Driver+18+for+SQL+Server"
        )
        == "mssql+pymssql://user:pass@example.database.windows.net:1433/fpfa"
    )


def test_normalize_database_url_uses_odbc_connect_wrapper_when_pyodbc_available(monkeypatch):
    monkeypatch.setattr("services.article_repository._pyodbc_usable", lambda: True)
    assert normalize_database_url(
        "Server=tcp:example.database.windows.net,1433;Database=fpfa;"
        "Uid=user;Pwd=pass;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    ).startswith("mssql+pyodbc:///?odbc_connect=")


def test_normalize_database_url_converts_connection_string_to_pymssql_when_pyodbc_unavailable(monkeypatch):
    monkeypatch.setattr("services.article_repository._pyodbc_usable", lambda: False)
    assert (
        normalize_database_url(
            "Server=tcp:example.database.windows.net,1433;Database=fpfa;"
            "Uid=user;Pwd=pass;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
        )
        == "mssql+pymssql://user:pass@example.database.windows.net:1433/fpfa"
    )


def test_normalize_database_url_preserves_odbc_connect_wrapper_when_pyodbc_available(monkeypatch):
    monkeypatch.setattr("services.article_repository._pyodbc_usable", lambda: True)
    value = (
        "mssql+pyodbc:///?odbc_connect="
        "Server%3Dtcp%3Aexample.database.windows.net%2C1433%3B"
        "Database%3Dfpfa%3BUid%3Duser%3BPwd%3Dpass%3BEncrypt%3Dyes%3B"
    )
    assert normalize_database_url(value) == value


def test_normalize_database_url_converts_odbc_connect_wrapper_to_pymssql_when_pyodbc_unavailable(monkeypatch):
    monkeypatch.setattr("services.article_repository._pyodbc_usable", lambda: False)
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


@dataclass
class _FakeSnapshot:
    payload: dict[str, object] | None
    reference: "_FakeDocumentReference | None" = None

    @property
    def exists(self) -> bool:
        return self.payload is not None

    def to_dict(self) -> dict[str, object]:
        return dict(self.payload or {})


class _FakeDocumentReference:
    def __init__(self, storage: dict[str, dict[str, object]], document_id: str):
        self._storage = storage
        self._document_id = document_id

    def get(self) -> _FakeSnapshot:
        return _FakeSnapshot(self._storage.get(self._document_id), reference=self)

    def create(self, payload: dict[str, object]) -> None:
        if self._document_id in self._storage:
            raise FileExistsError
        self._storage[self._document_id] = dict(payload)

    def update(self, payload: dict[str, object]) -> None:
        if self._document_id not in self._storage:
            self._storage[self._document_id] = {}
        self._storage[self._document_id].update(payload)


class _FakeQuery:
    def __init__(self, collection: "_FakeCollection", rows: list[dict[str, object]] | None = None):
        self._collection = collection
        self._rows = rows

    def where(self, field: str, op: str, value: object) -> "_FakeQuery":
        assert op == "=="
        rows = [row for row in self._iter_rows() if row.get(field) == value]
        return _FakeQuery(self._collection, rows)

    def order_by(self, field: str, direction: str | None = None) -> "_FakeQuery":
        reverse = direction == _FakeFirestoreModule.Query.DESCENDING
        rows = sorted(
            self._iter_rows(),
            key=lambda row: row.get(field) or datetime.min.replace(tzinfo=timezone.utc),
            reverse=reverse,
        )
        return _FakeQuery(self._collection, rows)

    def limit(self, value: int) -> "_FakeQuery":
        return _FakeQuery(self._collection, self._iter_rows()[:value])

    def stream(self) -> list[_FakeSnapshot]:
        snapshots: list[_FakeSnapshot] = []
        for document_id, row in self._collection._items(self._rows):
            snapshots.append(
                _FakeSnapshot(
                    row,
                    reference=_FakeDocumentReference(self._collection._storage, document_id),
                )
            )
        return snapshots

    def _iter_rows(self) -> list[dict[str, object]]:
        return [dict(row) for _, row in self._collection._items(self._rows)]


class _FakeCollection(_FakeQuery):
    def __init__(self):
        self._storage: dict[str, dict[str, object]] = {}
        super().__init__(self)

    def document(self, document_id: str) -> _FakeDocumentReference:
        return _FakeDocumentReference(self._storage, document_id)

    def _items(
        self,
        rows: list[dict[str, object]] | None = None,
    ) -> list[tuple[str, dict[str, object]]]:
        if rows is None:
            return [(document_id, dict(row)) for document_id, row in self._storage.items()]

        indexed_rows: list[tuple[str, dict[str, object]]] = []
        for row in rows:
            url = str(row.get("url") or "")
            for document_id, candidate in self._storage.items():
                if candidate.get("url") != url:
                    continue
                indexed_rows.append((document_id, dict(candidate)))
                break
        return indexed_rows


class _FakeFirestoreClient:
    def __init__(self):
        self._collections: dict[str, _FakeCollection] = {}

    def collection(self, name: str) -> _FakeCollection:
        if name not in self._collections:
            self._collections[name] = _FakeCollection()
        return self._collections[name]


class _FakeFirestoreModule:
    class Query:
        DESCENDING = "DESCENDING"


def test_repository_supports_firestore_backend(monkeypatch):
    fake_client = _FakeFirestoreClient()

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("ARTICLE_STORE", "firestore")
    monkeypatch.setenv("FIRESTORE_PROJECT_ID", "pressreview-458312")
    monkeypatch.setenv("ARTICLES_COLLECTION", "articles")
    monkeypatch.setattr(
        "services.article_repository._create_firestore_client",
        lambda project_id: (fake_client, _FakeFirestoreModule),
    )
    monkeypatch.setattr(
        "services.article_repository._get_firestore_already_exists_exception",
        lambda: FileExistsError,
    )

    repo = ArticleRepository()
    try:
        inserted = repo.insert_article(
            source="Foreign Affairs",
            url="https://fa.com/firestore-one",
            title="One",
            author="Author A",
            article_text="Text",
            core_thesis="Core",
            detailed_abstract="Abstract",
            supporting_data_quotes="Quote",
            publication_date="2024-01-01",
            date_added="2024-01-02 03:04:05",
        )
        duplicate = repo.insert_article(
            source="Foreign Affairs",
            url="https://fa.com/firestore-one",
            title="Duplicate",
            author="Author B",
            article_text="Text",
            core_thesis="Core",
            detailed_abstract="Abstract",
            supporting_data_quotes="Quote",
            publication_date="2024-01-01",
        )
        repo.insert_article(
            source="Foreign Policy",
            url="https://fp.com/firestore-two",
            title="Two",
            author="Author C",
            article_text="Text",
            core_thesis="Core",
            detailed_abstract="Abstract",
            supporting_data_quotes="Quote",
            publication_date=None,
            date_added="2024-01-03 03:04:05",
        )
        latest = repo.get_latest_articles(limit=10)
        row = repo.get_article_by_url("https://fa.com/firestore-one")
        assert row is not None
        repo.update_article_publication_date(int(row["id"]), "2024-02-02")
        repo.update_article_date_added_by_url("https://fa.com/firestore-one", "2024-02-03 04:05:06")
        updated = repo.get_article_by_url("https://fa.com/firestore-one")
    finally:
        repo.close()

    assert repo.database_url == "firestore://pressreview-458312/articles"
    assert inserted is True
    assert duplicate is False
    assert [item["title"] for item in latest] == ["Two", "One"]
    assert row is not None
    assert row["publication_date"] == "2024-01-01"
    assert updated is not None
    assert updated["publication_date"] == "2024-02-02"
    assert updated["date_added"] == "2024-02-03 04:05:06"
