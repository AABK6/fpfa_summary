#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from playwright.sync_api import Page, Playwright, sync_playwright


VIEWPORTS = (
    ("mobile-320", 320, 700),
    ("mobile-390", 390, 844),
    ("tablet", 768, 900),
    ("desktop", 1440, 1000),
)


def _expected_articles(api_base_url: str) -> list[dict]:
    response = requests.get(
        urljoin(api_base_url.rstrip("/") + "/", "api/articles"),
        params={"limit": 2},
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or not payload:
        raise RuntimeError("The API returned no articles for the browser smoke test.")
    return payload[:2]


def _assert_accessible_reader(page: Page, expected: list[dict]) -> None:
    reader = page.locator('[data-testid="article-reader"]')
    reader.wait_for(state="visible", timeout=30_000)

    title = page.locator('[data-testid="active-title"]')
    title.wait_for(state="visible")
    if title.inner_text().strip() != expected[0]["title"]:
        raise RuntimeError("The reader did not open on the latest API article.")

    counter = page.locator('[data-testid="article-counter"]')
    if not counter.inner_text().strip().startswith("1 of"):
        raise RuntimeError("The reader counter does not start at the newest article.")

    source_link = page.locator('[data-testid="source-link"]')
    href = source_link.get_attribute("href") or ""
    if urlparse(href).scheme not in {"http", "https"}:
        raise RuntimeError("The original-source link is missing or invalid.")
    if source_link.get_attribute("target") != "_blank":
        raise RuntimeError("The original-source link does not open safely in a new tab.")

    selected_tabs = page.locator('[role="tab"][aria-selected="true"]')
    if selected_tabs.count() != 1:
        raise RuntimeError("The section tabs do not expose one selected state.")

    page.locator('[data-testid="section-summary"]').click()
    if not page.locator('[data-testid="section-content"]').inner_text().strip():
        raise RuntimeError("The summary section is empty after activation.")

    active_title = title.inner_text().strip()
    page.locator('[data-testid="section-summary"]').press("ArrowRight")
    evidence_tab = page.locator('[data-testid="section-evidence"]')
    if evidence_tab.get_attribute("aria-selected") != "true":
        raise RuntimeError("Arrow keys do not move between section tabs.")
    if title.inner_text().strip() != active_title:
        raise RuntimeError("Section-tab keys changed the active article.")

    if len(expected) > 1:
        page.locator('[data-testid="older-button"]').click()
        page.wait_for_function(
            "expected => document.querySelector('[data-testid=active-title]')?.textContent?.trim() === expected",
            arg=expected[1]["title"],
        )
        page.keyboard.press("ArrowLeft")
        page.wait_for_function(
            "expected => document.querySelector('[data-testid=active-title]')?.textContent?.trim() === expected",
            arg=expected[0]["title"],
        )

    has_horizontal_overflow = page.evaluate(
        "document.documentElement.scrollWidth > document.documentElement.clientWidth + 1"
    )
    if has_horizontal_overflow:
        raise RuntimeError("The page overflows horizontally at this viewport.")


def _assert_cache_fallback(
    page: Page,
    api_base_url: str,
    expected_title: str,
    screenshot_path: Path,
) -> None:
    api_pattern = re.compile(
        re.escape(api_base_url.rstrip("/")) + r"/api/articles(?:\?.*)?$"
    )
    page.route(
        api_pattern,
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"temporarily":"unavailable"}',
        ),
    )
    refresh = page.get_by_role("button", name="Refresh summaries")
    refresh.click()
    page.mouse.move(0, 0)
    stale_status = page.locator('[aria-label^="Offline copy."]')
    stale_status.wait_for(state="attached", timeout=15_000)
    if page.locator('[data-testid="active-title"]').inner_text().strip() != expected_title:
        raise RuntimeError("The cached feed changed the active article unexpectedly.")
    page.screenshot(path=str(screenshot_path), full_page=True)

    page.unroute(api_pattern)
    refresh.click()
    page.mouse.move(0, 0)
    stale_status.wait_for(state="detached", timeout=30_000)


def _run_viewport(
    playwright: Playwright,
    *,
    base_url: str,
    api_base_url: str,
    expected: list[dict],
    output_dir: Path,
    name: str,
    width: int,
    height: int,
    check_cache_fallback: bool,
) -> None:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(
        viewport={"width": width, "height": height},
        locale="en-US",
        reduced_motion="reduce",
    )
    page = context.new_page()
    console_issues: list[str] = []
    console_messages: list[str] = []
    failed_requests: list[str] = []

    def record_console_issue(message) -> None:
        text = message.text
        console_messages.append(f"[{message.type}] {text}")
        if message.type in {"error", "warning"} or re.search(
            r"EXCEPTION CAUGHT|assertion was thrown|setState\(\).*during build",
            text,
            flags=re.IGNORECASE,
        ):
            console_issues.append(f"[{message.type}] {text}")

    page.on("console", record_console_issue)
    page.on(
        "requestfailed",
        lambda request: failed_requests.append(
            f"{request.method} {request.url}: {request.failure}"
        )
        if request.resource_type in {"document", "script", "xhr", "fetch"}
        else None,
    )

    try:
        page.goto(base_url, wait_until="networkidle", timeout=60_000)
        _assert_accessible_reader(page, expected)
        if check_cache_fallback:
            _assert_cache_fallback(
                page,
                api_base_url,
                expected[0]["title"],
                output_dir / f"{name}-offline.png",
            )
        page.screenshot(path=str(output_dir / f"{name}.png"), full_page=True)
    except Exception:
        page.screenshot(path=str(output_dir / f"{name}-failure.png"), full_page=True)
        raise
    finally:
        context.close()
        browser.close()

    relevant_console_issues = [
        error
        for error in console_issues
        if not re.search(
            r"favicon|source map|CPU-only rendering.*WebGL",
            error,
            flags=re.IGNORECASE,
        )
    ]
    if relevant_console_issues:
        raise RuntimeError(
            f"Browser console issues at {name}: {relevant_console_issues}. "
            f"Console tail: {console_messages[-30:]}"
        )
    if failed_requests:
        raise RuntimeError(f"Failed browser requests at {name}: {failed_requests}")


def run_smoke(base_url: str, api_base_url: str, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    expected = _expected_articles(api_base_url)
    with sync_playwright() as playwright:
        for name, width, height in VIEWPORTS:
            _run_viewport(
                playwright,
                base_url=base_url,
                api_base_url=api_base_url,
                expected=expected,
                output_dir=output_dir,
                name=name,
                width=width,
                height=height,
                check_cache_fallback=name == "mobile-320",
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke-test the deployed FPFA web reader.")
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--api-base-url", required=True)
    parser.add_argument("--output-dir", default="output/playwright/web-smoke")
    args = parser.parse_args()

    run_smoke(args.base_url, args.api_base_url, Path(args.output_dir))
    print("Web smoke test passed at four responsive viewports.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
