import os
from pathlib import Path

from fpfa.api.app import create_app
from fpfa.db.schema import ensure_schema
from fpfa.db.repo import ArticleRepository


def test_api_articles_temp_db(tmp_path):
    db = tmp_path / "test.db"
    os.environ["FPFA_DB_PATH"] = str(db)
    ensure_schema(str(db))
    repo = ArticleRepository(str(db))
    # Insert two rows with older/newer dates naturally via default CURRENT_TIMESTAMP
    repo.insert_article(
        source="Foreign Policy",
        url="https://foreignpolicy.com/x",
        title="T1",
        author="A1",
        article_text="txt",
        core_thesis="core",
        detailed_abstract="abs",
        supporting_data_quotes="- q1\n- q2",
    )
    repo.insert_article(
        source="Foreign Affairs",
        url="https://www.foreignaffairs.com/y",
        title="T2",
        author="A2",
        article_text="txt2",
        core_thesis="core2",
        detailed_abstract="abs2",
        supporting_data_quotes="- q3\n- q4",
    )

    app = create_app()
    with app.test_client() as c:
        r = c.get("/api/articles?limit=2")
        assert r.status_code == 200
        data = r.get_json()
        assert isinstance(data, list) and len(data) == 2
        # Route reverses order after DESC; last inserted should appear first in DB, then reversed
        # So expect [older, newer]
        assert {data[0]["title"], data[1]["title"]} == {"T1", "T2"}

