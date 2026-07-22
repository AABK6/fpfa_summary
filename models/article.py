from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from models.sources import normalize_article_source


class Article(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    source: str
    url: HttpUrl
    title: str
    author: str
    article_text: str
    core_thesis: str
    detailed_abstract: str
    supporting_data_quotes: str
    publication_date: Optional[str] = None
    date_added: Optional[str] = None  # SQLite usually stores this as string

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        return normalize_article_source(value)


class ArticleSummary(BaseModel):
    """Public article contract; deliberately excludes the copyrighted body text."""

    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    source: str = Field(max_length=64)
    url: HttpUrl
    title: str = Field(max_length=500)
    author: str = Field(max_length=500)
    core_thesis: str = Field(max_length=4000)
    detailed_abstract: str = Field(max_length=20000)
    supporting_data_quotes: str = Field(max_length=12000)
    publication_date: Optional[str] = Field(default=None, max_length=64)
    date_added: Optional[str] = Field(default=None, max_length=64)

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        return normalize_article_source(value)
