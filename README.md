# FPFA Summary

Foreign Policy / Foreign Affairs article ingestion plus a small API and Flutter client.

This README reflects the repository as it exists on March 24, 2026.

## Repository Structure

- `summarize_fa_hardened.py`: Foreign Affairs ingestion script.
- `summarize_fp.py`: Foreign Policy ingestion script.
- `app.py`: Flask API and server-rendered homepage, default local port `5000`.
- `main.py`: FastAPI variant of the API, default local port `8000`.
- `services/`: article storage, publication-date normalization, service layer.
- `scripts/`: migration, parser canary, smoke tests, repair utilities.
- `fpfa_app/`: Flutter client for web/mobile.

## Verified Deployment Topology

The repository is now wired for the cheapest practical GCP path:

| Component | Where it runs | Defined by |
| --- | --- | --- |
| Scheduled ingestion (`Update articles`) | GitHub-hosted Actions runner writing into GCP Firestore | `.github/workflows/update_articles.yml` |
| Backend deploy CI | GitHub-hosted Actions runner | `.github/workflows/master_ppfflaskapp.yml` |
| Production backend target | Google Cloud Run | `.github/workflows/master_ppfflaskapp.yml` |
| Production web frontend target | Firebase Hosting | `.github/workflows/deploy_flutter_static_web_apps.yml` + `firebase.json` |
| Android distribution | Firebase App Distribution | `.github/workflows/deploy_android.yml` |
| Production article store | Firestore Native (`articles` collection by default) | `services/article_repository.py` + workflow env |
| Local development store | SQLite `articles.db` unless env overrides it | `services/article_repository.py` |

Important clarification:

- Azure is no longer the intended production path in this branch.
- The backend and frontend deployment workflows now target GCP / Firebase.
- The scheduled ingestion job still runs on GitHub Actions because that is the lowest-bill runner, but it writes into Firestore in GCP.

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the full operations view.

## Why This Is The Lowest-Bill Setup

- Cloud Run can scale to zero, so there is no always-on VM bill for the API.
- Firestore avoids the baseline monthly cost of Cloud SQL.
- Firebase Hosting is the cheapest fit for the static Flutter web build.
- Android distribution stays on Firebase App Distribution, which the repo already used.

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

## Storage Behavior

- If `ARTICLE_STORE=firestore`, the backend and ingestion scripts use Firestore.
- Firestore config comes from:
  - `FIRESTORE_PROJECT_ID`
  - `ARTICLES_COLLECTION` (default: `articles`)
- If `DATABASE_URL` is set to a SQLAlchemy/SQLite URL, the backend uses that database.
- Otherwise the app falls back to local SQLite.
- Local SQLite path resolution:
  - `ARTICLES_DB_PATH`
  - `FPFA_DB_PATH`
  - fallback: `articles.db` in the repo root

The storage layer lives in `services/article_repository.py`.

## Running Ingestion Scripts

These are the ingestion entrypoints wired into GitHub Actions:

```bash
python summarize_fa_hardened.py 7
python summarize_fp.py 7
```

Required environment for real summarization:

```bash
export GEMINI_API_KEY=your_key_here
```

Firestore target:

```bash
export ARTICLE_STORE=firestore
export FIRESTORE_PROJECT_ID=pressreview-458312
export ARTICLES_COLLECTION=articles
```

Local SQLite fallback:

```bash
unset ARTICLE_STORE
unset FIRESTORE_PROJECT_ID
python summarize_fa_hardened.py 1
```

## Running The Flutter App

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
flutter build web --dart-define=API_BASE_URL=https://fpfa-summary-api-1028212947283.europe-west1.run.app
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
python scripts/smoke_test_api.py --base-url https://fpfa-summary-api-1028212947283.europe-west1.run.app
```

Flutter:

```bash
cd fpfa_app
flutter analyze
flutter test
```

## Firebase / GCP Files

- `.firebaserc`: default Firebase project `pressreview-458312`
- `firebase.json`: Firebase Hosting config for the Flutter web build
- `fpfa_app/android/app/google-services.json`: Android Firebase config
- `.github/workflows/deploy_android.yml`: APK distribution to Firebase App Distribution

## Current Documentation Scope

Older notes in the repo still mention Azure App Service / Azure Static Web Apps. Those are legacy notes, not the active deployment target after this GCP migration.
