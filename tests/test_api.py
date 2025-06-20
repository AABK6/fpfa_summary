import requests

BASE_URL = 'http://localhost:5000'

def test_api_articles():
    response = requests.get(f'{BASE_URL}/api/articles')
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
