from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable


class DocumentBudgetExceeded(ValueError):
    """Raised when untrusted publisher content exceeds a configured budget."""


def _positive_env(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


@dataclass(frozen=True)
class DocumentLimits:
    response_bytes: int = 5 * 1024 * 1024
    html_chars: int = 5_000_000
    article_chars: int = 250_000
    paragraphs: int = 2_000
    json_depth: int = 32
    json_nodes: int = 20_000
    json_scripts: int = 100
    date_candidates: int = 500

    @classmethod
    def from_env(cls) -> "DocumentLimits":
        return cls(
            response_bytes=_positive_env("FPFA_MAX_RESPONSE_BYTES", cls.response_bytes),
            html_chars=_positive_env("FPFA_MAX_HTML_CHARS", cls.html_chars),
            article_chars=_positive_env("FPFA_MAX_ARTICLE_CHARS", cls.article_chars),
            paragraphs=_positive_env("FPFA_MAX_PARAGRAPHS", cls.paragraphs),
            json_depth=_positive_env("FPFA_MAX_JSON_DEPTH", cls.json_depth),
            json_nodes=_positive_env("FPFA_MAX_JSON_NODES", cls.json_nodes),
            json_scripts=_positive_env("FPFA_MAX_JSON_SCRIPTS", cls.json_scripts),
            date_candidates=_positive_env("FPFA_MAX_DATE_CANDIDATES", cls.date_candidates),
        )


def ensure_html_budget(html: str, limits: DocumentLimits | None = None) -> str:
    active = limits or DocumentLimits.from_env()
    if len(html) > active.html_chars:
        raise DocumentBudgetExceeded("HTML_CHAR_BUDGET_EXCEEDED")
    return html


def collect_bounded_paragraphs(
    values: Iterable[str], limits: DocumentLimits | None = None
) -> list[str]:
    active = limits or DocumentLimits.from_env()
    output: list[str] = []
    total_chars = 0
    for value in values:
        if len(output) >= active.paragraphs:
            raise DocumentBudgetExceeded("PARAGRAPH_BUDGET_EXCEEDED")
        next_size = total_chars + len(value) + (2 if output else 0)
        if next_size > active.article_chars:
            raise DocumentBudgetExceeded("ARTICLE_CHAR_BUDGET_EXCEEDED")
        output.append(value)
        total_chars = next_size
    return output
