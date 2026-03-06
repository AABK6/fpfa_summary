#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.article_repository import ArticleRepository, resolve_articles_db_path
from services.publication_dates import (
    extract_publication_date_from_soup,
    extract_publication_date_from_url,
    normalize_publication_date,
)


FP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class PlannedUpdate:
    article_id: int
    source: str
    title: str
    url: str
    old_value: str | None
    new_value: str | None
    reason: str


def fetch_article_html(source: str, url: str) -> str | None:
    if source == "Foreign Affairs":
        from summarize_fa_hardened import fetch_html as fetch_foreign_affairs_html

        return fetch_foreign_affairs_html(url)

    try:
        response = requests.get(url, headers={"User-Agent": FP_USER_AGENT}, timeout=20)
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        return None


def determine_repaired_date(source: str, url: str, current_value: str | None) -> tuple[str | None, str]:
    normalized_current = normalize_publication_date(current_value)
    if normalized_current is not None:
        if normalized_current == current_value:
            return normalized_current, "already_normalized"
        return normalized_current, "normalized_existing_value"

    html = fetch_article_html(source, url)
    if html:
        repaired = extract_publication_date_from_soup(BeautifulSoup(html, "html.parser"), url=url)
        if repaired is not None:
            return repaired, "re_scraped_source_html"

    url_date = extract_publication_date_from_url(url)
    if url_date is not None:
        return url_date, "url_fallback"

    return None, "unable_to_repair"


def build_updates(repo: ArticleRepository, *, limit: int | None = None) -> list[PlannedUpdate]:
    rows = repo.list_articles_with_publication_dates()
    updates: list[PlannedUpdate] = []

    for row in rows:
        new_value, reason = determine_repaired_date(
            row["source"],
            row["url"],
            row["publication_date"],
        )
        if new_value == row["publication_date"]:
            continue
        updates.append(
            PlannedUpdate(
                article_id=row["id"],
                source=row["source"],
                title=row["title"],
                url=row["url"],
                old_value=row["publication_date"],
                new_value=new_value,
                reason=reason,
            )
        )
        if limit is not None and len(updates) >= limit:
            break

    return updates


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize and repair article publication dates.")
    parser.add_argument("--db-path", default=resolve_articles_db_path())
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--apply", action="store_true", help="Write repaired dates back to the database.")
    args = parser.parse_args()

    repo = ArticleRepository(sqlite_path=args.db_path)
    try:
        updates = build_updates(repo, limit=args.limit)
        print(f"Planned updates: {len(updates)}")
        for update_row in updates[:20]:
            print(
                f"[{update_row.reason}] id={update_row.article_id} "
                f"{update_row.old_value!r} -> {update_row.new_value!r} | {update_row.title}"
            )

        if args.apply:
            for update_row in updates:
                repo.update_article_publication_date(update_row.article_id, update_row.new_value)
            print(f"Applied updates: {len(updates)}")
    finally:
        repo.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
