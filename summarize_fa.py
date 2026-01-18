#!/usr/bin/env python3
"""
Scrape the latest Foreign Affairs pieces, bypass the paywall,
summarise them with Gemini, and cache everything in SQLite.

The script auto‑detects your undetected‑chromedriver version
and chooses the correct driver‑patching method, so it runs on
both v2.x and v3.x without manual tweaks.
"""

import os
import sys
import pickle
import sqlite3
import importlib
from contextlib import contextmanager
from pathlib import Path
from typing import List, Dict, Optional

# ───────────────────────── Selenium setup ────────────────────────────
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# ───────────────────────── Gemini SDK ────────────────────────────────
from google import genai
from google.genai import types  # noqa: F401  (imported for completeness)

# ───────────────────────── Constants ─────────────────────────────────
FA_BASE         = "https://www.foreignaffairs.com"
FA_LATEST       = f"{FA_BASE}/most-recent"
PAYWALL_PATTERN = "*/modules/custom/fa_paywall_js/js/paywall.js*"
COOKIES_PATH    = Path("fa_cookies.pkl")
DB_PATH         = Path("articles.db")
MAX_CF_RETRIES  = 3

# ───────────────────────── DB helpers ────────────────────────────────
def init_db(db_path: Path = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute(
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


def insert_article(conn: sqlite3.Connection, **row):
    keys = ", ".join(row.keys())
    qmarks = ", ".join("?" for _ in row)
    try:
        conn.execute(
            f"INSERT INTO articles ({keys}) VALUES ({qmarks})", tuple(row.values())
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # already stored


def fetch_article(conn: sqlite3.Connection, url: str):
    return conn.execute("SELECT * FROM articles WHERE url = ?", (url,)).fetchone()


# ───────────────────────── Driver patch helper ───────────────────────
def _patched_driver_path() -> str:
    """
    Return a fully patched chromedriver path that works on both
    undetected‑chromedriver v3.x (modern `install()`) and v2.x (legacy patcher).
    """
    uc_mod = importlib.reload(uc)  # ensure module fully initialised

    if hasattr(uc_mod, "install"):  # v3.x path
        return uc_mod.install()

    # v2.x fallback
    from undetected_chromedriver.patcher import Patcher
    return Patcher().patch_exe()


# ───────────────────────── Selenium context ──────────────────────────
@contextmanager
def selenium_session(headless: bool = True):
    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=400,300")

    driver = uc.Chrome(
        options=options,
        driver_executable_path=_patched_driver_path(),
    )

    # block FA paywall JS
    driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": [PAYWALL_PATTERN]})
    driver.execute_cdp_cmd("Network.enable", {})

    try:
        yield driver
    finally:
        driver.quit()


# ───────────────────────── Cookie helpers ────────────────────────────
def load_cookies(driver):
    if COOKIES_PATH.exists():
        driver.get(FA_BASE)  # must visit domain before adding cookies
        with COOKIES_PATH.open("rb") as f:
            for ck in pickle.load(f):
                if isinstance(ck.get("expiry"), float):
                    ck["expiry"] = int(ck["expiry"])
                try:
                    driver.add_cookie(ck)
                except Exception:
                    pass


def save_cookies(driver):
    COOKIES_PATH.write_bytes(pickle.dumps(driver.get_cookies()))


# ───────────────────────── Scraping utilities ────────────────────────
def _cloudflare_blocked(html: str) -> bool:
    return "Attention Required" in html or "cf-chl" in html


def _wait_for_article(driver):
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.TAG_NAME, "article"))
    )
    # remove overlay & force text visible
    driver.execute_script(
        """
        document.querySelectorAll(
          '.paywall, .loading-indicator, .unlock-article-message__container'
        ).forEach(el => el.remove());
        document.querySelectorAll('.dropcap-paragraph')
                .forEach(p => p.classList.add('loaded'));
    """
    )


def get_latest_urls(driver, n: int) -> List[str]:
    driver.get(FA_LATEST)
    _wait_for_article(driver)
    soup = BeautifulSoup(driver.page_source, "html.parser")

    urls, seen = [], set()
    for card in soup.select("div.card--large"):
        if len(urls) >= n:
            break
        link_el = card.select_one("h3.body-m a, h4.body-s a")
        if link_el and "podcasts" not in link_el["href"]:
            full = FA_BASE + link_el["href"]
            if full not in seen:
                urls.append(full)
                seen.add(full)
    return urls


