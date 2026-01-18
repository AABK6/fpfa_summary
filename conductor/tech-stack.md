# Technology Stack

## Current Stack (Source of Truth)

**Programming Languages:**
- Python (Backend)
- Dart (Frontend)

**Frameworks:**
- Flask (Web API)
- Flutter (Mobile/Web Frontend)

**Database:**
- SQLite (`articles.db`)

**Key Libraries/Tools:**
- BeautifulSoup4, Selenium, Playwright (Scraping)
- Google GenAI (Summarization)
- Flask-CORS (Cross-Origin Resource Sharing)

**Deployment:**
- GitHub Actions (CI/CD)

## Target Stack (Modernization)

**Backend:**
- **FastAPI:** Selected to replace Flask for improved performance, async support, and automatic documentation.
- **Pydantic:** For robust data validation and schema definition.

**Frontend:**
- **Flutter (Refactored):** Retained as the frontend framework but with a modernized architecture (Clean Architecture, Provider/Riverpod for state management).
