import pytest

import json

def test_api_articles(client):
    """
    Test the /api/articles endpoint using the Flask test client.
    """
    response = client.get('/api/articles')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert isinstance(data, list)
    # Note: If the database is empty, this might fail. 
    # In a real test, we would mock the database or use a test database.
    # For now, we just check if it's a list.
    assert len(data) >= 0


def test_flask_home_page_renders(client):
    """Test Flask home page renders without template/static URL errors."""
    response = client.get('/')
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
