import pytest
from pydantic import ValidationError
from models.article import Article

def test_article_valid_data():
    data = {
        "id": 1,
        "source": "Foreign Affairs",
        "url": "https://www.foreignaffairs.com/article",
        "title": "Test Title",
        "author": "Test Author",
        "article_text": "Text",
        "core_thesis": "Thesis",
        "detailed_abstract": "Abstract",
        "supporting_data_quotes": "Quotes",
        "date_added": "2023-10-27 10:00:00"
    }
    article = Article(**data)
    assert article.title == "Test Title"
    assert str(article.url) == "https://www.foreignaffairs.com/article"

def test_article_invalid_url():
    data = {
        "source": "Foreign Affairs",
        "url": "not-a-url",
        "title": "Test Title",
        "author": "Test Author",
        "article_text": "Text",
        "core_thesis": "Thesis",
        "detailed_abstract": "Abstract",
        "supporting_data_quotes": "Quotes"
    }
    with pytest.raises(ValidationError):
        Article(**data)

def test_article_missing_required_field():
    data = {
        "url": "https://www.foreignaffairs.com/article",
        "title": "Test Title"
        # Missing other fields
    }
    with pytest.raises(ValidationError):
        Article(**data)
