from typing import Iterable, List
import logging
from .config import load_config
from .db.repo import ArticleRepository
from .db.schema import ensure_schema

# Scrapers
from .scrapers import foreign_affairs as fa
from .scrapers import foreign_policy as fp


logger = logging.getLogger("fpfa.pipeline")


SCRAPERS = {
    "fa": fa,
    "foreign_affairs": fa,
    "fp": fp,
    "foreign_policy": fp,
}


def run_pipeline(sources: Iterable[str], limit: int, summarizer, persist: bool = True) -> int:
    """Discover, fetch, summarize, and optionally persist. Returns number inserted."""
    cfg = load_config()
    ensure_schema(cfg.db_path)
    repo = ArticleRepository(cfg.db_path)

    inserted = 0
    for src in sources:
        module = SCRAPERS.get(src.lower())
        if not module:
            logger.warning("Unknown source: %s", src)
            continue
        logger.info("Discovering URLs for source=%s limit=%s", src, limit)
        urls = module.list_urls(limit=limit)
        logger.info("Discovered %d URL(s) for %s", len(urls), src)
        for url in urls:
            logger.debug("Processing URL: %s", url)
            if repo.get_by_url(url):
                logger.info("Skipping existing URL: %s", url)
                continue
            logger.info("Fetching article: %s", url)
            article = module.fetch_article(url)
            if not article:
                logger.warning("Failed to fetch article: %s", url)
                continue
            title = article.get("title", "")
            author = article.get("author", "")
            text = article.get("text", "")
            # Summarize
            logger.info("Summarizing article: %s", title)
            core = summarizer.core_thesis(title, author, text)
            detail = summarizer.detailed_abstract(title, author, text)
            quotes = summarizer.supporting_quotes(title, author, text)
            # Persist (optional)
            if persist:
                logger.info("Inserting article into DB: %s", title)
                repo.insert_article(
                    source="Foreign Affairs" if module is fa else "Foreign Policy",
                    url=url,
                    title=title,
                    author=author,
                    article_text=text,
                    core_thesis=core,
                    detailed_abstract=detail,
                    supporting_data_quotes=quotes,
                )
            inserted += 1
    logger.info("Pipeline completed. Inserted %d article(s).", inserted)
    return inserted
