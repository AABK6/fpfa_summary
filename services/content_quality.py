from __future__ import annotations

import re


_LEADING_LABEL = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:\*\*)?"
    r"(?:core\s+thesis|thesis|detailed\s+abstract|abstract|summary|"
    r"supporting\s+(?:data\s+and\s+quotes|evidence)|evidence)"
    r"\s*(?:\*\*)?\s*[:\-–—]?\s*(?:\*\*)?\s*",
    re.IGNORECASE,
)
_LEADING_BOILERPLATE = re.compile(
    r"^\s*(?:here(?:'s|\s+is)|below\s+is)\s+"
    r"(?:a|the)?\s*(?:concise|detailed)?\s*"
    r"(?:summary|analysis|thesis|abstract)(?:\s+of\s+the\s+article)?\s*[:\-–—]?\s*",
    re.IGNORECASE,
)


def sanitize_generated_text(value: object) -> str:
    """Remove common model wrappers while preserving substantive text."""

    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    text = re.sub(r"^```(?:markdown|text)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    text = _LEADING_LABEL.sub("", text, count=1)
    text = _LEADING_BOILERPLATE.sub("", text, count=1)
    text = re.sub(r"\*\*([^*\n]+)\*\*", r"\1", text)
    text = text.replace("`", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
