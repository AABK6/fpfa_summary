import requests
from bs4 import BeautifulSoup

def extract_latest_article_urls(url, num_links_to_retrieve=3):
    """
    Extracts a specified number of the latest article URLs from the Foreign Affairs
    "Most Recent" page, preserving order.

    Args:
        url: The URL of the Foreign Affairs "Most Recent" page.
        num_links_to_retrieve: The number of article URLs to extract (default: 3).

    Returns:
        A list of strings, where each string is an article URL (up to num_links_to_retrieve),
        preserving order, or None if extraction fails.
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
        links_retrieved_count = 0 # Initialize counter

        for card in article_cards:
            if links_retrieved_count >= num_links_to_retrieve: # Check if limit reached
                break # Exit loop if limit is reached

            # Find URLs in <h3> (main title)
            h3_link = card.find('h3', class_='body-m').find('a') if card.find('h3', class_='body-m') else None
            if h3_link and h3_link.has_attr('href'):
                article_urls.append("https://www.foreignaffairs.com" + h3_link['href'])
                links_retrieved_count += 1 # Increment counter
                continue

            if links_retrieved_count >= num_links_to_retrieve: # Check again after h3 (in case h3 already got enough links)
                break

            # If not found in h3, find URLs in <h4> (subtitle)
            h4_link = card.find('h4', class_='body-s').find('a') if card.find('h4', class_='body-s') else None
            if h4_link and h4_link.has_attr('href'):
                article_urls.append("https://www.foreignaffairs.com" + h4_link['href'])
                links_retrieved_count += 1 # Increment counter

        return article_urls

    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL: {e}")
        return None
    except Exception as e:
        print(f"Error parsing article URLs: {e}")
        return None

if __name__ == '__main__':
    most_recent_url = "https://www.foreignaffairs.com/most-recent"
    num_links = 3 # Example: Retrieve 5 links
    latest_article_urls = extract_latest_article_urls(most_recent_url, num_links_to_retrieve=num_links)

    if latest_article_urls:
        print(f"Latest {num_links} Article URLs from Foreign Affairs Most Recent Page (Order Preserved):\n")
        for url in latest_article_urls:
            print(url)
    else:
        print("Failed to extract latest article URLs.")