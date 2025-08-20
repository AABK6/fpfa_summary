import os
import pytest

from fpfa.pipeline import run_pipeline
from fpfa.summarizers.stub import StubSummaryGenerator


pytestmark = pytest.mark.live


def test_live_pipeline_dry_run(monkeypatch, tmp_path):
    if os.environ.get("LIVE_TESTS") != "1":
        pytest.skip("LIVE_TESTS=1 not set; skipping live network tests")

    # Use a temp DB even though we won't persist, just to exercise init
    os.environ["FPFA_DB_PATH"] = str(tmp_path / "live.db")
    inserted = run_pipeline(["fa", "fp"], limit=1, summarizer=StubSummaryGenerator(), persist=False)
    assert inserted >= 1

