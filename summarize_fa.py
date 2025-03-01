import requests
from bs4 import BeautifulSoup
import re
import sys
import os
from google import genai
from google.genai import types

"""
Usage:
    python summarize_fp.py [NUMBER_OF_ARTICLES_TO_SUMMARIZE]

Description:
    - Scrapes article URLs from Foreign Policy listing page.
    - Extracts text content from each article.
    - Summarizes each article using Gemini API, now with the EXACTLY CORRECT SDK imports.
"""

def extract_latest_article_urls(num_links_to_retrieve=3):
    """
    Extracts a specified number of latest article URLs (excluding podcasts).
    (URL extraction function - same as before)
    """
    url = "https://www.foreignaffairs.com/most-recent"
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        article_cards = soup.find_all('div', class_='card--large')
        if not article_cards:
            return None

        article_urls = []
        links_retrieved_count = 0

        for card in article_cards:
            if links_retrieved_count >= num_links_to_retrieve:
                break

            # Find URLs in <h3> (main title)
            h3_link = card.find('h3', class_='body-m').find('a') if card.find('h3', class_='body-m') else None
            if h3_link and h3_link.has_attr('href'):
                extracted_url = "https://www.foreignaffairs.com" + h3_link['href']
                if "podcasts" not in extracted_url.lower(): # Check for "podcasts" in URL
                    article_urls.append(extracted_url)
                    links_retrieved_count += 1
                    continue

            if links_retrieved_count >= num_links_to_retrieve:
                break

            # Find URLs in <h4> (subtitle)
            h4_link = card.find('h4', class_='body-s').find('a') if card.find('h4', class_='body-s') else None
            if h4_link and h4_link.has_attr('href'):
                extracted_url = "https://www.foreignaffairs.com" + h4_link['href']
                if "podcasts" not in extracted_url.lower(): # Check for "podcasts" in URL
                    article_urls.append(extracted_url)
                    links_retrieved_count += 1

        return article_urls

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None
    except Exception as e:
        print(f"Error parsing article URLs: {e}")
        return None


def extract_foreign_affairs_article(url):
    """
    Extracts the title, author, and text content of a Foreign Affairs article.
    (Article scraping function - same as before)
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract Title
        title_element = soup.find('h1', class_='topper__title')
        title = title_element.text.strip() if title_element else "Title Not Found"

        # Extract Subtitle (optional, if you want to include it)
        subtitle_element = soup.find('h2', class_='topper__subtitle')
        subtitle = subtitle_element.text.strip() if subtitle_element else "" # or "Subtitle Not Found"

        # Extract Author
        author_element = soup.find('h3', class_='topper__byline')
        author = author_element.text.strip() if author_element else "Author Not Found"

        # Extract Article Text
        article_content = soup.find('article')
        if not article_content:
            article_content = soup.find('div', class_='article-body')
        if not article_content:
            article_content = soup.find('div', class_='Article__body')
        if not article_content:
            article_content = soup.find('main')

        if not article_content:
            article_text = "Article Text Not Found" # Indicate text not found, but still return title/author
        else:
            paragraphs = article_content.find_all('p')
            if not paragraphs:
                paragraphs = article_content.find_all('div', class_='paragraph')

            article_text_list = []
            for p in paragraphs:
                article_text_list.append(p.text.strip())
            article_text = "\n\n".join(article_text_list)


        return {
            "title": title,
            "subtitle": subtitle, # Include subtitle
            "author": author,
            "text": article_text
        }

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None
    except Exception as e:
        print(f"Error parsing article: {e}")
        return None

def create_client(api_key: str) -> genai.Client: # Corrected return type and function name
    """
    Creates a Gemini Pro API client using the 'google' SDK. # Updated description
    """
    client = genai.Client(api_key=api_key)
    return client

def generate_core_thesis(client: genai.Client, article: dict) -> str: # Corrected parameter type
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

def generate_detailed_abstract(client: genai.Client, article: dict) -> str: # Corrected parameter type
    """
    Generates an abstract that expands on the core thesis.
    """
    prompt = f"""
    Task: Provide two dense paragraphs summarizing the main arguments and points
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


def generate_supporting_data_quotes(client: genai.Client, article: dict) -> str: # Corrected parameter type
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
            print("Usage: python summarize_fp.py [NUMBER_OF_ARTICLES_TO_SUMMARIZE]")
            print("       Please provide a valid integer for the number of articles.")
            sys.exit(1)

    article_urls = extract_latest_article_urls(num_articles_to_summarize)

    if not article_urls:
        print("No article URLs found. Exiting.")
        sys.exit(1)

    articles_data = []
    for url in article_urls:
        print(f"Scraping article from: {url}")
        article_data = extract_foreign_affairs_article(url)
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

    model = create_client(api_key) # Create Gemini client using the corrected function

    print("\n--- Article Summaries ---")
    for article in articles_data:
        print(f"\n--- ARTICLE: {article['title']} by {article['author']} ---")

        core_thesis = generate_core_thesis(model, article) # Pass model to summarization functions
        detailed_abstract = generate_detailed_abstract(model, article)
        supporting_data_quotes = generate_supporting_data_quotes(model, article)

        print("\n=== CORE THESIS ===")
        print(core_thesis)
        print("\n=== DETAILED ABSTRACT ===")
        print(detailed_abstract)
        print("\n=== SUPPORTING DATA AND QUOTES ===")
        print(supporting_data_quotes)
        print("-" * 50)

if __name__ == "__main__":
    main()