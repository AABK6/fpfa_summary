import os
import re
import pytest

import fpfa.scrapers.foreign_affairs as fa
import fpfa.scrapers.foreign_policy as fp


LIVE = os.environ.get("LIVE_TESTS") == "1"


pytestmark = pytest.mark.live


def require_live():
    if not LIVE:
        pytest.skip("LIVE_TESTS=1 not set; skipping live network tests")


def _looks_like_url(u: str) -> bool:
    return bool(re.match(r"^https?://", u))


def test_live_fa_list_and_fetch():
    require_live()
    urls = fa.list_urls(limit=5)
    assert urls, "expected at least one FA URL"
    assert all(u.startswith("https://www.foreignaffairs.com") and _looks_like_url(u) for u in urls)

    picked = None
    for u in urls:
        art = fa.fetch_article(u)
        if art and art.get("text"):
            picked = art
            break
    assert picked, "failed to fetch any FA article"
    assert len(picked["title"]) > 5
    assert len(picked["author"]) > 0
    assert len(picked["text"]) > 200


def test_live_fp_list_and_fetch():
    require_live()
    urls = fp.list_urls(limit=5)
    assert urls, "expected at least one FP URL"
    assert all(u.startswith("https://foreignpolicy.com") and _looks_like_url(u) for u in urls)

    picked = None
    for u in urls:
        art = fp.fetch_article(u)
        if art and art.get("text"):
            picked = art
            break
    assert picked, "failed to fetch any FP article"
    assert len(picked["title"]) > 5
    assert len(picked["author"]) > 0
    assert len(picked["text"]) > 100

