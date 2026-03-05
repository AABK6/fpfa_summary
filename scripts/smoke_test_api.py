#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from urllib.parse import urljoin

import requests


REQUIRED_ARTICLE_KEYS = {
    "id",
    "source",
    "url",
    "title",
    "author",
    "article_text",
    "core_thesis",
    "detailed_abstract",
    "supporting_data_quotes",
    "publication_date",
    "date_added",
}


def run_smoke(base_url: str) -> None:
    health_url = urljoin(base_url.rstrip("/") + "/", "health")
    articles_url = urljoin(base_url.rstrip("/") + "/", "api/articles")

    health_resp = requests.get(health_url, timeout=20)
    health_resp.raise_for_status()
    health_payload = health_resp.json()
    if health_payload.get("status") != "healthy":
        raise RuntimeError(f"Unexpected /health payload: {health_payload}")

    articles_resp = requests.get(articles_url, timeout=30)
    articles_resp.raise_for_status()
    articles_payload = articles_resp.json()
    if not isinstance(articles_payload, list):
        raise RuntimeError("/api/articles payload is not a list")

    if articles_payload:
        first = articles_payload[0]
        missing = REQUIRED_ARTICLE_KEYS.difference(first.keys())
        if missing:
            raise RuntimeError(f"First article missing keys: {sorted(missing)}")


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
