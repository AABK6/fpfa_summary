from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import List
from models.article import Article
from services.article_service import ArticleService

app = FastAPI(
    title="FPFA Summary API",
    description="API for Foreign Policy & Foreign Affairs Summaries",
    version="1.0.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


def static_url(path: str) -> str:
    return app.url_path_for("static", path=path)


templates.env.globals["static_url"] = static_url

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:3000",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_article_service():
    return ArticleService()

@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify system status.
    """
    return JSONResponse(content={"status": "healthy"}, status_code=200)

@app.get("/api/articles", response_model=List[Article])
async def get_articles(service: ArticleService = Depends(get_article_service)):
    """
    Fetch the latest articles.
    """
    return service.get_latest_articles(limit=20)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request, service: ArticleService = Depends(get_article_service)):
    """
    Main route: Fetch and display the latest articles.
    """
    articles = service.get_latest_articles(limit=20)
    # Convert Pydantic models to dicts for Jinja2 if necessary, usually Jinja2 handles objects well 
    # but to be safe/consistent with Flask behavior:
    # app.py passed a list of dicts (because row_factory result was converted).
    # Here we have List[Article]. Jinja2 can access attributes like article.title.
    # We need to ensure index.html supports object attribute access ({{ article.title }}) 
    # or if it expects dict access ({{ article['title'] }}).
    # Let's check index.html.
    return templates.TemplateResponse(request, "index.html", {"articles": articles})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
