from pathlib import Path

from services.article_service import resolve_articles_db_path


def test_resolve_articles_db_path_defaults_to_repo_root(monkeypatch):
    monkeypatch.delenv("ARTICLES_DB_PATH", raising=False)
    monkeypatch.delenv("FPFA_DB_PATH", raising=False)

    expected = Path(__file__).resolve().parents[1] / "articles.db"
    assert resolve_articles_db_path() == str(expected)


def test_resolve_articles_db_path_uses_env_override(monkeypatch, tmp_path):
    monkeypatch.delenv("FPFA_DB_PATH", raising=False)
    custom_db = tmp_path / "custom_articles.db"
    monkeypatch.setenv("ARTICLES_DB_PATH", str(custom_db))

    assert resolve_articles_db_path() == str(custom_db)


def test_resolve_articles_db_path_uses_legacy_fpfa_override(monkeypatch, tmp_path):
    monkeypatch.delenv("ARTICLES_DB_PATH", raising=False)
    custom_db = tmp_path / "legacy_custom_articles.db"
    monkeypatch.setenv("FPFA_DB_PATH", str(custom_db))

    assert resolve_articles_db_path() == str(custom_db)


def test_resolve_articles_db_path_prefers_articles_db_path(monkeypatch, tmp_path):
    legacy_db = tmp_path / "legacy.db"
    new_db = tmp_path / "new.db"
    monkeypatch.setenv("FPFA_DB_PATH", str(legacy_db))
    monkeypatch.setenv("ARTICLES_DB_PATH", str(new_db))

    assert resolve_articles_db_path() == str(new_db)
