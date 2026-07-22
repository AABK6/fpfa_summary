from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
import urllib3

from services.document_limits import DocumentBudgetExceeded, DocumentLimits


class OutboundPolicyError(ValueError):
    """Raised when a publisher URL crosses the configured trust boundary."""


@dataclass(frozen=True)
class PublisherPolicy:
    roots: tuple[str, ...]
    max_redirects: int = 5


def _normalized_roots(roots: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(root.casefold().strip(".") for root in roots if root.strip("."))


def _host_allowed(host: str, roots: tuple[str, ...]) -> bool:
    normalized = host.casefold().strip(".")
    return any(normalized == root or normalized.endswith(f".{root}") for root in roots)


def validate_publisher_url(url: str, policy: PublisherPolicy) -> str:
    parsed = urlsplit(url.strip())
    if parsed.scheme.casefold() != "https":
        raise OutboundPolicyError("OUTBOUND_URL_REQUIRES_HTTPS")
    if parsed.username or parsed.password:
        raise OutboundPolicyError("OUTBOUND_URL_USERINFO_FORBIDDEN")
    if not parsed.hostname or not _host_allowed(parsed.hostname, _normalized_roots(policy.roots)):
        raise OutboundPolicyError("OUTBOUND_HOST_NOT_ALLOWED")
    try:
        port = parsed.port
    except ValueError as exc:
        raise OutboundPolicyError("OUTBOUND_PORT_INVALID") from exc
    if port not in (None, 443):
        raise OutboundPolicyError("OUTBOUND_PORT_NOT_ALLOWED")
    clean = parsed._replace(fragment="", netloc=parsed.hostname.casefold())
    return urlunsplit(clean)


def resolve_publisher_url(base_url: str, href: str, policy: PublisherPolicy) -> str:
    return validate_publisher_url(urljoin(base_url, href), policy)


def _resolved_public_addresses(host: str, port: int = 443) -> tuple[str, ...]:
    try:
        records = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise OutboundPolicyError("OUTBOUND_DNS_RESOLUTION_FAILED") from exc
    addresses = tuple(sorted({str(record[4][0]) for record in records}))
    if not addresses:
        raise OutboundPolicyError("OUTBOUND_DNS_EMPTY")
    for value in addresses:
        address = ipaddress.ip_address(value.split("%", 1)[0])
        if not address.is_global:
            raise OutboundPolicyError("OUTBOUND_ADDRESS_NOT_PUBLIC")
    return addresses


def _read_bounded_response(response: requests.Response, limit: int) -> str:
    declared = response.headers.get("Content-Length")
    if declared:
        try:
            if int(declared) > limit:
                raise DocumentBudgetExceeded("RESPONSE_BYTE_BUDGET_EXCEEDED")
        except ValueError:
            pass
    chunks: list[bytes] = []
    size = 0
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        size += len(chunk)
        if size > limit:
            raise DocumentBudgetExceeded("RESPONSE_BYTE_BUDGET_EXCEEDED")
        chunks.append(chunk)
    payload = b"".join(chunks)
    encoding = response.encoding or "utf-8"
    return payload.decode(encoding, errors="replace")


class _PinnedResponse:
    def __init__(self, raw: urllib3.HTTPResponse, pool: urllib3.HTTPSConnectionPool, url: str):
        self._raw = raw
        self._pool = pool
        self.status_code = raw.status
        self.headers = raw.headers
        self.url = url
        self.encoding = "utf-8"
        content_type = raw.headers.get("Content-Type", "")
        if "charset=" in content_type:
            self.encoding = content_type.rsplit("charset=", 1)[-1].split(";", 1)[0].strip()

    @property
    def is_redirect(self) -> bool:
        return self.status_code in {301, 302, 303, 307, 308}

    @property
    def is_permanent_redirect(self) -> bool:
        return self.status_code in {301, 308}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} response for {self.url}")

    def iter_content(self, chunk_size: int):
        yield from self._raw.stream(chunk_size, decode_content=True)

    def close(self) -> None:
        self._raw.release_conn()
        self._pool.close()


def _pinned_get(
    url: str,
    *,
    address: str,
    headers: dict[str, str] | None,
    timeout: int | float,
) -> _PinnedResponse:
    """Connect to the validated IP while retaining publisher SNI and certificate checks."""
    parsed = urlsplit(url)
    hostname = parsed.hostname or ""
    pool = urllib3.HTTPSConnectionPool(
        address,
        port=443,
        assert_hostname=hostname,
        server_hostname=hostname,
        timeout=urllib3.Timeout(connect=timeout, read=timeout),
        maxsize=1,
        block=True,
    )
    request_headers = dict(headers or {})
    request_headers["Host"] = hostname
    target = parsed.path or "/"
    if parsed.query:
        target += f"?{parsed.query}"
    try:
        raw = pool.request(
            "GET",
            target,
            headers=request_headers,
            redirect=False,
            preload_content=False,
            retries=False,
        )
    except Exception:
        pool.close()
        raise
    return _PinnedResponse(raw, pool, url)


def fetch_publisher_html(
    url: str,
    *,
    policy: PublisherPolicy,
    headers: dict[str, str] | None = None,
    timeout: int | float = 20,
    session: requests.Session | None = None,
    limits: DocumentLimits | None = None,
) -> str:
    active_limits = limits or DocumentLimits.from_env()
    client = session
    current = validate_publisher_url(url, policy)
    for redirect_count in range(policy.max_redirects + 1):
        parsed = urlsplit(current)
        addresses = _resolved_public_addresses(parsed.hostname or "")
        if session is None:
            response = _pinned_get(
                current,
                address=addresses[0],
                headers=headers,
                timeout=timeout,
            )
        else:
            response = client.get(
                current,
                headers=headers,
                timeout=timeout,
                allow_redirects=False,
                stream=True,
            )
        try:
            if response.is_redirect or response.is_permanent_redirect:
                if redirect_count >= policy.max_redirects:
                    raise OutboundPolicyError("OUTBOUND_REDIRECT_LIMIT_EXCEEDED")
                location = response.headers.get("Location")
                if not location:
                    raise OutboundPolicyError("OUTBOUND_REDIRECT_MISSING_LOCATION")
                current = resolve_publisher_url(current, location, policy)
                continue
            response.raise_for_status()
            final_url = validate_publisher_url(response.url or current, policy)
            if final_url != current:
                raise OutboundPolicyError("OUTBOUND_UNEXPECTED_FINAL_URL")
            return _read_bounded_response(response, active_limits.response_bytes)
        finally:
            response.close()
    raise OutboundPolicyError("OUTBOUND_REDIRECT_LIMIT_EXCEEDED")


def playwright_route_allowed(url: str, policy: PublisherPolicy) -> bool:
    try:
        parsed = urlsplit(validate_publisher_url(url, policy))
        _resolved_public_addresses(parsed.hostname or "")
    except (OutboundPolicyError, ValueError):
        return False
    return True
