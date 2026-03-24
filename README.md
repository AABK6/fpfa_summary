# FPFA Summary

Foreign Policy / Foreign Affairs article ingestion plus a small API and Flutter client.

This README reflects the repository as it exists on March 24, 2026.

## Repository Structure

- `summarize_fa_hardened.py`: Foreign Affairs ingestion script.
- `summarize_fp.py`: Foreign Policy ingestion script.
- `app.py`: Flask API and server-rendered homepage, default local port `5000`.
- `main.py`: FastAPI variant of the API, default local port `8000`.
- `services/`: DB access, publication-date normalization, service layer.
- `scripts/`: migration, parser canary, smoke tests, repair utilities.
- `fpfa_app/`: Flutter client for web/mobile.

## Verified Deployment Topology

There are multiple runtimes in this repo. They do not all run in the same place.

| Component | Where it runs | Defined by |
| --- | --- | --- |
| Scheduled ingestion (`Update articles`) | GitHub-hosted Actions runner (`ubuntu-latest`) | `.github/workflows/update_articles.yml` |
| Backend deploy CI | GitHub-hosted Actions runner (`ubuntu-latest`) | `.github/workflows/master_ppfflaskapp.yml` |
| Production backend target | Azure Web App (`PPFFlaskApp` by default) | `.github/workflows/master_ppfflaskapp.yml` |
| Production web frontend target | Azure Static Web Apps | `.github/workflows/deploy_flutter_static_web_apps.yml` |
| Android distribution | Firebase App Distribution | `.github/workflows/deploy_android.yml` |
| Database in CI / production | Remote DB via `DATABASE_URL` secret, intended for Azure SQL | workflow env + deployment notes |
| Local development database | SQLite `articles.db` unless env overrides it | `services/article_repository.py` |

Important clarification:

- There is Firebase usage in this repo, but not for web hosting.
- The active web deployment workflow targets Azure Static Web Apps.
- The active Google/Firebase integration is Android APK distribution plus Firebase project metadata files.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the full operations view.

## Running Locally

Install Python dependencies:

```bash
pip install -r requirements.txt
```

### Flask app

```bash
python app.py
```

- Binds to `http://localhost:5000`
- Endpoints:
  - `GET /health`
  - `GET /api/articles`
  - `GET /`

### FastAPI app

```bash
python main.py
```

- Binds to `http://localhost:8000`
- Endpoints:
  - `GET /health`
  - `GET /api/articles`
  - `GET /`
  - `GET /docs`
  - `GET /redoc`

## Database Behavior

- If `DATABASE_URL` is set, the backend and ingestion scripts use that remote database.
- Otherwise they use local SQLite.
- Local SQLite path resolution:
  - `ARTICLES_DB_PATH`
  - `FPFA_DB_PATH`
  - fallback: `articles.db` in the repo root

The DB access layer lives in `services/article_repository.py`.

## Running Ingestion Scripts

These are the ingestion entrypoints currently wired into GitHub Actions:

```bash
python summarize_fa_hardened.py 7
python summarize_fp.py 7
```

Required environment for real summarization:

```bash
export GEMINI_API_KEY=your_key_here
```

Optional remote DB:

```bash
export DATABASE_URL=your_connection_string_here
```

## Running the Flutter App

From `fpfa_app/`:

```bash
flutter pub get
flutter run
```

The Flutter app resolves its backend base URL like this:

- `API_BASE_URL` compile-time define if provided
- otherwise Android emulator fallback: `http://10.0.2.2:8000`
- otherwise local fallback: `http://localhost:8000`

Examples:

```bash
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:5000
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000
```

If you run `app.py`, pass `API_BASE_URL=http://localhost:5000`.
If you run `main.py`, the Flutter default already matches port `8000`.

## Tests

Run the Python test suite:

```bash
pytest tests -q
```

Targeted checks:

```bash
python scripts/live_parser_canary.py
python scripts/smoke_test_api.py --base-url https://your-app.azurewebsites.net
```

Flutter:

```bash
cd fpfa_app
flutter analyze
flutter test
```

## Notes on Legacy / Ambiguous Files

- `.firebaserc` points to Firebase project `pressreview-458312`.
- `fpfa_app/android/app/google-services.json` is present.
- `.github/workflows/deploy_android.yml` uploads Android APKs to Firebase App Distribution.
- There is no Firebase Hosting workflow in this repo.
- `firebase-debug.log` is a local debug artifact and is ignored by git.

## Current Documentation Scope

Older notes in the repo describe a broader refactor and an `fpfa` package/CLI. That package is not present in this branch, so this README documents only the code and workflows that are actually checked in.
