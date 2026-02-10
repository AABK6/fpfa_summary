from __future__ import annotations

import os
import sqlite3
from typing import Any

from flask import Flask, jsonify, render_template
from flask_cors import CORS

from models.sources import normalize_article_source
from services.article_service import resolve_articles_db_path
from template_utils import safe_date

app = Flask(__name__)
CORS(app)
app.jinja_env.filters["safe_date"] = safe_date


@app.context_processor
def utility_processor() -> dict[str, Any]:
    def static_url(path: str) -> str:
        return app.url_for("static", filename=path)

    return {"static_url": static_url}


def _normalize_source_for_response(raw_source: str) -> str:
    """Return canonical source names while preserving unknown legacy values safely."""
    try:
        return normalize_article_source(raw_source)
    except ValueError:
        return raw_source


def get_latest_articles(limit: int = 10) -> list[dict[str, Any]]:
    """Fetch latest articles sorted by date_added DESC."""
    db_path = resolve_articles_db_path()
    if not os.path.exists(db_path):
        return []

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(articles)")
        available_columns = {row[1] for row in cursor.fetchall()}
        publication_date_expr = (
            "publication_date"
            if "publication_date" in available_columns
            else "NULL AS publication_date"
        )

        cursor.execute(
            """
            SELECT
                id, source, url, title, author, article_text,
                core_thesis, detailed_abstract, supporting_data_quotes,
                {publication_date_expr}, date_added
            FROM articles
            ORDER BY datetime(date_added) DESC
            LIMIT ?
            """.format(publication_date_expr=publication_date_expr),
            (limit,),
        )
        rows = cursor.fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()

    return [
        {
            "id": row[0],
            "source": _normalize_source_for_response(row[1]),
            "url": row[2],
            "title": row[3],
            "author": row[4],
            "article_text": row[5],
            "core_thesis": row[6],
            "detailed_abstract": row[7],
            "supporting_data_quotes": row[8],
            "publication_date": row[9],
            "date_added": row[10],
        }
        for row in rows
    ]


@app.get("/health")
def health() -> Any:
    return jsonify({"status": "healthy"})


@app.get("/")
def home() -> str:
    articles = get_latest_articles(limit=20)
    return render_template("index.html", articles=articles)


@app.get("/api/articles")
def api_articles() -> Any:
    articles = get_latest_articles(limit=20)
    return jsonify(articles)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
