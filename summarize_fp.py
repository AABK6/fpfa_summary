import requests
from bs4 import BeautifulSoup
import re
import sys
import os

from models.sources import ArticleSource
from services.article_repository import ArticleRepository, resolve_articles_db_path
from services.publication_dates import extract_publication_date_from_soup
from services.document_limits import DocumentBudgetExceeded, collect_bounded_paragraphs, ensure_html_budget
from services.outbound_http import (
    OutboundPolicyError,
    PublisherPolicy,
    fetch_publisher_html,
    playwright_route_allowed,
    resolve_publisher_url,
    validate_publisher_url,
)

PUBLISHER_POLICY = PublisherPolicy(("foreignpolicy.com",))

# ======= DATABASE IMPORTS AND FUNCTIONS (MINIMAL ADDITION) =======
ALLOW_TRUNCATED_CONTENT = os.getenv("ALLOW_TRUNCATED_CONTENT", "0") == "1"

def init_db(db_path=None):
    """
    Creates (if not exists) a table 'articles' for storing article data.
    Includes a column 'article_text' to store the full text of the article.
    The URL is declared UNIQUE to skip duplicates.
    """
    database_url = os.getenv("DATABASE_URL")
    resolved_path = db_path or resolve_articles_db_path()
    return ArticleRepository(database_url=database_url, sqlite_path=resolved_path)

def insert_article(repo, source, url, title, author, article_text,
                   core_thesis, detailed_abstract, supporting_data_quotes, publication_date=None):
    """
    Inserts an article into the database table 'articles'.
    Skips if the URL is already present (UNIQUE constraint).
    """
    inserted = repo.insert_article(
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
    if inserted:
        print(f"Inserted article into DB: {title}")

def get_article_by_url(repo, url):
    """
    Returns (title, author, article_text, core_thesis, detailed_abstract, supporting_data_quotes) if present,
    or None if not found.
    """
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



def _normalize_paragraph_text(raw_text: str) -> str:
    text = re.sub(r"\s+", " ", raw_text).strip()
    if not text:
        return ""

    lower_text = text.lower()
    skip_markers = (
        "read more",
        "sign up",
        "newsletter",
        "advertisement",
        "most read",
        "podcast",
    )
    if any(marker in lower_text for marker in skip_markers):
        return ""

    return text


def _collect_paragraphs(container) -> list[str]:
    seen = set()
    cleaned_paragraphs: list[str] = []
    for paragraph in container.find_all("p"):
        candidate = _normalize_paragraph_text(paragraph.get_text(" ", strip=True))
        if not candidate:
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        cleaned_paragraphs.append(candidate)
    return collect_bounded_paragraphs(cleaned_paragraphs)


def _extract_fp_article_body(soup: BeautifulSoup) -> str:
    content_selectors = [
        "div.content-ungated",
        "div.content-gated--main-article",
        "article .article-content",
        "article",
        "main",
    ]

    for selector in content_selectors:
        container = soup.select_one(selector)
        if not container:
            continue

        paragraphs = _collect_paragraphs(container)
        if len(" ".join(paragraphs)) >= 400:
            return "\n\n".join(paragraphs)

    # Last-resort fallback: any paragraphs in the page, filtered + deduplicated.
    fallback_paragraphs = _collect_paragraphs(soup)
    return "\n\n".join(fallback_paragraphs)


def _fetch_html_via_playwright(url: str) -> str | None:
    """Optional JS-rendered fallback for pages where requests returns truncated HTML."""
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
    except Exception:
        return None

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                args=["--disable-dev-shm-usage"],
            )
            context = browser.new_context()
            page = context.new_page()
            context.route(
                "**/*",
                lambda route: route.continue_()
                if playwright_route_allowed(route.request.url, PUBLISHER_POLICY)
                else route.abort(),
            )
            validate_publisher_url(url, PUBLISHER_POLICY)
            page.goto(url, wait_until="networkidle", timeout=30000)
            validate_publisher_url(page.url, PUBLISHER_POLICY)
            html = ensure_html_budget(page.content())
            browser.close()
            return html
    except PWTimeoutError:
        return None
    except Exception:
        return None


def _is_likely_truncated(article_body: str) -> bool:
    paragraphs = [p for p in article_body.split("\n\n") if p.strip()]
    return len(article_body) < 900 and len(paragraphs) < 3


def _candidate_fetch_count(target_count: int) -> int:
    """Over-fetch candidate URLs so truncation-skipped articles don't fail the batch."""
    return max(target_count * 3, 10)


def collect_eligible_articles(article_urls: list[str], desired_count: int) -> tuple[list[dict], int, int]:
    """
    Scrape candidate URLs and keep up to the requested number of eligible articles.

    Returns:
        (eligible_articles, skipped_for_truncation, scrape_failures)
    """
    articles_data: list[dict] = []
    truncated_skips = 0
    scrape_failures = 0

    for url in article_urls:
        print(f"Scraping article from: {url}")
        article_data = scrape_foreignpolicy_article(url)
        if not article_data:
            scrape_failures += 1
            print(f"Failed to scrape article from: {url}")
            continue

        article_data["url"] = url
        if article_data.get("content_warning"):
            truncated_skips += 1
            print(f"[WARN] Extracted content may be truncated for URL: {url}")
            if not ALLOW_TRUNCATED_CONTENT:
                print(f"[SKIP] Skipping potentially truncated article: {url}")
                continue

        articles_data.append(article_data)
        if len(articles_data) >= desired_count:
            break

    return articles_data, truncated_skips, scrape_failures


