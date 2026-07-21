from __future__ import annotations

import argparse
from collections.abc import Iterable

from models.sources import ArticleSource
from services.article_repository import ArticleRepository, resolve_articles_db_path
from services.gemini_summary_batch import (
    GeminiBatchClient,
    SummaryBatchError,
    prepare_summary_batch,
    reconcile_job,
    reconcile_open_batches,
    resolve_api_key,
    resolve_model,
)
from services.summary_batch_repository import PendingArticle, SummaryBatchRepository


def _normalized_sources(
    sources: Iterable[ArticleSource | str],
) -> tuple[ArticleSource, ...]:
    values: list[ArticleSource] = []
    for source in sources:
        normalized = (
            source if isinstance(source, ArticleSource) else ArticleSource(source)
        )
        if normalized not in values:
            values.append(normalized)
    return tuple(values)


def _collect_source(
    source: ArticleSource,
    *,
    article_repository: ArticleRepository,
    limit: int,
    excluded_urls: set[str],
) -> list[PendingArticle]:
    if source is ArticleSource.FOREIGN_AFFAIRS:
        from summarize_fa_hardened import collect_new_articles
    elif source is ArticleSource.FOREIGN_POLICY:
        from summarize_fp import collect_new_articles
    else:  # pragma: no cover - the enum makes this defensive only
        raise ValueError(f"Unsupported source: {source}")

    collected = collect_new_articles(
        article_repository,
        limit,
        excluded_urls=excluded_urls,
    )
    return [
        PendingArticle.from_mapping(article, source=source.value)
        for article in collected
    ]


def run_batch_ingestion(
    *,
    limit: int = 7,
    sources: Iterable[ArticleSource | str] = tuple(ArticleSource),
    article_repository: ArticleRepository | None = None,
    batch_repository: SummaryBatchRepository | None = None,
    api: GeminiBatchClient | None = None,
) -> int:
    """Reconcile old work, collect both publications, then submit one Gemini Batch."""
    if limit <= 0:
        print("[ERROR] limit must be positive")
        return 1

    active_sources = _normalized_sources(sources)
    if not active_sources:
        print("[ERROR] at least one source is required")
        return 1

    db_path = resolve_articles_db_path()
    owns_article_repository = article_repository is None
    owns_batch_repository = batch_repository is None
    articles = article_repository or ArticleRepository(sqlite_path=db_path)
    batches = batch_repository or SummaryBatchRepository(sqlite_path=db_path)

    def active_api() -> GeminiBatchClient:
        nonlocal api
        if api is None:
            api = GeminiBatchClient.from_api_key(resolve_api_key())
        return api

    try:
        open_jobs = batches.list_reconcilable_jobs()
        if open_jobs:
            reconciliation = reconcile_open_batches(
                article_repository=articles,
                batch_repository=batches,
                api=active_api(),
            )
            print(
                "[BATCH] Reconciliation: "
                f"checked={reconciliation.checked}, "
                f"completed={reconciliation.completed}, "
                f"pending={reconciliation.pending}, "
                f"failed={reconciliation.failed}, "
                f"errors={reconciliation.errors}"
            )
            if reconciliation.errors:
                print(
                    "[ERROR] Existing batch work could not be reconciled; no new batch submitted."
                )
                return 1

        excluded_urls = batches.open_urls()
        pending_articles: list[PendingArticle] = []
        for source in active_sources:
            source_articles = _collect_source(
                source,
                article_repository=articles,
                limit=limit,
                excluded_urls=excluded_urls,
            )
            pending_articles.extend(source_articles)
            excluded_urls.update(article.url for article in source_articles)
            print(f"[COLLECT] {source.value}: {len(source_articles)} new article(s)")

        if not pending_articles:
            print("[BATCH] No new articles to submit.")
            return 0

        job = prepare_summary_batch(
            batches,
            pending_articles,
            model=resolve_model(),
        )
        print(
            f"[BATCH] Prepared {job.id}: {job.request_count} article(s), "
            "one structured summary request per article."
        )
        try:
            outcome = reconcile_job(
                job,
                article_repository=articles,
                batch_repository=batches,
                api=active_api(),
            )
        except Exception as exc:
            code = (
                str(exc) if isinstance(exc, SummaryBatchError) else type(exc).__name__
            )
            batches.record_check_error(job.id, code)
            print(
                f"[ERROR] Batch submission failed ({code}); prepared work is kept for retry."
            )
            return 1

        print(f"[BATCH] Submitted {job.id}: {outcome}")
        return 0 if outcome != "FAILED" else 1
    finally:
        if owns_batch_repository:
            batches.close()
        if owns_article_repository:
            articles.close()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect FPFA articles and submit one asynchronous Gemini Batch."
    )
    parser.add_argument("limit", nargs="?", type=int, default=7)
    parser.add_argument(
        "--source",
        action="append",
        choices=[source.value for source in ArticleSource],
        help="Limit the run to one publication; may be repeated.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    selected_sources = args.source or [source.value for source in ArticleSource]
    return run_batch_ingestion(limit=args.limit, sources=selected_sources)


if __name__ == "__main__":
    raise SystemExit(main())
