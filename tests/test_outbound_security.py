from __future__ import annotations

import socket

import pytest
import requests
from bs4 import BeautifulSoup

from services.document_limits import DocumentBudgetExceeded, DocumentLimits
from services.outbound_http import (
    OutboundPolicyError,
    PublisherPolicy,
    fetch_publisher_html,
    validate_publisher_url,
)
from services.publication_dates import extract_publication_date_from_soup


class _Response:
    def __init__(self, status: int, url: str, body: bytes, headers: dict[str, str]):
        self.status_code = status
        self.url = url
        self.body = body
        self.headers = headers
        self.encoding = "utf-8"
        self.is_redirect = status in {301, 302, 303, 307, 308}
        self.is_permanent_redirect = status in {301, 308}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def iter_content(self, chunk_size: int):
        for offset in range(0, len(self.body), chunk_size):
            yield self.body[offset : offset + chunk_size]

    def close(self) -> None:
        return None


class _Session:
    def __init__(self, responses: list[_Response]):
        self.responses = responses
        self.urls: list[str] = []

    def get(self, url: str, **_kwargs) -> _Response:
        self.urls.append(url)
        return self.responses.pop(0)


def _response(status: int, url: str, body: bytes = b"", **headers: str) -> _Response:
    return _Response(status, url, body, headers)


def test_publisher_policy_rejects_scheme_host_userinfo_and_port():
    policy = PublisherPolicy(("foreignpolicy.com",))
    for url in (
        "http://foreignpolicy.com/article",
        "https://foreignpolicy.com.evil.test/article",
        "https://user@foreignpolicy.com/article",
        "https://foreignpolicy.com:444/article",
    ):
        with pytest.raises(OutboundPolicyError):
            validate_publisher_url(url, policy)


def test_fetch_rejects_redirect_outside_publisher(monkeypatch):
    monkeypatch.setattr(
        "services.outbound_http._resolved_public_addresses",
        lambda _host, _port=443: ("203.0.113.1",),
    )
    session = _Session(
        [_response(302, "https://foreignpolicy.com/start", Location="https://127.0.0.1/admin")]
    )
    with pytest.raises(OutboundPolicyError, match="HOST_NOT_ALLOWED"):
        fetch_publisher_html(
            "https://foreignpolicy.com/start",
            policy=PublisherPolicy(("foreignpolicy.com",)),
            session=session,
        )


def test_fetch_rejects_private_dns_resolution(monkeypatch):
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))],
    )
    with pytest.raises(OutboundPolicyError, match="ADDRESS_NOT_PUBLIC"):
        fetch_publisher_html(
            "https://foreignpolicy.com/start",
            policy=PublisherPolicy(("foreignpolicy.com",)),
            session=_Session([]),
        )


def test_fetch_stream_enforces_byte_budget(monkeypatch):
    monkeypatch.setattr(
        "services.outbound_http._resolved_public_addresses",
        lambda _host, _port=443: ("203.0.113.1",),
    )
    response = _response(200, "https://foreignpolicy.com/start", b"x" * 11)
    with pytest.raises(DocumentBudgetExceeded, match="RESPONSE_BYTE"):
        fetch_publisher_html(
            "https://foreignpolicy.com/start",
            policy=PublisherPolicy(("foreignpolicy.com",)),
            session=_Session([response]),
            limits=DocumentLimits(response_bytes=10),
        )


def test_json_ld_depth_budget_fails_closed(monkeypatch):
    monkeypatch.setenv("FPFA_MAX_JSON_DEPTH", "2")
    soup = BeautifulSoup(
        '<script type="application/ld+json">{"a":{"b":{"datePublished":"2024-01-01"}}}</script>',
        "html.parser",
    )
    with pytest.raises(DocumentBudgetExceeded, match="JSON_DEPTH"):
        extract_publication_date_from_soup(soup)
