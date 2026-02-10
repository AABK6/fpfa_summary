import pytest
from pydantic import ValidationError

from models.article import Article
from models.sources import ArticleSource


def test_article_valid_data():
    data = {
        "id": 1,
        "source": ArticleSource.FOREIGN_AFFAIRS.value,
        "url": "https://www.foreignaffairs.com/article",
        "title": "Test Title",
        "author": "Test Author",
        "article_text": "Text",
        "core_thesis": "Thesis",
        "detailed_abstract": "Abstract",
        "supporting_data_quotes": "Quotes",
        "date_added": "2023-10-27 10:00:00",
    }
    article = Article(**data)
    assert article.title == "Test Title"
    assert str(article.url) == "https://www.foreignaffairs.com/article"


def test_article_invalid_url():
    data = {
        "source": ArticleSource.FOREIGN_AFFAIRS.value,
        "url": "not-a-url",
        "title": "Test Title",
        "author": "Test Author",
        "article_text": "Text",
        "core_thesis": "Thesis",
        "detailed_abstract": "Abstract",
        "supporting_data_quotes": "Quotes",
    }
    with pytest.raises(ValidationError):
        Article(**data)


def test_article_missing_required_field():
    data = {
        "url": "https://www.foreignaffairs.com/article",
        "title": "Test Title",
    }
    with pytest.raises(ValidationError):
        Article(**data)


def test_article_source_legacy_alias_is_normalized():
    article = Article(
        source="FA",
        url="https://www.foreignaffairs.com/article",
        title="Test Title",
        author="Test Author",
        article_text="Text",
        core_thesis="Thesis",
        detailed_abstract="Abstract",
        supporting_data_quotes="Quotes",
    )
    assert article.source == ArticleSource.FOREIGN_AFFAIRS.value


def test_article_source_invalid_value_rejected():
    with pytest.raises(ValidationError):
        Article(
            source="Economist",
            url="https://www.foreignaffairs.com/article",
            title="Test Title",
            author="Test Author",
            article_text="Text",
            core_thesis="Thesis",
            detailed_abstract="Abstract",
            supporting_data_quotes="Quotes",
        )
