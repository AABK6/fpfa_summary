from __future__ import annotations

import json
from types import SimpleNamespace

from models.sources import ArticleSource
from services.article_repository import ArticleRepository
from services.gemini_summary_batch import (
    ArticleSummary,
    GeminiBatchClient,
    prepare_summary_batch,
    reconcile_job,
)
from services.summary_batch_repository import PendingArticle, SummaryBatchRepository
from update_articles import run_batch_ingestion


def _article(url: str, source: str = "Foreign Affairs") -> PendingArticle:
    return PendingArticle(
        source=source,
        url=url,
        title=f"Title for {url}",
        author="Test Author",
        text="Substantial source text. " * 80,
        publication_date="2026-07-21",
    )


def _provider_job(
    *,
    state: str = "JOB_STATE_PENDING",
    display_name: str = "",
    responses: list[object] | None = None,
):
    return SimpleNamespace(
        name="batches/provider-123",
        display_name=display_name,
        state=SimpleNamespace(name=state),
        dest=(
            SimpleNamespace(inlined_responses=responses)
            if responses is not None
            else None
        ),
    )


class _FakeBatches:
    def __init__(self):
        self.listed: list[object] = []
        self.created: list[dict[str, object]] = []
        self.by_name: dict[str, object] = {}

    def list(self, *, config):
        assert config == {"page_size": 100}
        return list(self.listed)

    def create(self, **kwargs):
        self.created.append(kwargs)
        return _provider_job(
            display_name=str(kwargs["config"]["display_name"]),
        )

    def get(self, *, name):
        return self.by_name[name]


def _api(batches: _FakeBatches) -> GeminiBatchClient:
    return GeminiBatchClient(SimpleNamespace(batches=batches))


class _FirestoreSnapshot:
    def __init__(self, document_id: str, payload: dict[str, object]):
        self.id = document_id
        self._payload = payload

    def to_dict(self):
        return dict(self._payload)


class _FirestoreDocument:
    def __init__(self, collection, document_id: str):
        self.collection = collection
        self.id = document_id

    def update(self, payload):
        self.collection.storage[self.id].update(payload)


class _FirestoreQuery:
    def __init__(self, collection, field: str, operator: str, value):
        self.collection = collection
        self.field = field
        self.operator = operator
        self.value = value

    def stream(self):
        rows = self.collection.storage.items()
        if self.operator == "==":
            rows = (
                (key, row) for key, row in rows if row.get(self.field) == self.value
            )
        elif self.operator == "in":
            rows = (
                (key, row) for key, row in rows if row.get(self.field) in self.value
            )
        else:  # pragma: no cover - production code only uses these two operators
            raise AssertionError(self.operator)
        return [_FirestoreSnapshot(key, row) for key, row in rows]


class _FirestoreCollection:
    def __init__(self):
        self.storage: dict[str, dict[str, object]] = {}

    def document(self, document_id: str):
        return _FirestoreDocument(self, document_id)

    def stream(self):
        return [
            _FirestoreSnapshot(document_id, row)
            for document_id, row in self.storage.items()
        ]

    def where(self, field: str, operator: str, value):
        return _FirestoreQuery(self, field, operator, value)


class _FirestoreWriteBatch:
    def __init__(self):
        self.operations: list[tuple[str, object, dict[str, object]]] = []

    def create(self, reference, payload):
        self.operations.append(("create", reference, dict(payload)))

    def update(self, reference, payload):
        self.operations.append(("update", reference, dict(payload)))

    def commit(self):
        for operation, reference, _payload in self.operations:
            if operation == "create" and reference.id in reference.collection.storage:
                raise FileExistsError(reference.id)
        for operation, reference, payload in self.operations:
            if operation == "create":
                reference.collection.storage[reference.id] = payload
            else:
                reference.collection.storage[reference.id].update(payload)


class _FirestoreClient:
    def __init__(self):
        self.collections: dict[str, _FirestoreCollection] = {}

    def collection(self, name: str):
        return self.collections.setdefault(name, _FirestoreCollection())

    def batch(self):
        return _FirestoreWriteBatch()


def test_repository_persists_open_urls_and_terminal_state(tmp_path):
    repository = SummaryBatchRepository(sqlite_path=str(tmp_path / "state.db"))
    try:
        job = prepare_summary_batch(
            repository,
            [_article("https://example.com/one")],
            model="gemini-3.6-flash",
        )
        items = repository.get_items(job.id)

        assert repository.open_urls() == {"https://example.com/one"}
        assert len(items) == 1
        assert items[0].request_hash

        repository.update_provider(
            job.id,
            provider_batch_name="batches/provider-123",
            state="JOB_STATE_SUCCEEDED",
        )
        assert repository.list_reconcilable_jobs()[0].state == "JOB_STATE_SUCCEEDED"

        repository.finalize(
            job.id,
            state="COMPLETED",
            item_statuses={items[0].id: "COMPLETED"},
        )
        assert repository.open_urls() == set()
    finally:
        repository.close()


