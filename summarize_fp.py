import requests
from bs4 import BeautifulSoup
import re
import sys
from google import genai
from google.genai import types
import os

# ======= DATABASE IMPORTS AND FUNCTIONS (MINIMAL ADDITION) =======
import sqlite3

def init_db(db_path="articles.db"):
    """
    Creates (if not exists) a table 'articles' for storing article data.
    Includes a column 'article_text' to store the full text of the article.
    The URL is declared UNIQUE to skip duplicates.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
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
    ''')
    conn.commit()
    return conn

def insert_article(conn, source, url, title, author, article_text,
                   core_thesis, detailed_abstract, supporting_data_quotes):
    """
    Inserts an article into the database table 'articles'.
    Skips if the URL is already present (UNIQUE constraint).
    """
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO articles
            (source, url, title, author, article_text,
             core_thesis, detailed_abstract, supporting_data_quotes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (source, url, title, author, article_text,
              core_thesis, detailed_abstract, supporting_data_quotes))
        conn.commit()
        print(f"Inserted article into DB: {title}")
    except sqlite3.IntegrityError:
        # We'll handle pre-existing articles in main() by checking first
        pass

def get_article_by_url(conn, url):
    """
    Returns (title, author, article_text, core_thesis, detailed_abstract, supporting_data_quotes) if present,
    or None if not found.
    """
    cursor = conn.cursor()
    cursor.execute('''
        SELECT title, author, article_text, core_thesis,
               detailed_abstract, supporting_data_quotes
        FROM articles
        WHERE url = ?
    ''', (url,))
    return cursor.fetchone()

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
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
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
            model='gemini-2.5-flash-preview-05-20',
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
            model='gemini-2.5-flash-preview-05-20',
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        print(f"Error generating supporting data/quotes: {e}")
        return "Summary generation failed."


def main():
    # Thin wrapper delegating to the new pipeline
    try:
        limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    except ValueError:
        print("Usage: python summarize_fp.py [NUMBER_OF_ARTICLES_TO_SUMMARIZE]")
        sys.exit(1)

    from fpfa.pipeline import run_pipeline
    from fpfa.summarizers.gemini import GeminiSummaryGenerator

    inserted = run_pipeline(["fp"], limit=limit, summarizer=GeminiSummaryGenerator())
    print(f"Inserted {inserted} Foreign Policy articles.")

if __name__ == "__main__":
    main()
