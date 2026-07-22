from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from models.article import ArticleSummary
from models.sources import normalize_article_source
from services.article_service import get_cached_article_service
from services.http_config import allowed_origins
from template_utils import safe_date

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": allowed_origins()}})
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
    for article in service.get_latest_article_summaries(limit=limit):
        payload = ArticleSummary.model_validate(article).model_dump(mode="json")
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
    raw_limit = request.args.get("limit", "20")
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        return jsonify({"error": "limit must be an integer between 1 and 50"}), 400
    if not 1 <= limit <= 50:
        return jsonify({"error": "limit must be between 1 and 50"}), 400

    response = jsonify(get_latest_articles(limit=limit))
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=3600"
    return response


@app.after_request
def set_security_headers(response: Any) -> Any:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault("Cross-Origin-Resource-Policy", "same-site")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; img-src 'self' data: https:; style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; connect-src 'self' https://*.run.app; frame-ancestors 'none'",
    )
    return response


if __name__ == "__main__":
    app.run(
        host=os.getenv("FPFA_DEV_HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FPFA_DEBUG", "0") == "1",
    )
