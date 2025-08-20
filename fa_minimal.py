#!/usr/bin/env python3
"""
Minimal ForeignAffairs fetcher: prints Title, Author, and Article Text.

This simplified version focuses on the most direct and reliable selectors
for the target website's current structure.
"""

import sys

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: This script requires the 'requests' and 'beautifulsoup4' libraries.", file=sys.stderr)
    print("Please install them using: pip install requests beautifulsoup4 lxml", file=sys.stderr)
    sys.exit(1)

# A standard User-Agent to mimic a browser
UA_CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

def fetch_and_parse_article(url: str):
    """
    Fetches the article URL, parses the HTML, and prints the content.
    """
    # 1. Fetch the HTML content of the article
    try:
        headers = {"User-Agent": UA_CHROME}
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        html = response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}", file=sys.stderr)
        return

    # 2. Create a BeautifulSoup object to parse the HTML
    # 'lxml' is generally faster and more robust than 'html.parser'
    soup = BeautifulSoup(html, "lxml")

    # 3. Extract Title and Author using reliable meta tags
    # These are often more direct than parsing JSON-LD for this specific site
    title_tag = soup.find("meta", property="og:title")
    title = title_tag["content"] if title_tag else "Title not found"

    author_tags = soup.find_all("meta", property="article:author")
    authors = ", ".join(tag["content"] for tag in author_tags) if author_tags else "Author not found"

    # 4. Extract the article text from the main content container
    article_text = ""
    # The 'div.paywall-content' is the primary container for the article body.
    article_container = soup.find("div", class_="paywall-content")
    
    if article_container:
        # Find all paragraph and blockquote tags to reconstruct the article flow
        elements = article_container.find_all(['p', 'blockquote'])
        article_text = "\n\n".join(element.get_text(strip=True) for element in elements)
    
    if not article_text:
        print("Error: Could not extract article body. The website structure may have changed.", file=sys.stderr)
        return

    # 5. Print the extracted information
    print(f"Title: {title}")
    print(f"Author: {authors}\n")
    print(article_text)


if __name__ == "__main__":
    # --- Replace this URL with the article you want to fetch ---
    ARTICLE_URL = "https://www.foreignaffairs.com/china/real-china-model-wang-kroeber"
    
    if len(sys.argv) > 1:
        # Allow passing a URL as a command-line argument as a simple alternative
        fetch_and_parse_article(sys.argv[1])
    else:
        fetch_and_parse_article(ARTICLE_URL)
        