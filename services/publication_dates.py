from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

from bs4 import BeautifulSoup


DEFAULT_ALLOWED_FUTURE_DAYS = 1
URL_DATE_RE = re.compile(r"/(?P<year>(?:19|20)\d{2})/(?P<month>\d{2})/(?P<day>\d{2})(?:/|$)")


def _reference_today(now: datetime | date | None = None) -> date:
    if now is None:
        return datetime.now(timezone.utc).date()
    if isinstance(now, datetime):
        if now.tzinfo is None:
            return now.date()
        return now.astimezone(timezone.utc).date()
    return now


def _parse_raw_date(raw_value: Any) -> date | None:
    if raw_value is None:
        return None

    value_text = str(raw_value).strip()
    if not value_text or value_text.isdigit():
        return None

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value_text):
        try:
            return date.fromisoformat(value_text)
        except ValueError:
            return None

    normalized_text = value_text.replace("Z", "+00:00")
    for candidate in (normalized_text, normalized_text.split(" ", 1)[0]):
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            continue
        return parsed.date()

    for pattern in (
        "%Y/%m/%d",
        "%Y-%m-%d %H:%M:%S",
        "%B %d, %Y",
        "%b %d, %Y",
    ):
        try:
            return datetime.strptime(value_text, pattern).date()
        except ValueError:
            continue

    return None


def normalize_publication_date(
    raw_value: Any,
    *,
    now: datetime | date | None = None,
    allowed_future_days: int = DEFAULT_ALLOWED_FUTURE_DAYS,
) -> str | None:
    parsed_date = _parse_raw_date(raw_value)
    if parsed_date is None:
        return None

    if parsed_date > _reference_today(now) + timedelta(days=allowed_future_days):
        return None

    return parsed_date.isoformat()


def is_suspicious_publication_date(
    raw_value: Any,
    *,
    now: datetime | date | None = None,
    allowed_future_days: int = DEFAULT_ALLOWED_FUTURE_DAYS,
) -> bool:
    return raw_value is not None and normalize_publication_date(
        raw_value, now=now, allowed_future_days=allowed_future_days
    ) is None


def extract_publication_date_from_url(
    url: str | None,
    *,
    now: datetime | date | None = None,
    allowed_future_days: int = DEFAULT_ALLOWED_FUTURE_DAYS,
) -> str | None:
    if not url:
        return None

    match = URL_DATE_RE.search(url)
    if not match:
        return None

    raw_value = f"{match.group('year')}-{match.group('month')}-{match.group('day')}"
    return normalize_publication_date(raw_value, now=now, allowed_future_days=allowed_future_days)


def coerce_publication_date(
    raw_value: Any,
    *,
    url: str | None = None,
    now: datetime | date | None = None,
    allowed_future_days: int = DEFAULT_ALLOWED_FUTURE_DAYS,
) -> str | None:
    normalized = normalize_publication_date(raw_value, now=now, allowed_future_days=allowed_future_days)
    if normalized is not None:
        return normalized
    return extract_publication_date_from_url(url, now=now, allowed_future_days=allowed_future_days)


def _iter_json_nodes(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _iter_json_nodes(value)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_json_nodes(item)


def _json_ld_date_candidates(soup: BeautifulSoup) -> list[str]:
    candidates: list[str] = []
    for script in soup.find_all("script", attrs={"type": re.compile(r"ld\+json", re.I)}):
        raw_text = script.string or script.get_text(" ", strip=True)
        if not raw_text:
            continue
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError:
            continue
        for node in _iter_json_nodes(payload):
            for key in ("datePublished", "dateCreated"):
                value = node.get(key)
                if value:
                    candidates.append(str(value))
    return candidates


def _meta_date_candidates(soup: BeautifulSoup) -> list[str]:
    selectors = (
        ("meta", {"property": "article:published_time"}),
        ("meta", {"name": "article:published_time"}),
        ("meta", {"property": "og:published_time"}),
        ("meta", {"name": "parsely-pub-date"}),
        ("meta", {"name": "publish-date"}),
        ("meta", {"itemprop": "datePublished"}),
    )
    candidates: list[str] = []
    for tag_name, attrs in selectors:
        tag = soup.find(tag_name, attrs=attrs)
        if tag and tag.get("content"):
            candidates.append(tag["content"].strip())
    return candidates


def _time_tag_candidates(soup: BeautifulSoup) -> list[str]:
    selectors = (
        ".hed-heading time[datetime]",
        ".topper time[datetime]",
        "header time[datetime]",
        "article time[datetime]",
        "main time[datetime]",
        "time[datetime]",
    )
    candidates: list[str] = []
    seen: set[str] = set()
    for selector in selectors:
        for tag in soup.select(selector):
            candidate = (tag.get("datetime") or tag.get_text(strip=True) or "").strip()
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            candidates.append(candidate)
    return candidates


def _first_normalized(
    raw_candidates: Iterable[str],
    *,
    now: datetime | date | None = None,
    allowed_future_days: int = DEFAULT_ALLOWED_FUTURE_DAYS,
) -> str | None:
    for raw_candidate in raw_candidates:
        normalized = normalize_publication_date(
            raw_candidate, now=now, allowed_future_days=allowed_future_days
        )
        if normalized is not None:
            return normalized
    return None


def extract_publication_date_from_soup(
    soup: BeautifulSoup,
    *,
    url: str | None = None,
    now: datetime | date | None = None,
    allowed_future_days: int = DEFAULT_ALLOWED_FUTURE_DAYS,
) -> str | None:
    for candidates in (
        _meta_date_candidates(soup),
        _json_ld_date_candidates(soup),
    ):
        normalized = _first_normalized(candidates, now=now, allowed_future_days=allowed_future_days)
        if normalized is not None:
            return normalized

    url_date = extract_publication_date_from_url(url, now=now, allowed_future_days=allowed_future_days)
    if url_date is not None:
        return url_date

    return _first_normalized(_time_tag_candidates(soup), now=now, allowed_future_days=allowed_future_days)
