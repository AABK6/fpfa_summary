from pydantic import BaseModel, HttpUrl, ConfigDict, field_validator
from typing import Optional

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
    date_added: Optional[str] = None  # SQLite usually stores this as string

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        return normalize_article_source(value)

