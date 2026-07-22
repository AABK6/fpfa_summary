from __future__ import annotations

from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from models.article import ArticleSummary
from services.article_service import ArticleService, get_cached_article_service
from services.http_config import allowed_origins
from template_utils import safe_date

app = FastAPI(
    title="FPFA Summary API",
    description="API for Foreign Policy & Foreign Affairs Summaries",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


def static_url(path: str) -> str:
    return app.url_path_for("static", path=path)


templates.env.globals["static_url"] = static_url
templates.env.filters["safe_date"] = safe_date

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def set_security_headers(request: Request, call_next):
    response = await call_next(request)
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

def get_article_service() -> ArticleService:
    return get_cached_article_service()


@app.get("/health")
async def health_check() -> JSONResponse:
    return JSONResponse(content={"status": "healthy"}, status_code=200)


@app.get("/api/articles", response_model=list[ArticleSummary])
async def get_articles(
    response: Response,
    limit: int = Query(default=20, ge=1, le=50),
    service: ArticleService = Depends(get_article_service),
) -> list[ArticleSummary]:
    response.headers["Cache-Control"] = "public, max-age=300, stale-while-revalidate=3600"
    return service.get_latest_article_summaries(limit=limit)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, service: ArticleService = Depends(get_article_service)) -> HTMLResponse:
    articles = service.get_latest_article_summaries(limit=20)
    return templates.TemplateResponse(request, "index.html", {"articles": articles})


if __name__ == "__main__":
    import os
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("FPFA_DEV_HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("FPFA_RELOAD", "0") == "1",
    )
