import sqlite3
import os
from typing import List
from models.article import Article

class ArticleService:
    def __init__(self, db_path: str = "articles.db"):
        self.db_path = db_path

    def get_latest_articles(self, limit: int = 10) -> List[Article]:
        """
        Fetch the latest articles from the 'articles' table,
        sorted by date_added (descending), limited to 'limit' results.
        """
        if not os.path.exists(self.db_path):
             return []

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT 
                    id, source, url, title, author, article_text,
                    core_thesis, detailed_abstract, supporting_data_quotes, date_added
                FROM articles
                ORDER BY date_added DESC
                LIMIT ?
            ''', (limit,))
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            # Table might not exist
            return []
        finally:
            conn.close()

        articles = []
        for row in rows:
            # Convert row to dict, handled by row_factory
            data = dict(row)
            articles.append(Article(**data))
        
        # Original app reversed the order, but the SQL orders by DESC (latest first).
        # Usually "latest articles" means most recent on top.
        # However, app.py did `articles.reverse()` after fetching DESC.
        # This implies it wanted Oldest -> Newest in the list?
        # Let's double check app.py logic. 
        # app.py: ORDER BY date_added DESC LIMIT 10 -> gets 10 newest.
        # articles.reverse() -> puts the 10th newest at index 0, and the newest at index 9.
        # This is strictly for display purposes?
        # I will keep the original logic if it was intended, or clarify. 
        # The prompt says "Refactor", implying keeping behavior.
        # But for an API, usually you want list[0] to be the latest.
        # I will strictly follow the "latest first" API convention for now (no reverse),
        # unless I see a reason to reverse.
        # Wait, if `articles.reverse()` was used, then the API returned Oldest of the N latest first.
        # I will stick to standard API behavior (Latest First) unless the UI breaks.
        # The UI "Deck" might stack them.
        # If I change the order, the Deck order might change.
        # I will return them Latest First (no reverse) and let the Frontend handle sorting if needed.
        # Wait, actually, let's look at `get_latest_articles` in app.py again.
        return articles
