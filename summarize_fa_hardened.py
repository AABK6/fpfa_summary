#!/usr/bin/env python3
"""
Hardened Foreign Affairs summariser
----------------------------------
Implements three changes requested 31 May 2025:
  1.  Uses Playwright + playwright‑stealth instead of Selenium/undetected‑chromedriver.
  2.  Checks the SQLite cache **before** loading a page, so we do not waste browser time on
      articles we already have.
  3.  All network calls have a bounded `MAX_RETRIES` (default=3) so Cloudflare loops
      can never hang the script again.

Extra perks:
  • Compatible with the other DB helpers already present in the repo.
  • Completely synchronous – no asyncio – to keep it drop‑in.
  • Requires two extra pip installs:playwri
        pip install playwright playwright-stealth
        playwright install chromium
"""

from __future__ import annotations

import os
import sys
import sqlite3
from typing import List, Dict

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from playwright_stealth import stealth  # pip install playwright-stealth
from google import genai  #  → works exactly as in the original script

# --------------------------------------------------------------------------------------
# Constants & configuration
# --------------------------------------------------------------------------------------
START_URL = "https://www.foreignaffairs.com/most-recent"
MAX_RETRIES = 3  # Hard‑cap on Cloudflare / navigation retries
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


# --------------------------------------------------------------------------------------
# Database helpers (identical to the original ones) ––––––––––––––––––––––––––––––––––––
# --------------------------------------------------------------------------------------
DB_PATH = "articles.db"


def init_db(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            url TEXT UNIQUE,
            title TEXT,
            author TEXT,
            article_text TEXT,
            core_thesis TEXT,
            detailed_abstract TEXT,
            supporting_data_quotes TEXT,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    return conn


def insert_article(
    conn,
    source,
    url,
    title,
    author,
    article_text,
    core_thesis,
    detailed_abstract,
    supporting_data_quotes,
):
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO articles
            (source, url, title, author, article_text,
             core_thesis, detailed_abstract, supporting_data_quotes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source,
                url,
                title,
                author,
                article_text,
                core_thesis,
                detailed_abstract,
                supporting_data_quotes,
            ),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # already cached


def get_article_by_url(conn, url):
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT title, author, article_text, core_thesis,
               detailed_abstract, supporting_data_quotes
        FROM articles WHERE url = ?
        """,
        (url,),
    )
    return cursor.fetchone()


# --------------------------------------------------------------------------------------
# Playwright helpers –––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––-
# --------------------------------------------------------------------------------------

def fetch_html(url: str, max_retries: int = MAX_RETRIES) -> str | None:
    """Return fully‑rendered HTML or *None* if Cloudflare beat us."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(user_agent=USER_AGENT, viewport={"width": 1280, "height": 800})
        page = context.new_page()
        stealth(page)  # ← zero‑cost, hides playwright fingerprints

        for attempt in range(1, max_retries + 1):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                # Simple Cloudflare detector
                if "Attention Required" in page.content() or "cf-chl" in page.content():
                    continue  # try again (browser stays open)
                return page.content()
            except PWTimeoutError:
                pass  # silently fall through to retry loop
        return None  # Give up – caller decides how to handle


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
                url = "https://www.foreignaffairs.com" + anchor["href"]
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
        text_parts = [p.get_text(strip=True) for p in article_body.find_all("p")]
        text = "\n\n".join(text_parts)

    return {
        "title": title,
        "subtitle": subtitle,
        "author": author,
        "text": text,
        "url": url,
    }


# --------------------------------------------------------------------------------------
# Gemini helpers (unchanged) –––––––––––––––––––––––––––––––––––––––––––––––––––––––––––-
# --------------------------------------------------------------------------------------

def create_client(api_key: str) -> genai.Client:  # type: ignore
    return genai.Client(api_key=api_key)


def generate_core_thesis(client, article):
    prompt = f"""
Task: Write 1‑2 dense sentences capturing the main conclusion or central argument.
Title: {article['title']}
Author: {article['author']}
Text: {article['text']}
"""
    return client.models.generate_content(model="gemini-2.0-flash", contents=prompt).text.strip()


def generate_detailed_abstract(client, article):
    prompt = f"""
Task: Provide two dense paragraphs summarising the article.
Title: {article['title']}
Author: {article['author']}
Text: {article['text']}
"""
    return client.models.generate_content(model="gemini-2.5-flash-preview-05-20", contents=prompt).text.strip()


def generate_supporting_data_quotes(client, article):
    prompt = f"""
Task: List key data points and 2‑3 direct quotes.
Title: {article['title']}
Author: {article['author']}
Text: {article['text']}
"""
    return client.models.generate_content(model="gemini-2.5-flash-preview-05-20", contents=prompt).text.strip()


# --------------------------------------------------------------------------------------
# Main entry point –––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––-
# --------------------------------------------------------------------------------------

def main():
    num_to_fetch = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    conn = init_db()

    # 1. Collect URLs
    urls = extract_latest_article_urls(num_to_fetch)
    if not urls:
        print("[ERROR] No article URLs found – Cloudflare or layout change? Aborting.")
        sys.exit(1)

    # 2. Summarise
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[ERROR] GEMINI_API_KEY env var not set.")
        sys.exit(1)
    client = create_client(api_key)

    for url in urls:
        cached = get_article_by_url(conn, url)
        if cached:
            title, author, *_ = cached
            print(f"[CACHE] {title} by {author}")
            continue  # Already summarised – skip heavy browser work

        article = extract_foreign_affairs_article(url)
        if not article:
            print(f"[WARN] Failed to fetch article at {url}")
            continue

        core = generate_core_thesis(client, article)
        abstract = generate_detailed_abstract(client, article)
        quotes = generate_supporting_data_quotes(client, article)

        insert_article(
            conn,
            source="Foreign Affairs",
            url=article["url"],
            title=article["title"],
            author=article["author"],
            article_text=article["text"],
            core_thesis=core,
            detailed_abstract=abstract,
            supporting_data_quotes=quotes,
        )
        print(f"[OK] Stored summary for {article['title']}")

    conn.close()


if __name__ == "__main__":
    main()
