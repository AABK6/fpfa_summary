# Modernization Roadmap: FPFA Summary

## Backend Modernization: Flask vs. FastAPI

### Current State
The project currently uses **Flask 3.1.2** with **SQLite**. The backend provides a simple HTML interface and a single JSON API endpoint.

### Comparison

| Feature | Flask | FastAPI |
| :--- | :--- | :--- |
| **Performance** | Synchronous by default, slower for high concurrency. | Asynchronous (async/await), built on Starlette, high performance. |
| **Type Safety** | Minimal, relies on manual validation. | Native support for Python type hints, automatic Pydantic validation. |
| **Documentation** | Requires extra extensions (e.g., Flasgger). | Automatic interactive Swagger/ReDoc out of the box. |
| **Security** | Standard features, manual input sanitization. | Built-in security utilities, robust type-driven validation. |
| **Modernity** | Mature, but showing its age for API-first apps. | Modern, industry-standard for new Python APIs. |

### Recommendation: Migrate to FastAPI
Given the project's goal of modernization and the small size of the current codebase (`app.py`), migrating to **FastAPI** is highly recommended. 

#### Benefits
- **Automatic Docs:** Immediate access to `/docs` for testing scrapers.
- **Type Safety:** Clearer contracts between backend and Flutter/Web frontends.
- **Async Support:** Better handling of database I/O and potential future integrations (e.g., real-time updates).

#### Migration Plan
1.  **Dependencies:** Add `fastapi`, `uvicorn`, and `pydantic`.
2.  **Schema Definition:** Define Pydantic models for `Article` to replace raw dictionaries.
3.  **Route Migration:** 
    - Convert `@app.route('/')` to `@app.get("/", response_class=HTMLResponse)`.
    - Convert `@app.route('/api/articles')` to `@app.get("/api/articles", response_model=List[Article])`.
4.  **Database:** Refactor `get_latest_articles` to be async-friendly (using `aiosqlite` or simply keeping it sync for now as a first step).
5.  **Templates:** Keep Jinja2 for the home page (FastAPI supports Jinja2 via `Jinja2Templates`).

---

## Frontend Modernization: Flutter Evaluation

### Current State
The frontend is a single-file **Flutter** application (`main.dart`) that uses basic `setState` for state management and manual JSON parsing.

### Identified Issues
- **Tight Coupling:** UI widgets, business logic, and API calls are all mixed in `main.dart`.
- **Manual State Management:** Complex UI interactions (the "Deck" of cards) are handled with manual state updates, which are difficult to test and maintain.
- **Brittle Parsing:** Date parsing and string splitting (for quotes) rely on specific string formats that might break if the backend format changes.
- **Hardcoded Config:** Backend URLs and environment settings are hardcoded or use fragile logic.
- **No Error Handling:** Minimal UI feedback for network failures or parsing errors.

### Recommendation: Refactor for Scalability
Maintain **Flutter** as the platform but perform a significant refactor to adopt modern architectural patterns.

#### Proposed Improvements
1.  **Clean Architecture:** Split the code into layers:
    - **Data Layer:** Repositories and Data Sources (handling HTTP calls).
    - **Domain Layer:** Entities (Models) and potentially Use Cases.
    - **Presentation Layer:** Widgets and State Management.
2.  **State Management:** Replace manual `setState` logic with a more robust solution like **Provider** or **Riverpod**. This will decouple the "Deck" logic from the UI.
3.  **Robust Models:** Use `json_serializable` for safer and more maintainable JSON parsing.
4.  **Dependency Injection:** Use a service locator like `get_it` to manage singleton services (API clients, repositories).
5.  **Environment Configuration:** Use `flutter_dotenv` or similar to handle different backend URLs for dev/prod.
6.  **Improved UX:** Add proper loading states, error boundaries, and empty state handling.

---

## Roadmap Summary
- **Backend:** Migrate from Flask to **FastAPI** to improve API reliability and performance.
- **Frontend:** Refactor the existing **Flutter** app into a modular, testable architecture.
- **Integration:** Standardize the JSON contract between FastAPI (Pydantic models) and Flutter (Entities) to ensure long-term stability.
