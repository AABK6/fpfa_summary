from __future__ import annotations

from typing import Any

from flask import Flask, jsonify, render_template
from flask_cors import CORS

from models.sources import normalize_article_source
from services.article_service import get_cached_article_service
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
    serialized: list[dict[str, Any]] = []
    service = get_cached_article_service()
    for article in service.get_latest_articles(limit=limit):
        payload = article.model_dump(mode="json")
        payload["source"] = _normalize_source_for_response(str(payload["source"]))
        serialized.append(payload)
    return serialized


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
