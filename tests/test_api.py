import pytest

import json

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert data, "Expected fixture-seeded results, got empty list"
    assert REQUIRED_ARTICLE_KEYS.issubset(data[0].keys())


def test_flask_api_articles_deterministic_order_by_date_added(flask_client_with_db):
    response = flask_client_with_db.get("/api/articles")
    data = response.get_json()

    # Flask app reverses SQL DESC order before returning; assert that behavior is deterministic.
    assert [item["title"] for item in data] == ["Alpha", "Beta", "Gamma"]
    assert [item["date_added"] for item in data] == sorted(item["date_added"] for item in data)


def test_flask_api_articles_contract_url_serializable(flask_client_with_db):
    response = flask_client_with_db.get("/api/articles")
    data = response.get_json()

    for item in data:
        url = item["url"]
        parsed = urlparse(url)
        assert parsed.scheme in {"http", "https"}
        assert parsed.netloc


def test_flask_home_page_renders_key_content(flask_client_with_db):
    response = flask_client_with_db.get("/")

    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert '<html' in body.lower()
    assert 'styles.css' in body


@pytest.mark.parametrize(
    "date_added, expected_display",
    [
        ("2023-01-01 12:34:56", "January 1"),
        (None, "Unknown date"),
        ("not-a-date", "Unknown date"),
    ],
)
def test_flask_home_page_date_rendering(client, monkeypatch, date_added, expected_display):
    """Flask template renders valid and fallback date text through safe_date filter."""
    sample_articles = [
        {
            "id": 1,
            "source": "Foreign Policy",
            "url": "https://example.com/article",
            "title": "Sample Title",
            "author": "Sample Author",
            "article_text": "Text",
            "core_thesis": "Thesis",
            "detailed_abstract": "Abstract",
            "supporting_data_quotes": "Quote",
            "date_added": date_added,
        }
    ]

    monkeypatch.setattr("app.get_latest_articles", lambda limit=20: sample_articles)

    response = client.get('/')
    assert response.status_code == 200
    assert expected_display in response.get_data(as_text=True)
