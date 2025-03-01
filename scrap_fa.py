import requests
from bs4 import BeautifulSoup

def extract_latest_article_urls(url, num_links_to_retrieve=3):
    """
    Extracts a specified number of the latest article URLs from the Foreign Affairs
    "Most Recent" page, preserving order, and ignoring "podcasts" links.

    Args:
        url: The URL of the Foreign Affairs "Most Recent" page.
        num_links_to_retrieve: The number of article URLs to extract (default: 3).

    Returns:
        A list of strings, where each string is an article URL (up to num_links_to_retrieve),
        preserving order and excluding podcast links, or None if extraction fails.
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

    Args:
        url: The URL of the Foreign Affairs article.

    Returns:
        A dictionary containing 'title', 'subtitle', 'author', and 'text', or None if extraction fails.
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
            'title': title,
            'subtitle': subtitle, # Include subtitle
            'author': author,
            'text': article_text
        }

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None
    except Exception as e:
        print(f"Error parsing article: {e}")
        return None


if __name__ == '__main__':
    most_recent_url = "https://www.foreignaffairs.com/most-recent"
    num_links = 5  # Example: Retrieve 5 links
    latest_article_urls = extract_latest_article_urls(most_recent_url, num_links_to_retrieve=num_links)

    if latest_article_urls:
        print(f"Extracting title, author, and text from the latest {num_links} articles (excluding podcasts)...\n")
        for article_url in latest_article_urls:
            print(f"URL: {article_url}")
            article_data = extract_foreign_affairs_article(article_url)
            if article_data:
                print("--- Article Data ---")
                print(f"Title: {article_data['title']}")
                if article_data['subtitle']: # Print subtitle only if it exists
                    print(f"Subtitle: {article_data['subtitle']}")
                print(f"Author: {article_data['author']}")
                # Print a snippet of the article text
                snippet_length = 300
                snippet = article_data['text'][:snippet_length] + "..." if len(article_data['text']) > snippet_length else article_data['text']
                print("Article Snippet:\n")
                print(snippet)
                print("-" * 50)  # Separator
            else:
                print("Failed to extract article data for this URL.")
                print("-" * 50)
    else:
        print("Failed to extract latest article URLs.")