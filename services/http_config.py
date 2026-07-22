from __future__ import annotations

import os


DEFAULT_ALLOWED_ORIGINS = (
    "https://ppf-fpfa-summary-prod.web.app",
    "https://ppf-fpfa-summary-prod.firebaseapp.com",
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:5000",
    "http://localhost:8000",
    "http://localhost:8080",
    "http://localhost:8088",
    "http://127.0.0.1:5000",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8088",
)


def allowed_origins() -> list[str]:
    """Return explicit browser origins, optionally overridden by the environment."""

    configured = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if not configured.strip():
        return list(DEFAULT_ALLOWED_ORIGINS)
    return [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
