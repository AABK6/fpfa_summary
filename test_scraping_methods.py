import requests
from bs4 import BeautifulSoup
import time
import pytest


@pytest.fixture
def headers():
    return {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }


@pytest.fixture
def cookies():
    return {}

def test_with_headers(headers):
    url = "https://www.foreignaffairs.com/most-recent"
    try:
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url)
        print(f"Status code: {response.status_code}")
        print("First 200 chars of response:")
        print(response.text[:200])
    except Exception as e:
        print(f"Exception: {e}")

def test_with_cookies(headers, cookies):
    url = "https://www.foreignaffairs.com/most-recent"
    try:
        session = requests.Session()
        session.headers.update(headers)
        session.cookies.update(cookies)
        response = session.get(url)
        print(f"Status code: {response.status_code}")
        print("First 200 chars of response:")
        print(response.text[:200])
    except Exception as e:
        print(f"Exception: {e}")

def test_with_selenium():
    try:
        import undetected_chromedriver as uc
        import pickle
        import os
        options = uc.ChromeOptions()
        # options.add_argument("--headless")  # Disable headless for manual CAPTCHA
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        # Open browser in a small window and off-screen if possible
        options.add_argument("--window-size=400,300")
        options.add_argument("--window-position=2000,0")  # Move window off main screen if supported
        driver = uc.Chrome(options=options, driver_executable_path="/home/aabecassis/chromedriver")
        url = "https://www.foreignaffairs.com/most-recent"
        cookies_file = "cookies.pkl"
        # If cookies file exists, load cookies before visiting the page
        if os.path.exists(cookies_file):
            driver.get("https://www.foreignaffairs.com/")
            with open(cookies_file, "rb") as f:
                cookies = pickle.load(f)
            for cookie in cookies:
                # Selenium expects expiry as int, not float
                if isinstance(cookie.get('expiry', None), float):
                    cookie['expiry'] = int(cookie['expiry'])
                try:
                    driver.add_cookie(cookie)
                except Exception as e:
                    print(f"Cookie import error: {e}")
            driver.get(url)
            time.sleep(3)
            html = driver.page_source
            print("Selenium page source (first 200 chars):")
            print(html[:200])
            # Auto-delete cookies and retry if Cloudflare block detected
            if ("Attention Required" in html or "cf-chl" in html) and os.path.exists(cookies_file):
                print("Cloudflare block detected. Deleting cookies and retrying...")
                driver.quit()
                os.remove(cookies_file)
                # Recursively retry
                test_with_selenium()
                return
        else:
            print("No cookies found. Loading page and waiting 10 seconds for login/session cookies to be set...")
            driver.get(url)
            time.sleep(10)  # Wait for login/session cookies to be set
            # Save cookies after waiting
            cookies = driver.get_cookies()
            with open(cookies_file, "wb") as f:
                pickle.dump(cookies, f)
            print(f"Saved {len(cookies)} cookies to {cookies_file}. Re-run to use them automatically.")
            html = driver.page_source
            print("Selenium page source (first 200 chars):")
            print(html[:200])
            # Auto-delete cookies and retry if Cloudflare block detected
            if ("Attention Required" in html or "cf-chl" in html) and os.path.exists(cookies_file):
                print("Cloudflare block detected. Deleting cookies and retrying...")
                driver.quit()
                os.remove(cookies_file)
                # Recursively retry
                test_with_selenium()
                return
        driver.quit()
    except Exception as e:
        print(f"Selenium Exception: {e}")

if __name__ == "__main__":
    print("Test 1: Current headers (Firefox UA)")
    headers1 = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }
    test_with_headers(headers1)
    print("\nTest 2: Chrome User-Agent")
    headers2 = headers1.copy()
    headers2['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
    test_with_headers(headers2)
    print("\nTest 3: Add Referer and Origin")
    headers3 = headers2.copy()
    headers3['Referer'] = 'https://www.foreignaffairs.com/'
    headers3['Origin'] = 'https://www.foreignaffairs.com'
    test_with_headers(headers3)
    print("\nTest 4: With dummy cookies (replace with real cookies from browser for real test)")
    cookies = {
        # Example: 'cookie_name': 'cookie_value'
        # You can copy cookies from your browser's dev tools for a real test
    }
    test_with_cookies(headers3, cookies)
    print("\nTest 5: Selenium headless browser")
    test_with_selenium()

