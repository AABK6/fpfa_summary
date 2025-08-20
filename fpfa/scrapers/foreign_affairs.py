from typing import List, Optional
import re
import logging
from bs4 import BeautifulSoup
from . import base
logger = logging.getLogger("fpfa.scrapers.fa")
BASE = "https://www.foreignaffairs.com"
MOST_RECENT = f"{BASE}/most-recent"


def list_urls(limit: int = 5) -> List[str]:
    """List latest Foreign Affairs article URLs (skip podcasts)."""
    session = base.build_session()
    resp = session.get(MOST_RECENT)
    if resp.status_code != 200:
        logger.warning("FA list request failed: %s", resp.status_code)
        return []
    soup = BeautifulSoup(resp.text, "lxml")
    urls: List[str] = []
    # Card layout links
    for card in soup.select("div.card--large"):
        if len(urls) >= limit:
            break
        a = card.select_one("h3.body-m a") or card.select_one("h4.body-s a")
        if not a or not a.get("href"):
            continue
        href = a["href"].strip()
        full = href if href.startswith("http") else f"{BASE}{href}"
        if "podcast" in full or "podcasts" in full:
            continue
        urls.append(full)
    logger.info("FA list extracted %d URL(s)", len(urls))
    return urls


def fetch_article(url: str) -> Optional[dict]:
    session = base.build_session()
    resp = session.get(url)
    if resp.status_code != 200:
        logger.warning("FA fetch failed %s: %s", url, resp.status_code)
        return None
    soup = BeautifulSoup(resp.text, "lxml")

    # Prefer meta og:title and multiple authors via article:author
    title_tag = soup.find("meta", property="og:title")
    title = title_tag["content"].strip() if title_tag and title_tag.get("content") else "Title not found"

    author_tags = soup.find_all("meta", property="article:author")
    authors = ", ".join(tag["content"].strip() for tag in author_tags if tag.get("content"))
    if not authors:
        # Fallback to visible byline if needed
        by = soup.select_one("h3.topper__byline")
        authors = by.get_text(strip=True) if by else "Author not found"

    # Main content container observed
    container = soup.find("div", class_="paywall-content")
    text = ""
    if container:
        parts = []
        for el in container.find_all(["p", "blockquote"]):
            t = el.get_text(strip=True)
            if t:
                parts.append(t)
        text = "\n\n".join(parts)

    if not text:
        logger.warning("FA empty article body for %s", url)
        return None

    return {"title": title, "author": authors, "text": text, "url": url}
