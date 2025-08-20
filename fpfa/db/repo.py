import sqlite3
from typing import List, Optional
from ..models import Article


class ArticleRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def get_latest(self, limit: int = 20, source: Optional[str] = None, offset: int = 0) -> List[Article]:
        conn = self._connect()
        try:
            cur = conn.cursor()
            base_query = (
                "SELECT id, source, url, title, author, article_text, "
                "core_thesis, detailed_abstract, supporting_data_quotes, date_added "
                "FROM articles"
            )
            params: list = []
            if source:
                base_query += " WHERE source = ?"
                params.append(source)
            base_query += " ORDER BY date_added DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cur.execute(base_query, tuple(params))
            rows = cur.fetchall()

            articles: List[Article] = []
            for row in rows:
                articles.append(
                    Article(
                        id=row[0],
                        source=row[1],
                        url=row[2],
                        title=row[3],
                        author=row[4],
                        article_text=row[5],
                        core_thesis=row[6],
                        detailed_abstract=row[7],
                        supporting_data_quotes=row[8],
                        date_added=row[9],
                    )
                )
            return articles
        finally:
            conn.close()

    def get_by_url(self, url: str) -> Optional[Article]:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(
                (
                    "SELECT id, source, url, title, author, article_text, core_thesis, "
                    "detailed_abstract, supporting_data_quotes, date_added FROM articles WHERE url = ?"
                ),
                (url,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return Article(
                id=row[0],
                source=row[1],
                url=row[2],
                title=row[3],
                author=row[4],
                article_text=row[5],
                core_thesis=row[6],
                detailed_abstract=row[7],
                supporting_data_quotes=row[8],
                date_added=row[9],
            )
        finally:
            conn.close()

    def insert_article(
        self,
        source: str,
        url: str,
        title: str,
        author: str,
        article_text: str,
        core_thesis: str,
        detailed_abstract: str,
        supporting_data_quotes: str,
    ) -> None:
        conn = self._connect()
        try:
            cur = conn.cursor()
            # Prepare quotes_json dual-write
            import json
            items = []
            for line in str(supporting_data_quotes).splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith(('*', '-', '•')):
                    line = line.lstrip('*-•').strip()
                items.append(line)
            quotes_json = json.dumps(items, ensure_ascii=False)
            cur.execute(
                (
                    "INSERT OR IGNORE INTO articles (source, url, title, author, article_text, "
                    "core_thesis, detailed_abstract, supporting_data_quotes, quotes_json) VALUES (?,?,?,?,?,?,?,?,?)"
                ),
                (
                    source,
                    url,
                    title,
                    author,
                    article_text,
                    core_thesis,
                    detailed_abstract,
                    supporting_data_quotes,
                    quotes_json,
                ),
            )
            conn.commit()
        finally:
            conn.close()
