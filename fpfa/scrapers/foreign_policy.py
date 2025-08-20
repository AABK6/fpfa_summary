from typing import List, Optional
import re
import logging
from bs4 import BeautifulSoup
from . import base
logger = logging.getLogger("fpfa.scrapers.fp")
BASE = "https://foreignpolicy.com"
LATEST = f"{BASE}/category/latest/"


def list_urls(limit: int = 5) -> List[str]:
    session = base.build_session()
    resp = session.get(LATEST)
    if resp.status_code != 200:
        logger.warning("FP list request failed: %s", resp.status_code)
        return []
    html = re.sub(r'<script[^>]+(?:piano\\.io|cxense\\.com)[^>]+></script>', '', resp.text)
    soup = BeautifulSoup(html, "lxml")
    urls: List[str] = []
    for container in soup.find_all('div', class_='blog-list-layout'):
        if len(urls) >= limit:
            break
        figure_tag = container.find('figure', class_='figure-image')
        if figure_tag:
            link_tag = figure_tag.find('a')
            if link_tag and 'href' in link_tag.attrs:
                full = link_tag['href']
                urls.append(full)
    logger.info("FP list extracted %d URL(s)", len(urls))
    return urls


def fetch_article(url: str) -> Optional[dict]:
    session = base.build_session()
    resp = session.get(url)
    if resp.status_code != 200:
        logger.warning("FP fetch failed %s: %s", url, resp.status_code)
        return None

    html = re.sub(r'<script[^>]+(?:piano\\.io|cxense\\.com)[^>]+></script>', '', resp.text)
    soup = BeautifulSoup(html, "lxml")

    title_elem = soup.select_one("div.hed-heading h1.hed")
    title = title_elem.get_text(strip=True) if title_elem else "No Title Found"

    meta_author = soup.find("meta", attrs={"name": "author"})
    if meta_author and meta_author.get("content"):
        author = meta_author["content"].strip()
    else:
        author_div = soup.select_one("div.author-bio-text")
        if author_div:
            author_text = author_div.get_text(strip=True)
            author = author_text.replace("By ", "").strip()
        else:
            author = "No Author Found"

    content_parts = []
    ungated = soup.select_one("div.content-ungated")
    if ungated:
        paragraphs = ungated.find_all("p")
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text:
                content_parts.append(text)

    gated = soup.select_one("div.content-gated--main-article")
    if gated:
        paragraphs = gated.find_all("p")
        for p in paragraphs:
            text = p.get_text(strip=True)
            if text:
                content_parts.append(text)

    article_body = "\n\n".join(content_parts)
    if not article_body:
        logger.warning("FP empty article body for %s", url)
        return None
    return {"title": title, "author": author, "text": article_body, "url": url}