def scrape_article(driver, url: str, retry: int = 0) -> Optional[Dict]:
    if retry >= MAX_CF_RETRIES:
        print(f"[!] Cloudflare keeps blocking after {MAX_CF_RETRIES} tries: {url}")
        return None

    driver.get(url)
    _wait_for_article(driver)
    html = driver.page_source
    if _cloudflare_blocked(html):
        print("[!] Cloudflare block – clearing cookies & retrying…")
        COOKIES_PATH.unlink(missing_ok=True)
        load_cookies(driver)
        return scrape_article(driver, url, retry + 1)

    soup = BeautifulSoup(html, "html.parser")

    title_tag = soup.select_one("h1.topper__title")
    author_tag = soup.select_one("h3.topper__byline")
    subtitle_tag = soup.select_one("h2.topper__subtitle")

    title = title_tag.get_text(strip=True) if title_tag else "Title Not Found"
    author = author_tag.get_text(strip=True) if author_tag else "Author Not Found"
    subtitle = subtitle_tag.get_text(strip=True) if subtitle_tag else ""

    article_el = (
        soup.select_one("article")
        or soup.select_one("div.article-body")
        or soup.select_one("div.Article__body")
        or soup.select_one("main")
    )

    text = (
        "\n\n".join(p.get_text(strip=True) for p in article_el.find_all("p"))
        if article_el
        else "Article Text Not Found"
    )

    return {
        "url": url,
        "title": title,
        "author": author,
        "subtitle": subtitle,
        "text": text,
    }


# ───────────────────────── Gemini helpers ────────────────────────────
def new_gemini_client() -> genai.Client:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        sys.exit("⚠️  Set GEMINI_API_KEY environment variable first.")
    return genai.Client(api_key=key)


def _gemini(client, model: str, prompt: str) -> str:
    try:
        return client.models.generate_content(model=model, contents=prompt).text.strip()
    except Exception as e:
        return f"⚠️ Generation failed: {e}"


def core_thesis(client, article) -> str:
    prompt = f"""
Write 1–2 dense sentences that capture the central argument or main conclusion
of this Foreign Affairs article (no supporting detail).

Title: {article['title']}
Author: {article['author']}
Text: {article['text']}
"""
    return _gemini(client, "gemini-1.5-flash-latest", prompt)


def detailed_abstract(client, article) -> str:
    prompt = f"""
Summarise the article in **two concise paragraphs**:
– first: outline essential background and framing;
– second: trace the argument’s progression and main evidence.
Remove all superfluous words.

Title: {article['title']}
Author: {article['author']}
Text: {article['text']}
"""
    return _gemini(client, "gemini-1.5-flash-latest", prompt)


def supporting_data(client, article) -> str:
    prompt = f"""
Extract and list:
• key factual data points / statistics;
• 2‑3 direct quotes that embody the article’s voice.

Bullet‑point format only.

Title: {article['title']}
Author: {article['author']}
Text: {article['text']}
"""
    return _gemini(client, "gemini-1.5-flash-latest", prompt)


# ───────────────────────── Main entry point ──────────────────────────
def main():
    num_articles = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    conn = init_db()
    gem = new_gemini_client()

    with selenium_session() as driver:
        load_cookies(driver)

        urls = get_latest_urls(driver, num_articles)
        if not urls:
            sys.exit("⚠️  No article URLs found.")

        save_cookies(driver)  # cache any new session cookies

        for url in urls:
            if fetch_article(conn, url):
                print(f"[✓] Already summarised: {url}")
                continue

            art = scrape_article(driver, url)
            if not art:
                continue

            thesis = core_thesis(gem, art)
            abstract = detailed_abstract(gem, art)
            quotes = supporting_data(gem, art)

            print(f"\n▶ {art['title']} — {art['author']}")
            print("  • Core thesis:", thesis)
            print("  • Abstract:\n", abstract)
            print("  • Data / Quotes:\n", quotes[:400], "…")  # trimmed for terminal

            insert_article(
                conn,
                source="Foreign Affairs",
                url=art["url"],
                title=art["title"],
                author=art["author"],
                article_text=art["text"],
                core_thesis=thesis,
                detailed_abstract=abstract,
                supporting_data_quotes=quotes,
            )

    conn.close()
    print("\n✅  Done.")


if __name__ == "__main__":
    main()
