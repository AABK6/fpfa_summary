# This is a Python script for scraping a Foreign Policy page.
import requests
from bs4 import BeautifulSoup
import re

"""
Usage:
    python foreign_policy_scraper.py [URL]

Description:
    - Removes references to known paywall scripts.
    - Retrieves the title, author, and the full article text.
"""

def scrape_foreignpolicy_article(url):
    """
    Fetch the Foreign Policy article, remove paywall references,
    and return the title, author, and full article text.
    """

    #1 Consider using a session object (requests.Session) for repeated requests to improve performance.
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/100.0.4896.127 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    html = response.text

    #2 A compiled regex could be more efficient if used repeatedly.
    html = re.sub(r'<script[^>]+(?:piano\\.io|cxense\\.com)[^>]+></script>', '', html)

    soup = BeautifulSoup(html, "html.parser")

    title_elem = soup.select_one("div.hed-heading h1.hed")
    title = title_elem.get_text(strip=True) if title_elem else "No Title Found"

    #3 Consider adding error handling for situations when the author meta tag is missing.
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

    #4 Potentially unify logic for ungated and gated sections for simpler code.
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

    #5 You could also return structured data (e.g., paragraphs as a list) for more flexible usage.
    article_body = "\n\n".join(content_parts)

    return {
        "title": title,
        "author": author,
        "article": article_body
    }

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python foreign_policy_scraper.py [URL]")
        sys.exit(1)
    url = sys.argv[1]

    data = scrape_foreignpolicy_article(url)
    print("TITLE:\n", data["title"], "\n")
    print("AUTHOR:\n", data["author"], "\n")
    print("ARTICLE:\n", data["article"], "\n")

if __name__ == "__main__":
    main()
