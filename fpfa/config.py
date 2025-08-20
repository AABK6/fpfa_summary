import os
from dataclasses import dataclass


def _default_db_path() -> str:
    # Default to project root articles.db (fpfa/.. is project root)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    return os.path.join(project_root, "articles.db")


@dataclass
class Config:
    """Runtime configuration for the backend."""

    db_path: str = os.environ.get("FPFA_DB_PATH", _default_db_path())
    model_core: str = os.environ.get("FPFA_MODEL_CORE", "gemini-2.5-flash-lite")
    model_detail: str = os.environ.get("FPFA_MODEL_DETAIL", "gemini-2.5-flash")
    model_quotes: str = os.environ.get("FPFA_MODEL_QUOTES", "gemini-2.5-flash")

def load_config() -> Config:
    # Read environment at call-time to support tests changing FPFA_DB_PATH dynamically.
    return Config(
        db_path=os.environ.get("FPFA_DB_PATH", _default_db_path()),
        model_core=os.environ.get("FPFA_MODEL_CORE", "gemini-2.5-flash-lite"),
        model_detail=os.environ.get("FPFA_MODEL_DETAIL", "gemini-2.5-flash"),
        model_quotes=os.environ.get("FPFA_MODEL_QUOTES", "gemini-2.5-flash"),
    )
