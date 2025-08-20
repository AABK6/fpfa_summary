from flask import Blueprint, jsonify, render_template, request
from ..config import load_config
from ..db.repo import ArticleRepository
from ..db.schema import ensure_schema


bp = Blueprint("main", __name__)


def _repo() -> ArticleRepository:
    cfg = load_config()
    ensure_schema(cfg.db_path)
    return ArticleRepository(cfg.db_path)


@bp.route("/")
def home():
    repo = _repo()
    # Match prior behavior: limit 20 and reverse order after fetching DESC
    articles = repo.get_latest(limit=20)
    data = [a.to_dict() for a in articles]
    data.reverse()
    return render_template("index.html", articles=data)


@bp.route("/api/articles")
def api_articles():
    repo = _repo()
    try:
        limit = int(request.args.get("limit", "20"))
    except ValueError:
        limit = 20
    try:
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        offset = 0
    source = request.args.get("source")

    articles = repo.get_latest(limit=limit, source=source, offset=offset)
    data = [a.to_dict() for a in articles]
    # Preserve existing reverse to match current JSON order
    data.reverse()
    return jsonify(data)

