from __future__ import annotations

import pytest

from scripts.live_parser_canary import _validate_article_payload


def test_validate_article_payload_accepts_expected_shape():
    _validate_article_payload(
        {"title": "A title", "text": "x" * 300},
        source="Foreign Affairs",
    )


def test_validate_article_payload_rejects_short_text():
    with pytest.raises(RuntimeError):
        _validate_article_payload({"title": "A", "text": "short"}, source="Foreign Policy")
