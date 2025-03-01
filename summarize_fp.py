import requests
from bs4 import BeautifulSoup
import re
import sys
from google import genai
from google.genai import types
import os

"""
Usage:
    python combined_scraper_summarizer.py [NUMBER_OF_ARTICLES_TO_SUMMARIZE]

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
        response = requests.get(url, headers=headers, timeout=10) # Added timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        html = response.text
    except requests.exceptions.RequestException as e:
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

    return {
        "title": title,
        "author": author,
        "text": article_body
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
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html_content = response.text
    except requests.exceptions.RequestException as e:
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
                article_url = link_tag['href']
                article_urls.append(article_url)
                if len(article_urls) >= num_links:
                    break
    return article_urls

def create_client(api_key: str) -> genai.Client:
    """
    Creates a Gemini Developer API client.
    """
    client = genai.Client(api_key=api_key)
    return client

def generate_core_thesis(client: genai.Client, article: dict) -> str:
    """
    Generates the Core Thesis in 1-2 sentences.
    """
    prompt = f"""
    Task: Write 1-2 dense sentences capturing the main conclusion or central argument
    of the above article, focusing only on the primary claim or takeaway without supporting details.
    
    Title: {article['title']}
    Author: {article['author']}
    Text: {article['text']}
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error generating core thesis: {e}")
        return "Summary generation failed."

def generate_detailed_abstract(client: genai.Client, article: dict) -> str:
    """
    Generates an abstract that expands on the core thesis.
    """
    prompt = f"""
    Task: Provide 1-2 dense paragraphs summarizing the main arguments and points
    of the article. Include essential background, the progression of ideas, and explain
    any important concepts the article uses to develop its case.
    Do not add anything else than the summary, and remove any unnecessary words.

    Title: {article['title']}
    Author: {article['author']}
    Text: {article['text']}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-thinking-exp-01-21', # Use a more stable model if available
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error generating detailed abstract: {e}")
        return "Summary generation failed."


def generate_supporting_data_quotes(client: genai.Client, article: dict) -> str:
    """
    Highlights critical data points and direct quotes from the article.
    """
    prompt = f"""
    Task: Extract and list:
    - The most important factual data points or statistics from the article.
    - 2-3 key direct quotes verbatim, capturing the article's ethos or perspective.

    Present them as bullet points or a short list, preserving the article's original style in the quotes. Do not add anything esle than the bullet points.

    Title: {article['title']}
    Author: {article['author']}
    Text: {article['text']}
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.0-flash-thinking-exp-01-21', # Use a more stable model if available
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error generating supporting data/quotes: {e}")
        return "Summary generation failed."


def main():
    if len(sys.argv) < 2:
        num_articles_to_summarize = 3 # Default to 3 articles if no argument is provided
    else:
        try:
            num_articles_to_summarize = int(sys.argv[1])
            if num_articles_to_summarize <= 0:
                print("Please provide a positive number of articles to summarize.")
                sys.exit(1)
        except ValueError:
            print("Usage: python combined_scraper_summarizer.py [NUMBER_OF_ARTICLES_TO_SUMMARIZE]")
            print("       Please provide a valid integer for the number of articles.")
            sys.exit(1)

    article_urls = scrape_foreignpolicy_article_list(num_articles_to_summarize)

    if not article_urls:
        print("No article URLs found. Exiting.")
        sys.exit(1)

    articles_data = []
    for url in article_urls:
        print(f"Scraping article from: {url}")
        article_data = scrape_foreignpolicy_article(url)
        if article_data:
            articles_data.append(article_data)
        else:
            print(f"Failed to scrape article from: {url}")

    if not articles_data:
        print("No article data scraped successfully. Exiting.")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY") # Get API key from environment variable
    if not api_key:
        print("Error: GEMINI_API_KEY environment variable not set.")
        print("Please set your Gemini API key as an environment variable named GEMINI_API_KEY.")
        sys.exit(1)

    client = create_client(api_key)

    print("\n--- Article Summaries ---")
    for article in articles_data:
        print(f"\n--- ARTICLE: {article['title']} by {article['author']} ---")

        core_thesis = generate_core_thesis(client, article)
        detailed_abstract = generate_detailed_abstract(client, article)
        supporting_data_quotes = generate_supporting_data_quotes(client, article)

        print("\n=== CORE THESIS ===")
        print(core_thesis)
        print("\n=== DETAILED ABSTRACT ===")
        print(detailed_abstract)
        print("\n=== SUPPORTING DATA AND QUOTES ===")
        print(supporting_data_quotes)
        print("-" * 50)

if __name__ == "__main__":
    main()