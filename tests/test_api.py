import os
import pytest
import requests

BASE_URL = 'http://localhost:5000'


@pytest.mark.live
def test_api_articles():
    if os.environ.get("LIVE_TESTS") != "1":
        pytest.skip("LIVE_TESTS=1 not set; skipping live server test")
    response = requests.get(f'{BASE_URL}/api/articles')
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
