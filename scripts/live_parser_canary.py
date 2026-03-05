#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import summarize_fa_hardened
import summarize_fp


def _validate_article_payload(payload: dict[str, Any], *, source: str) -> None:
    title = str(payload.get("title") or "").strip()
    text = str(payload.get("text") or "").strip()
    if not title:
        raise RuntimeError(f"{source}: missing title")
    if len(text) < 200:
        raise RuntimeError(f"{source}: extracted text too short ({len(text)} chars)")


def run_canary() -> None:
    fa_urls = summarize_fa_hardened.extract_latest_article_urls(num_links=1)
    if not fa_urls:
        raise RuntimeError("Foreign Affairs canary: no URLs discovered")
    fa_article = summarize_fa_hardened.extract_foreign_affairs_article(fa_urls[0])
    if not fa_article:
        raise RuntimeError("Foreign Affairs canary: article fetch failed")
    _validate_article_payload(fa_article, source="Foreign Affairs")

    fp_urls = summarize_fp.scrape_foreignpolicy_article_list(num_links=1)
    if not fp_urls:
        raise RuntimeError("Foreign Policy canary: no URLs discovered")
    fp_article = summarize_fp.scrape_foreignpolicy_article(fp_urls[0])
    if not fp_article:
        raise RuntimeError("Foreign Policy canary: article fetch failed")
    _validate_article_payload(fp_article, source="Foreign Policy")


if __name__ == "__main__":
    run_canary()
    print("Live parser canary passed.")
