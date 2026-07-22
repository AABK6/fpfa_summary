#!/usr/bin/env python3
"""
Hardened Foreign Affairs summariser
----------------------------------
Implements three changes requested 31 May 2025:
  1.  Uses plain HTTP requests by default (no Selenium / chromedriver required).
      Falls back to Playwright + stealth only if Cloudflare blocks requests.
  2.  Checks the SQLite cache **before** loading a page, so we do not waste browser time on
      articles we already have.
  3.  All network calls have a bounded `MAX_RETRIES` (default=3) so Cloudflare loops
      can never hang the script again.

Extra perks:
  • Compatible with the other DB helpers already present in the repo.
  • Completely synchronous – no asyncio – to keep it drop‑in.
  • Browser tooling is optional and only used as fallback:
        pip install playwright playwright-stealth
        playwright install chromium
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List

from bs4 import BeautifulSoup
import requests
from models.sources import ArticleSource
from services.article_repository import ArticleRepository, resolve_articles_db_path
from services.publication_dates import extract_publication_date_from_soup
from services.document_limits import (
    DocumentBudgetExceeded,
    collect_bounded_paragraphs,
    ensure_html_budget,
)
from services.outbound_http import (
    OutboundPolicyError,
    PublisherPolicy,
    fetch_publisher_html,
    playwright_route_allowed,
    resolve_publisher_url,
    validate_publisher_url,
)

# --------------------------------------------------------------------------------------
# Constants & configuration
# --------------------------------------------------------------------------------------
START_URL = "https://www.foreignaffairs.com/most-recent"
MAX_RETRIES = 3  # Hard‑cap on Cloudflare / navigation retries
REQUEST_TIMEOUT = 20
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
PUBLISHER_POLICY = PublisherPolicy(("foreignaffairs.com",))


# --------------------------------------------------------------------------------------
# Database helpers (identical to the original ones) ––––––––––––––––––––––––––––––––––––
# --------------------------------------------------------------------------------------
DB_PATH = resolve_articles_db_path()


def init_db(db_path: str = DB_PATH):
    database_url = os.getenv("DATABASE_URL")
    return ArticleRepository(database_url=database_url, sqlite_path=db_path)


def insert_article(
    repo,
    source,
    url,
    title,
    author,
    article_text,
    core_thesis,
    detailed_abstract,
    supporting_data_quotes,
    publication_date=None,
):
    repo.insert_article(
        source=source,
        url=url,
        title=title,
        author=author,
        article_text=article_text,
        core_thesis=core_thesis,
        detailed_abstract=detailed_abstract,
        supporting_data_quotes=supporting_data_quotes,
        publication_date=publication_date,
    )


def get_article_by_url(repo, url):
    row = repo.get_article_by_url(url)
    if not row:
        return None
    return (
        row.get("title"),
        row.get("author"),
        row.get("article_text"),
        row.get("core_thesis"),
        row.get("detailed_abstract"),
        row.get("supporting_data_quotes"),
    )


# --------------------------------------------------------------------------------------
# Fetch helpers –––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
# --------------------------------------------------------------------------------------

def _cloudflare_blocked(html: str) -> bool:
    return "Attention Required" in html or "cf-chl" in html


def _fetch_html_via_requests(url: str, max_retries: int) -> str | None:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }

    for _ in range(max_retries):
        try:
            html = fetch_publisher_html(
                url,
                policy=PUBLISHER_POLICY,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
            )
            if _cloudflare_blocked(html):
                continue
            return html
        except (requests.RequestException, OutboundPolicyError, DocumentBudgetExceeded):
            continue
    return None


def _fetch_html_via_playwright(url: str, max_retries: int) -> str | None:
    """
    Optional fallback used only when direct HTTP requests fail or are blocked.
    """
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
        from playwright_stealth import Stealth
    except Exception:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--disable-dev-shm-usage"],
            )
            context = browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            context.route(
                "**/*",
                lambda route: route.continue_()
                if playwright_route_allowed(route.request.url, PUBLISHER_POLICY)
                else route.abort(),
            )
            Stealth().apply_stealth_sync(page)

            for _ in range(max_retries):
                try:
                    validate_publisher_url(url, PUBLISHER_POLICY)
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    validate_publisher_url(page.url, PUBLISHER_POLICY)
                    html = ensure_html_budget(page.content())
                    if _cloudflare_blocked(html):
                        continue
                    return html
                except PWTimeoutError:
                    continue
            return None
    except Exception:
        return None


def fetch_html(url: str, max_retries: int = MAX_RETRIES) -> str | None:
    """
    Return HTML for a URL.
    Strategy:
      1) direct requests (no browser dependency)
      2) optional Playwright fallback if needed
    """
    html = _fetch_html_via_requests(url, max_retries=max_retries)
    if html:
        return html
    return _fetch_html_via_playwright(url, max_retries=max_retries)


# --------------------------------------------------------------------------------------
# Scraping logic –––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––-
# --------------------------------------------------------------------------------------

def extract_latest_article_urls(num_links: int = 3) -> List[str]:
    html = fetch_html(START_URL)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    article_cards = soup.find_all("div", class_="card--large")

    urls: List[str] = []
    for card in article_cards:
        if len(urls) >= num_links:
            break
        h_link = card.find(["h3", "h4"], class_=["body-m", "body-s"])
        if h_link:
            anchor = h_link.find("a")
            if anchor and anchor.has_attr("href"):
                try:
                    url = resolve_publisher_url(START_URL, anchor["href"], PUBLISHER_POLICY)
                except OutboundPolicyError:
                    continue
                if "podcast" not in url.lower():
                    urls.append(url)
    return urls


def extract_foreign_affairs_article(url: str) -> Dict[str, str] | None:
    html = fetch_html(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.find("h1", class_="topper__title")
    title = title_tag.get_text(strip=True) if title_tag else "Title Not Found"

    subtitle_tag = soup.find("h2", class_="topper__subtitle")
    subtitle = subtitle_tag.get_text(strip=True) if subtitle_tag else ""

    author_tag = soup.find("h3", class_="topper__byline")
    author = author_tag.get_text(strip=True) if author_tag else "Author Not Found"

    article_body = soup.find("article") or soup.find("div", class_="article-body") or soup.find("main")
    if not article_body:
        text = "Article Text Not Found"
    else:
        try:
            text_parts = collect_bounded_paragraphs(
                (p.get_text(" ", strip=True) for p in article_body.find_all("p"))
            )
        except DocumentBudgetExceeded:
            return None
        text = "\n\n".join(text_parts)

    publication_date = extract_publication_date_from_soup(soup, url=url)

    return {
        "title": title,
        "subtitle": subtitle,
        "author": author,
        "text": text,
        "url": url,
        "publication_date": publication_date,
    }


# --------------------------------------------------------------------------------------
# Collection helper –––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––
# --------------------------------------------------------------------------------------

def collect_new_articles(
    repo,
    desired_count: int,
    *,
    excluded_urls: set[str] | None = None,
) -> List[Dict[str, str]]:
    """Scrape eligible, not-yet-stored Foreign Affairs articles."""
    excluded = excluded_urls or set()
    candidate_count = max(desired_count * 3, 10)
    urls = extract_latest_article_urls(candidate_count)
    if not urls:
        print("[ERROR] No Foreign Affairs URLs found; parser or access may have changed.")
        return []

    articles: List[Dict[str, str]] = []
    for url in urls:
        if url in excluded:
            print(f"[PENDING] Foreign Affairs article already queued: {url}")
            continue
        cached = get_article_by_url(repo, url)
        if cached:
            title, author, *_ = cached
            print(f"[CACHE] {title} by {author}")
            continue
        article = extract_foreign_affairs_article(url)
        if not article:
            print(f"[WARN] Failed to fetch article at {url}")
            continue
        articles.append(article)
        if len(articles) >= desired_count:
            break
    return articles


# --------------------------------------------------------------------------------------
# Main entry point –––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––-
# --------------------------------------------------------------------------------------

def main() -> int:
    num_to_fetch = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    if num_to_fetch <= 0:
        print("Please provide a positive number of articles to collect.")
        return 1
    from update_articles import run_batch_ingestion

    return run_batch_ingestion(
        limit=num_to_fetch,
        sources=(ArticleSource.FOREIGN_AFFAIRS,),
    )


if __name__ == "__main__":
    raise SystemExit(main())