"""
Usage:
    python summarize_fp.py [NUMBER_OF_ARTICLES_TO_SUMMARIZE]

Description:
    - Scrapes article URLs from Foreign Policy listing page.
    - Extracts text content from each article.
    - Summarizes each article using Gemini API.
"""

def scrape_foreignpolicy_article(url):
    """
    Fetch the Foreign Policy article, remove paywall references,
    and return the title, author, and full article text.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/100.0.4896.127 Safari/537.36"
        )
    }
    try:
        html = fetch_publisher_html(
            url,
            policy=PUBLISHER_POLICY,
            headers=headers,
            timeout=10,
        )
    except (requests.exceptions.RequestException, OutboundPolicyError, DocumentBudgetExceeded) as e:
        print(f"Error fetching URL {url}: {e}")
        return None

    html = re.sub(r'<script[^>]+(?:piano\\.io|cxense\\.com)[^>]+></script>', '', html)

    soup = BeautifulSoup(html, "html.parser")

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

    try:
        article_body = _extract_fp_article_body(soup)
    except DocumentBudgetExceeded:
        return None

    if _is_likely_truncated(article_body):
        rendered_html = _fetch_html_via_playwright(url)
        if rendered_html:
            rendered_soup = BeautifulSoup(rendered_html, "html.parser")
            try:
                rendered_body = _extract_fp_article_body(rendered_soup)
            except DocumentBudgetExceeded:
                rendered_body = ""
            if len(rendered_body) > len(article_body):
                article_body = rendered_body

    publication_date = extract_publication_date_from_soup(soup, url=url)

    return {
        "title": title,
        "author": author,
        "text": article_body,
        "publication_date": publication_date,
        "content_warning": "possibly_truncated" if _is_likely_truncated(article_body) else None,
    }

def scrape_foreignpolicy_article_list(num_links=3):
    """
    Fetches a Foreign Policy listing page and extracts article URLs.
    """
    url = "https://foreignpolicy.com/category/latest/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/100.0.4896.127 Safari/537.36"
        )
    }
    try:
        html_content = fetch_publisher_html(
            url,
            policy=PUBLISHER_POLICY,
            headers=headers,
            timeout=10,
        )
    except (requests.exceptions.RequestException, OutboundPolicyError, DocumentBudgetExceeded) as e:
        print(f"Error fetching article list: {e}")
        return []

    html_content = re.sub(r'<script[^>]+(?:piano\.io|cxense\\.com)[^>]+></script>', '', html_content)
    soup = BeautifulSoup(html_content, 'html.parser')

    article_urls = []
    article_containers = soup.find_all('div', class_='blog-list-layout')
    for container in article_containers:
        figure_tag = container.find('figure', class_='figure-image')
        if figure_tag:
            link_tag = figure_tag.find('a')
            if link_tag and 'href' in link_tag.attrs:
                try:
                    article_url = resolve_publisher_url(
                        url, link_tag["href"], PUBLISHER_POLICY
                    )
                except OutboundPolicyError:
                    continue
                article_urls.append(article_url)
                if len(article_urls) >= num_links:
                    break
    return article_urls

def collect_new_articles(
    repo,
    desired_count: int,
    *,
    excluded_urls: set[str] | None = None,
) -> list[dict]:
    """Scrape eligible, not-yet-stored Foreign Policy articles."""
    excluded = excluded_urls or set()
    article_urls = scrape_foreignpolicy_article_list(
        _candidate_fetch_count(desired_count)
    )
    if not article_urls:
        print("[ERROR] No Foreign Policy URLs found; parser or access may have changed.")
        return []

    candidates: list[str] = []
    for url in article_urls:
        if url in excluded:
            print(f"[PENDING] Foreign Policy article already queued: {url}")
            continue
        cached = get_article_by_url(repo, url)
        if cached:
            title, author, *_ = cached
            print(f"[CACHE] {title} by {author}")
            continue
        candidates.append(url)

    articles, truncated_skips, scrape_failures = collect_eligible_articles(
        candidates,
        desired_count,
    )
    if not articles and truncated_skips > 0 and scrape_failures == 0:
        print(
            "[WARN] No eligible Foreign Policy articles passed the truncation guard; "
            f"skipped={truncated_skips}. Treating this source as a no-op."
        )
    elif len(articles) < desired_count and candidates:
        print(
            f"[WARN] Collected {len(articles)} eligible Foreign Policy articles "
            f"out of requested {desired_count}."
        )
    return articles


def main() -> int:
    if len(sys.argv) < 2:
        num_articles_to_summarize = 10
    else:
        try:
            num_articles_to_summarize = int(sys.argv[1])
            if num_articles_to_summarize <= 0:
                print("Please provide a positive number of articles to summarize.")
                return 1
        except ValueError:
            print("Usage: python summarize_fp.py [NUMBER_OF_ARTICLES_TO_SUMMARIZE]")
            print("       Please provide a valid integer for the number of articles.")
            return 1

    from update_articles import run_batch_ingestion

    return run_batch_ingestion(
        limit=num_articles_to_summarize,
        sources=(ArticleSource.FOREIGN_POLICY,),
    )

if __name__ == "__main__":
    raise SystemExit(main())
