from __future__ import annotations

from typing import List

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from models.article import Article
from services.article_service import ArticleService, resolve_articles_db_path
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
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_article_service() -> ArticleService:
    return ArticleService(db_path=resolve_articles_db_path())


@app.get("/health")
async def health_check() -> JSONResponse:
    return JSONResponse(content={"status": "healthy"}, status_code=200)


@app.get("/api/articles", response_model=List[Article])
async def get_articles(service: ArticleService = Depends(get_article_service)) -> list[Article]:
    return service.get_latest_articles(limit=20)


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, service: ArticleService = Depends(get_article_service)) -> HTMLResponse:
    articles = service.get_latest_articles(limit=20)
    return templates.TemplateResponse(request, "index.html", {"articles": articles})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
