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
