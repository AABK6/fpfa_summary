from pathlib import Path

from services.article_service import resolve_articles_db_path


def test_resolve_articles_db_path_defaults_to_repo_root(monkeypatch):
    monkeypatch.delenv("ARTICLES_DB_PATH", raising=False)

    expected = Path(__file__).resolve().parents[1] / "articles.db"
    assert resolve_articles_db_path() == str(expected)


def test_resolve_articles_db_path_uses_env_override(monkeypatch, tmp_path):
    custom_db = tmp_path / "custom_articles.db"
    monkeypatch.setenv("ARTICLES_DB_PATH", str(custom_db))

    assert resolve_articles_db_path() == str(custom_db)
