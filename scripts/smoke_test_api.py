#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from urllib.parse import urljoin

import requests


REQUIRED_ARTICLE_KEYS = {
    "id",
    "source",
    "url",
    "title",
    "author",
    "core_thesis",
    "detailed_abstract",
    "supporting_data_quotes",
    "publication_date",
    "date_added",
}
FORBIDDEN_ARTICLE_KEYS = {"article_text"}
PRODUCTION_WEB_ORIGIN = "https://ppf-fpfa-summary-prod.web.app"


def run_smoke(base_url: str) -> None:
    health_url = urljoin(base_url.rstrip("/") + "/", "health")
    articles_url = urljoin(base_url.rstrip("/") + "/", "api/articles")

    health_resp = requests.get(health_url, timeout=20)
    health_resp.raise_for_status()
    health_payload = health_resp.json()
    if health_payload.get("status") != "healthy":
        raise RuntimeError(f"Unexpected /health payload: {health_payload}")

    articles_resp = requests.get(
        articles_url,
        params={"limit": 5},
        headers={"Origin": PRODUCTION_WEB_ORIGIN},
        timeout=30,
    )
    articles_resp.raise_for_status()
    articles_payload = articles_resp.json()
    if not isinstance(articles_payload, list):
        raise RuntimeError("/api/articles payload is not a list")
    if len(articles_payload) > 5:
        raise RuntimeError("/api/articles ignored the requested limit")

    allow_origin = articles_resp.headers.get("Access-Control-Allow-Origin")
    if allow_origin != PRODUCTION_WEB_ORIGIN:
        raise RuntimeError(f"Unexpected CORS origin: {allow_origin!r}")

    payload_bytes = len(json.dumps(articles_payload, ensure_ascii=False).encode("utf-8"))
    if payload_bytes > 100_000:
        raise RuntimeError(f"Five-article payload is unexpectedly large: {payload_bytes} bytes")

    if articles_payload:
        first = articles_payload[0]
        missing = REQUIRED_ARTICLE_KEYS.difference(first.keys())
        if missing:
            raise RuntimeError(f"First article missing keys: {sorted(missing)}")
        forbidden = FORBIDDEN_ARTICLE_KEYS.intersection(first.keys())
        if forbidden:
            raise RuntimeError(f"Public payload exposes forbidden keys: {sorted(forbidden)}")

        urls = [str(item.get("url", "")) for item in articles_payload]
        title_keys = [
            (str(item.get("source", "")).casefold(), str(item.get("title", "")).casefold().strip())
            for item in articles_payload
        ]
        if len(urls) != len(set(urls)) or len(title_keys) != len(set(title_keys)):
            raise RuntimeError("Public payload contains duplicate articles")

        dates = [item.get("date_added") for item in articles_payload]
        comparable_dates = [value for value in dates if isinstance(value, str) and value]
        if comparable_dates != sorted(comparable_dates, reverse=True):
            raise RuntimeError("Articles are not ordered newest first")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run smoke tests against deployed API.")
    parser.add_argument("--base-url", required=True, help="Base URL, e.g. https://myapp.azurewebsites.net")
    args = parser.parse_args()

    try:
        run_smoke(args.base_url)
    except Exception as exc:  # noqa: BLE001
        print(f"Smoke test failed: {exc}")
        return 1

    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
