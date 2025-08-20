import types
from pathlib import Path

import fpfa.scrapers.foreign_affairs as fa
import fpfa.scrapers.foreign_policy as fp
import fpfa.scrapers.base as base


class FakeResp:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


class FakeSession:
    def __init__(self, mapping):
        self._mapping = mapping

    def get(self, url, **kwargs):
        return FakeResp(self._mapping.get(url, ""))


def test_fa_list_and_article(monkeypatch, tmp_path: Path):
    fixtures = Path(__file__).parent / "fixtures"
    html_list = (fixtures / "fa_list.html").read_text()
    html_article = (fixtures / "fa_article.html").read_text()

    mapping = {
        fa.MOST_RECENT: html_list,
        "https://www.foreignaffairs.com/article-1": html_article,
        "https://www.foreignaffairs.com/article-2": html_article,
    }

    monkeypatch.setattr(base, "build_session", lambda **kwargs: FakeSession(mapping))

    urls = fa.list_urls(limit=5)
    assert urls == [
        "https://www.foreignaffairs.com/article-1",
        "https://www.foreignaffairs.com/article-2",
    ]

    art = fa.fetch_article(urls[0])
    assert art and art["title"] == "FA Title"
    assert art["author"] == "Alice, Bob"
    assert "Paragraph 1." in art["text"]


def test_fp_list_and_article(monkeypatch):
    fixtures = Path(__file__).parent / "fixtures"
    html_list = (fixtures / "fp_list.html").read_text()
    html_article = (fixtures / "fp_article.html").read_text()

    mapping = {
        fp.LATEST: html_list,
        "https://foreignpolicy.com/2024/01/01/first/": html_article,
        "https://foreignpolicy.com/2024/01/02/second/": html_article,
    }

    monkeypatch.setattr(base, "build_session", lambda **kwargs: FakeSession(mapping))

    urls = fp.list_urls(limit=5)
    assert len(urls) == 2
    art = fp.fetch_article(urls[0])
    assert art and art["title"] == "FP Title"
    assert art["author"] == "Carol"
    assert "FP Para 1." in art["text"] and "FP Para 2." in art["text"]