def test_repository_uses_persistent_firestore_ledger(monkeypatch):
    client = _FirestoreClient()
    monkeypatch.setenv("ARTICLE_STORE", "firestore")
    monkeypatch.setenv("FIRESTORE_PROJECT_ID", "ppf-fpfa-summary-prod")
    monkeypatch.setenv("ARTICLES_COLLECTION", "articles")
    monkeypatch.setattr(
        "services.summary_batch_repository._create_firestore_client",
        lambda _project_id: (client, object()),
    )
    monkeypatch.setattr(
        "services.summary_batch_repository._get_firestore_already_exists_exception",
        lambda: FileExistsError,
    )

    repository = SummaryBatchRepository()
    try:
        job = prepare_summary_batch(
            repository,
            [_article("https://example.com/firestore")],
            model="gemini-3.6-flash",
        )
        item = repository.get_items(job.id)[0]

        assert repository.open_urls() == {"https://example.com/firestore"}
        repository.update_provider(
            job.id,
            provider_batch_name="batches/provider-firestore",
            state="JOB_STATE_PENDING",
        )
        assert repository.list_reconcilable_jobs()[0].provider_batch_name == (
            "batches/provider-firestore"
        )

        repository.finalize(
            job.id,
            state="COMPLETED",
            item_statuses={item.id: "COMPLETED"},
        )
        assert repository.open_urls() == set()
    finally:
        repository.close()


def test_batch_create_uses_one_structured_request_per_article(tmp_path):
    from google.genai import types

    repository = SummaryBatchRepository(sqlite_path=str(tmp_path / "state.db"))
    batches = _FakeBatches()
    try:
        job = prepare_summary_batch(
            repository,
            [
                _article("https://example.com/one"),
                _article("https://example.com/two", "Foreign Policy"),
            ],
            model="gemini-3.6-flash",
        )
        provider = _api(batches).create(job=job, items=repository.get_items(job.id))
    finally:
        repository.close()

    assert provider.state == "JOB_STATE_PENDING"
    assert len(batches.created) == 1
    request = batches.created[0]
    assert request["model"] == "gemini-3.6-flash"
    assert len(request["src"]) == 2
    for inline in request["src"]:
        validated = types.InlinedRequest.model_validate(inline)
        assert validated.metadata
        assert inline["config"]["response_mime_type"] == "application/json"
        assert inline["config"]["response_schema"] is ArticleSummary
        prompt = inline["contents"][0]["parts"][0]["text"]
        assert "core_thesis" in prompt
        assert "detailed_abstract" in prompt
        assert "supporting_data_quotes" in prompt


def test_reconciliation_recovers_interrupted_create_by_display_name(tmp_path):
    repository = SummaryBatchRepository(sqlite_path=str(tmp_path / "state.db"))
    articles = ArticleRepository(sqlite_path=str(tmp_path / "state.db"))
    batches = _FakeBatches()
    try:
        job = prepare_summary_batch(
            repository,
            [_article("https://example.com/one")],
            model="gemini-3.6-flash",
        )
        batches.listed = [_provider_job(display_name=job.display_name)]

        outcome = reconcile_job(
            job,
            article_repository=articles,
            batch_repository=repository,
            api=_api(batches),
        )

        persisted = repository.list_reconcilable_jobs()
        assert outcome == "PENDING"
        assert batches.created == []
        assert persisted[0].provider_batch_name == "batches/provider-123"
    finally:
        articles.close()
        repository.close()


def test_successful_batch_writes_all_three_summary_fields(tmp_path):
    repository = SummaryBatchRepository(sqlite_path=str(tmp_path / "state.db"))
    articles = ArticleRepository(sqlite_path=str(tmp_path / "state.db"))
    batches = _FakeBatches()
    try:
        source = _article("https://example.com/one")
        job = prepare_summary_batch(
            repository,
            [source],
            model="gemini-3.6-flash",
        )
        output = {
            "core_thesis": "The article argues that durable policy needs a clear strategic centre.",
            "detailed_abstract": (
                "The first paragraph reconstructs the article's context and central reasoning.\n\n"
                "The second paragraph follows its consequences and final conclusion."
            ),
            "supporting_data_quotes": [
                "Fact: The article identifies three constraints.",
                'Quote: "A strategy without choices is only a list."',
            ],
        }
        responses = [
            SimpleNamespace(
                response=SimpleNamespace(text=json.dumps(output)),
                error=None,
            )
        ]
        batches.listed = [
            _provider_job(
                state="JOB_STATE_SUCCEEDED",
                display_name=job.display_name,
                responses=responses,
            )
        ]

        outcome = reconcile_job(
            job,
            article_repository=articles,
            batch_repository=repository,
            api=_api(batches),
        )
        stored = articles.get_article_by_url(source.url)

        assert outcome == "COMPLETED"
        assert stored is not None
        assert stored["core_thesis"] == output["core_thesis"]
        assert stored["detailed_abstract"] == output["detailed_abstract"]
        assert "- Fact:" in stored["supporting_data_quotes"]
        assert repository.list_reconcilable_jobs() == []
    finally:
        articles.close()
        repository.close()


def test_combined_ingestion_submits_one_batch_for_both_sources(monkeypatch, tmp_path):
    repository = SummaryBatchRepository(sqlite_path=str(tmp_path / "state.db"))
    articles = ArticleRepository(sqlite_path=str(tmp_path / "state.db"))
    batches = _FakeBatches()

    def fake_collect(source, **_kwargs):
        suffix = "fa" if source is ArticleSource.FOREIGN_AFFAIRS else "fp"
        return [_article(f"https://example.com/{suffix}", source.value)]

    monkeypatch.setattr("update_articles._collect_source", fake_collect)
    try:
        result = run_batch_ingestion(
            limit=1,
            sources=tuple(ArticleSource),
            article_repository=articles,
            batch_repository=repository,
            api=_api(batches),
        )
    finally:
        articles.close()
        repository.close()

    assert result == 0
    assert len(batches.created) == 1
    assert len(batches.created[0]["src"]) == 2
