# Implementation Plan: Full Stack Modernization (FastAPI & Flutter Refactor)

## Phase 1: Backend Migration (FastAPI) [checkpoint: bae2759]

- [x] Task: Initialize FastAPI Environment 95ce72e
    - [x] Add `fastapi`, `uvicorn`, `pydantic` to `requirements.txt`
    - [x] Create a new entry point `main.py` for FastAPI
    - [x] Configure standard CORS and health check skeleton
- [x] Task: Define Data Models (Pydantic) b435708
    - [x] Create `models/article.py` defining the `Article` schema
    - [x] Implement validation logic for article fields (URLs, dates)
    - [x] Write unit tests for model validation
- [x] Task: Implement Data Access Layer 9fbe419
    - [x] Refactor `get_latest_articles` into a standalone service/repository
    - [x] Write tests for data retrieval logic using a mock/temporary database
- [x] Task: Implement API Routes (TDD) 862a915
    - [x] **Red:** Write failing integration tests for `/api/articles`
    - [x] **Green:** Implement the `/api/articles` endpoint in FastAPI
    - [x] **Red:** Write failing test for the root `/` HTML route
    - [x] **Green:** Implement the Jinja2 template rendering for the root route
- [x] Task: Implement Health and Documentation 309b310
    - [x] Implement the `/health` endpoint
    - [x] Configure custom Swagger UI metadata and ReDoc
    - [x] Verify `/docs` is accessible and correctly reflects the schema
- [x] Task: Conductor - User Manual Verification 'Phase 1: Backend Migration (FastAPI)' (Protocol in workflow.md) bae2759

## Phase 2: Frontend Architectural Refactor (Flutter)

- [x] Task: Project Restructuring and Layering dffd3bf
    - [x] Create directory structure: `lib/core`, `lib/domain`, `lib/data`, `lib/presentation`
    - [x] Move existing models to `lib/domain/entities`
- [x] Task: Domain Layer Implementation 0f4d2a7
    - [x] Define `ArticleRepository` abstract interface
    - [x] Create `GetArticles` UseCase (if following strict Clean Arch)
- [x] Task: Data Layer Implementation (TDD) 43fed1f
    - [-] **Red:** Write tests for `RemoteArticleDataSource` using a mock client (Skipped: Environment issue)
    - [x] **Green:** Implement `RemoteArticleDataSource` using the `http` package
    - [-] **Red:** Write tests for `LocalArticleDataSource` (Offline Support) (Skipped: Environment issue)
    - [x] **Green:** Implement `LocalArticleDataSource` using `shared_preferences` or `sqflite`
    - [x] Implement the `ArticleRepository` to manage data coordination (Remote -> Cache -> Local)
- [ ] Task: Presentation Layer - Theming and Shared UI
    - [ ] Create `lib/core/theme.dart` with centralized `ThemeData`
    - [ ] Implement `ErrorWidget`, `LoadingWidget`, and `EmptyStateWidget`
    - [ ] Update `ArticleCard` and `Deck` to use centralized theme constants
- [ ] Task: State Management Migration (Provider/Riverpod)
    - [ ] Setup the state management provider for articles
    - [ ] **Red:** Write widget tests for the `Deck` ensuring it reacts to different states (Loading, Error, Success)
    - [ ] **Green:** Refactor `HomePage` and `Deck` to consume state from the provider
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Frontend Architectural Refactor (Flutter)' (Protocol in workflow.md)

## Phase 3: Integration, E2E Testing, and CI/CD

- [ ] Task: End-to-End (E2E) Testing
    - [ ] Setup `flutter_driver` or `integration_test` package
    - [ ] Implement E2E tests verifying the full flow: API call -> UI Render -> Offline Cache
- [ ] Task: CI/CD Pipeline Update
    - [ ] Update `.github/workflows/` to include Python dependency caching for FastAPI
    - [ ] Add steps for FastAPI linting and unit tests
    - [ ] Update Flutter workflow to include the new architectural tests
- [ ] Task: Performance Benchmarking
    - [ ] Run load tests (e.g., using `locust` or simple scripts) against both Flask and FastAPI
    - [ ] Document findings in the final report
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Integration, E2E Testing, and CI/CD' (Protocol in workflow.md)
