from dataclasses import dataclass
from typing import Optional


@dataclass
class Article:
    id: int
    source: str
    url: str
    title: str
    author: str
    article_text: str
    core_thesis: str
    detailed_abstract: str
    supporting_data_quotes: str
    date_added: str  # stored as string from SQLite

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "source": self.source,
            "url": self.url,
            "title": self.title,
            "author": self.author,
            "article_text": self.article_text,
            "core_thesis": self.core_thesis,
            "detailed_abstract": self.detailed_abstract,
            "supporting_data_quotes": self.supporting_data_quotes,
            "date_added": self.date_added,
        }

