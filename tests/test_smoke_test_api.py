from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from scripts.smoke_test_api import run_smoke


def _mock_response(*, status_code: int, payload):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def test_run_smoke_happy_path(monkeypatch):
    responses = [
        _mock_response(status_code=200, payload={"status": "healthy"}),
        _mock_response(
            status_code=200,
            payload=[
                {
                    "id": 1,
                    "source": "Foreign Affairs",
                    "url": "https://fa.com/one",
                    "title": "Title",
                    "author": "Author",
                    "article_text": "Text",
                    "core_thesis": "Core",
                    "detailed_abstract": "Abstract",
                    "supporting_data_quotes": "Quotes",
                    "publication_date": None,
                    "date_added": "2024-01-01 00:00:00",
                }
            ],
        ),
    ]

    def fake_get(url, timeout):  # noqa: ARG001
        return responses.pop(0)

    monkeypatch.setattr("scripts.smoke_test_api.requests.get", fake_get)
    run_smoke("https://example.com")


def test_run_smoke_missing_keys_raises(monkeypatch):
    responses = [
        _mock_response(status_code=200, payload={"status": "healthy"}),
        _mock_response(status_code=200, payload=[{"id": 1}]),
    ]

    def fake_get(url, timeout):  # noqa: ARG001
        return responses.pop(0)

    monkeypatch.setattr("scripts.smoke_test_api.requests.get", fake_get)

    with pytest.raises(RuntimeError):
        run_smoke("https://example.com")
