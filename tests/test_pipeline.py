import os
from pathlib import Path

import fpfa.scrapers.base as base
import fpfa.scrapers.foreign_affairs as fa
import fpfa.scrapers.foreign_policy as fp
from fpfa.pipeline import run_pipeline
from fpfa.summarizers.stub import StubSummaryGenerator
from fpfa.db.repo import ArticleRepository
from fpfa.db.schema import ensure_schema


class FakeResp:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


class FakeSession:
    def __init__(self, mapping):
        self._mapping = mapping

    def get(self, url, **kwargs):
        return FakeResp(self._mapping.get(url, ""))


def test_pipeline_end_to_end(monkeypatch, tmp_path: Path):
    fixtures = Path(__file__).parent / "fixtures"
    mapping = {
        fa.MOST_RECENT: (fixtures / "fa_list.html").read_text(),
        "https://www.foreignaffairs.com/article-1": (fixtures / "fa_article.html").read_text(),
        "https://www.foreignaffairs.com/article-2": (fixtures / "fa_article.html").read_text(),
        fp.LATEST: (fixtures / "fp_list.html").read_text(),
        "https://foreignpolicy.com/2024/01/01/first/": (fixtures / "fp_article.html").read_text(),
        "https://foreignpolicy.com/2024/01/02/second/": (fixtures / "fp_article.html").read_text(),
    }

    monkeypatch.setattr(base, "build_session", lambda **kwargs: FakeSession(mapping))

    db = tmp_path / "pipeline.db"
    os.environ["FPFA_DB_PATH"] = str(db)
    ensure_schema(str(db))
    repo = ArticleRepository(str(db))

    # First run inserts 4 (2 FA + 2 FP)
    inserted = run_pipeline(["fa", "fp"], limit=5, summarizer=StubSummaryGenerator())
    assert inserted == 4
    assert len(repo.get_latest(limit=10)) == 4

    # Second run should be idempotent, inserts 0
    inserted2 = run_pipeline(["fa", "fp"], limit=5, summarizer=StubSummaryGenerator())
    assert inserted2 == 0

    # Dry run should not persist
    inserted3 = run_pipeline(["fa"], limit=1, summarizer=StubSummaryGenerator(), persist=False)
    assert inserted3 >= 0
    assert len(repo.get_latest(limit=10)) == 4

