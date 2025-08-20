import sqlite3
from typing import Optional


DDL_ARTICLES = """
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    url TEXT UNIQUE,
    title TEXT,
    author TEXT,
    article_text TEXT,
    core_thesis TEXT,
    detailed_abstract TEXT,
    supporting_data_quotes TEXT,
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

DDL_IDX_DATE = (
    "CREATE INDEX IF NOT EXISTS idx_articles_date ON articles(date_added DESC)"  # type: ignore
)


def ensure_schema(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(DDL_ARTICLES)
        cur.execute(DDL_IDX_DATE)
        _ensure_quotes_json_column(cur)
        conn.commit()
    finally:
        conn.close()


def _ensure_quotes_json_column(cur: sqlite3.Cursor) -> None:
    cur.execute("PRAGMA table_info(articles)")
    cols = [row[1] for row in cur.fetchall()]
    if "quotes_json" not in cols:
        cur.execute("ALTER TABLE articles ADD COLUMN quotes_json TEXT")


def migrate_quotes_to_json(db_path: str) -> int:
    """Backfill quotes_json from supporting_data_quotes. Returns rows updated."""
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        _ensure_quotes_json_column(cur)
        cur.execute(
            "SELECT id, supporting_data_quotes FROM articles WHERE (quotes_json IS NULL OR quotes_json = '') AND supporting_data_quotes IS NOT NULL AND supporting_data_quotes <> ''"
        )
        rows = cur.fetchall()
        import json

        updated = 0
        for _id, quotes_text in rows:
            # Split on lines starting with '-' or '*' or numbered bullets
            items = []
            for line in str(quotes_text).splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith(('*', '-', '•')):
                    line = line.lstrip('*-•').strip()
                items.append(line)
            qjson = json.dumps(items, ensure_ascii=False)
            cur.execute("UPDATE articles SET quotes_json = ? WHERE id = ?", (qjson, _id))
            updated += 1
        conn.commit()
        return updated
    finally:
        conn.close()
