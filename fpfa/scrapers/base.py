from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)


def build_session(timeout: float = 20.0, retries: int = 2) -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": DEFAULT_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    retry = Retry(
        total=retries,
        connect=retries,
        read=retries,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    # Store default timeout on session for helper use
    s.request = _timeout_wrapper(s.request, timeout)
    return s


def _timeout_wrapper(request_func, timeout: float):
    def wrapped(method, url, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = timeout
        return request_func(method, url, **kwargs)

    return wrapped


class Scraper(Protocol):
    def list_urls(self, limit: int = 5) -> List[str]:
        ...

    def fetch_article(self, url: str) -> Optional[dict]:
        ...


@dataclass
class ArticleData:
    title: str
    author: str
    text: str

