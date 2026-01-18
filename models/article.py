from pydantic import BaseModel, HttpUrl, ConfigDict
from typing import Optional

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
