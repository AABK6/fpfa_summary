# This Python script scrapes a Foreign Policy listing page to extract article URLs.
import requests
from bs4 import BeautifulSoup
import re

"""
Usage:
    python foreign_policy_scraper.py

Description:
    - Retrieves a list of article URLs from a listing page.
"""

def scrape_foreignpolicy_article_list(num_links=3):
    """
    Fetches a Foreign Policy listing page, optionally removes references
    to known paywall scripts, then extracts article URLs.
    """
    url = "https://foreignpolicy.com/category/latest/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/100.0.4896.127 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    # Remove possible paywall scripts
    html_content = re.sub(r'<script[^>]+(?:piano\.io|cxense\.com)[^>]+></script>', '', response.text)

    soup = BeautifulSoup(html_content, 'html.parser')
    article_urls = []

    # In the snippet, articles are inside <div class="blog-list-layout">.
    article_containers = soup.find_all('div', class_='blog-list-layout')

    for container in article_containers:
        figure_tag = container.find('figure', class_='figure-image')
        if figure_tag:
            link_tag = figure_tag.find('a')
            if link_tag and 'href' in link_tag.attrs:
                article_url = link_tag['href']
                article_urls.append(article_url)
                if len(article_urls) >= num_links:
                    break

    return article_urls

def main():
    urls = scrape_foreignpolicy_article_list()
    print("Found article URLs:")
    for u in urls:
        print(u)

if __name__ == "__main__":
    main()