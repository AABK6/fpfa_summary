import requests
from bs4 import BeautifulSoup
import sys
import os
import sqlite3
from google import genai


UA_CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def init_db(db_path="articles.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
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


def get_article_by_url(conn, url):
    cur = conn.cursor()
    cur.execute(
        """
        SELECT title, author, article_text, core_thesis, detailed_abstract, supporting_data_quotes
        FROM articles WHERE url = ?
        """,
        (url,),
    )
    return cur.fetchone()


def insert_article(conn, source, url, title, author, article_text, core_thesis, detailed_abstract, supporting_data_quotes):
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO articles
            (source, url, title, author, article_text, core_thesis, detailed_abstract, supporting_data_quotes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (source, url, title, author, article_text, core_thesis, detailed_abstract, supporting_data_quotes),
        )
        conn.commit()
        print(f"Inserted article into DB: {title}")
    except sqlite3.IntegrityError:
        pass


def list_fa_urls(limit=3):
    url = "https://www.foreignaffairs.com/most-recent"
    headers = {"User-Agent": UA_CHROME}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")
    urls = []
    for card in soup.select("div.card--large"):
        if len(urls) >= limit:
            break
        a = card.select_one("h3.body-m a") or card.select_one("h4.body-s a")
        if not a or not a.get("href"):
            continue
        href = a["href"].strip()
        full = href if href.startswith("http") else f"https://www.foreignaffairs.com{href}"
        if "podcast" in full or "podcasts" in full:
            continue
        urls.append(full)
    return urls


def fetch_fa_article(url: str):
    headers = {"User-Agent": UA_CHROME}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    title_tag = soup.find("meta", property="og:title")
    title = title_tag["content"].strip() if title_tag and title_tag.get("content") else "Title not found"

    author_tags = soup.find_all("meta", property="article:author")
    authors = ", ".join(tag["content"].strip() for tag in author_tags if tag.get("content"))
    if not authors:
        by = soup.select_one("h3.topper__byline")
        authors = by.get_text(strip=True) if by else "Author not found"

    text = ""
    container = soup.find("div", class_="paywall-content")
    if container:
        parts = []
        for el in container.find_all(["p", "blockquote"]):
            t = el.get_text(strip=True)
            if t:
                parts.append(t)
        text = "\n\n".join(parts)
    if not text:
        return None
    return {"title": title, "author": authors, "text": text}


def create_client(api_key: str) -> genai.Client:
    return genai.Client(api_key=api_key)


def generate_core_thesis(client: genai.Client, article: dict) -> str:
    prompt = f"""
    Task: Write 1-2 dense sentences capturing the main conclusion or central argument
    of the above article, focusing only on the primary claim without supporting details.

    Title: {article['title']}
    Author: {article['author']}
    Text: {article['text']}
    """
    try:
        res = client.models.generate_content(model='gemini-2.0-flash', contents=prompt)
        return res.text.strip()
    except Exception as e:
        print(f"Error generating core thesis: {e}")
        return "Summary generation failed."


def generate_detailed_abstract(client: genai.Client, article: dict) -> str:
    prompt = f"""
    Task: Provide 1-2 dense paragraphs summarizing the main arguments and points
    of the article. Include essential background and the progression of ideas. Do not include anything except the summary.

    Title: {article['title']}
    Author: {article['author']}
    Text: {article['text']}
    """
    try:
        res = client.models.generate_content(model='gemini-2.5-flash-preview-05-20', contents=prompt)
        return res.text.strip()
    except Exception as e:
        print(f"Error generating detailed abstract: {e}")
        return "Summary generation failed."


def generate_supporting_data_quotes(client: genai.Client, article: dict) -> str:
    prompt = f"""
    Task: Extract and list the most important factual data points or statistics and 2-3 key direct quotes verbatim. Return bullet points only.

    Title: {article['title']}
    Author: {article['author']}
    Text: {article['text']}
    """
    try:
        res = client.models.generate_content(model='gemini-2.5-flash-preview-05-20', contents=prompt)
        return res.text.strip()
    except Exception as e:
        print(f"Error generating supporting data/quotes: {e}")
        return "Summary generation failed."


def main():
    try:
        limit = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    except ValueError:
        print("Usage: python summarize_fa.py [NUMBER_OF_ARTICLES_TO_SUMMARIZE]")
        sys.exit(1)

    urls = list_fa_urls(limit)
    if not urls:
        print("No FA URLs found.")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not set.")
        sys.exit(2)
    client = create_client(api_key)

    conn = init_db("articles.db")
    for url in urls:
        print(f"Scraping: {url}")
        existing = get_article_by_url(conn, url)
        if existing:
            print("Already in DB, skipping.")
            continue
        art = fetch_fa_article(url)
        if not art:
            print("Failed to fetch article body.")
            continue
        core = generate_core_thesis(client, art)
        detail = generate_detailed_abstract(client, art)
        quotes = generate_supporting_data_quotes(client, art)
        insert_article(
            conn,
            source="Foreign Affairs",
            url=url,
            title=art["title"],
            author=art["author"],
            article_text=art["text"],
            core_thesis=core,
            detailed_abstract=detail,
            supporting_data_quotes=quotes,
        )
    conn.close()


if __name__ == "__main__":
    main()

