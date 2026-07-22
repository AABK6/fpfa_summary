# FPFA Summary

FPFA collects articles from *Foreign Policy* and *Foreign Affairs*, produces structured summaries, serves a small public API, and presents them in a responsive Flutter reader.

## Production topology

| Component | Current target |
| --- | --- |
| Web reader | `https://ppf-fpfa-summary-prod.web.app` |
| Public API | `https://fpfa-summary-api-1076204999548.europe-west1.run.app` |
| Article store | Firestore in `ppf-fpfa-summary-prod` |
| Scheduled ingestion | GitHub Actions, every four hours |
| Android distribution | Firebase App Distribution |

The old `pressreview-458312.web.app` host permanently redirects to the production reader. Its separately scoped configuration lives in `firebase.legacy.json`.

## Repository map

- `update_articles.py`: shared asynchronous ingestion entry point.
- `summarize_fa_hardened.py`, `summarize_fp.py`: source scrapers and single-source compatibility entry points.
- `services/gemini_summary_batch.py`: structured Gemini Batch submission and reconciliation.
- `services/summary_batch_repository.py`: persistent batch ledger for Firestore or SQL/SQLite.
- `services/`: storage, normalization, sanitization, and deduplication.
- `app.py`: production Flask service, port `5000` locally.
- `main.py`: FastAPI-compatible service, port `8000` locally.
- `fpfa_app/`: Flutter web and mobile reader.
- `scripts/smoke_test_api.py`: deployed API contract check.
- `scripts/smoke_test_web.py`: responsive browser and accessibility smoke check.
- `docs/DEPLOYMENT.md`: deployment, verification, redirect, and rollback runbook.

## Public API

`GET /api/articles?limit=20` returns newest-first summaries. `limit` must be between 1 and 50. The public response intentionally excludes `article_text`; the reader only needs the title, provenance, thesis, abstract, evidence, and dates.

The service also:

- removes duplicate URLs and same-source titles while preserving the newest row;
- strips common prompt labels and Markdown wrappers from generated fields;
- skips malformed rows instead of failing the whole feed;
- allows only the production Firebase origins and explicit localhost origins in browsers;
- caches successful public responses for five minutes.

## Local backend

PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

Then open `http://localhost:5000`, or inspect:

```powershell
Invoke-RestMethod http://localhost:5000/health
Invoke-RestMethod 'http://localhost:5000/api/articles?limit=5'
```

SQLite is the local default. Override it with `ARTICLES_DB_PATH`, `FPFA_DB_PATH`, or `DATABASE_URL`.

## Ingestion

The scheduled job uses one entry point for both publications:

```powershell
$env:FPFA_GEMINI_API_KEY = 'your-key'
$env:FPFA_GEMINI_MODEL = 'gemini-3.6-flash'
python update_articles.py 7
```

Each run first reconciles earlier asynchronous jobs, then scrapes new articles and submits one Gemini Batch. Completed summaries are normally written on a later four-hour run. Prepared requests and stable hashes are persisted before any provider call, so an interrupted run can reconcile instead of paying twice.

The source-specific compatibility commands use the same batch path:

```powershell
python summarize_fa_hardened.py 1
python summarize_fp.py 1
```

SQLite is the local fallback. To target production Firestore, also set:

```powershell
$env:ARTICLE_STORE = 'firestore'
$env:FIRESTORE_PROJECT_ID = 'ppf-fpfa-summary-prod'
$env:ARTICLES_COLLECTION = 'articles'
```

`GEMINI_API_KEY` remains a compatibility fallback; new configuration should use `FPFA_GEMINI_API_KEY`.

## Flutter reader

CI uses Flutter `3.44.6`. Release builds default to the production HTTPS API. Debug builds default to Flask on `localhost:5000`, or `10.0.2.2:5000` in the Android emulator.

```powershell
Set-Location fpfa_app
flutter pub get
dart format --output=none --set-exit-if-changed lib test integration_test
flutter analyze
flutter test
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:5000
```

Production builds must use HTTPS and reject loopback endpoints:

```powershell
flutter build web --release --dart-define=API_BASE_URL=https://fpfa-summary-api-1076204999548.europe-west1.run.app
flutter build apk --release --dart-define=API_BASE_URL=https://fpfa-summary-api-1076204999548.europe-west1.run.app
```

When the network fails, a timestamped cache is shown with an explicit offline banner. The reader opens on the latest article, supports keyboard arrows, exposes real source links, and adapts from 320-pixel phones to desktop screens.

## Verification

```powershell
python -m pytest tests -q
python scripts/smoke_test_api.py --base-url https://fpfa-summary-api-1076204999548.europe-west1.run.app
python scripts/smoke_test_web.py --base-url https://ppf-fpfa-summary-prod.web.app --api-base-url https://fpfa-summary-api-1076204999548.europe-west1.run.app
```

The web smoke test requires Chromium:

```powershell
python -m playwright install chromium
```

It verifies the latest title, source link, keyboard navigation, ARIA state, console/network health, and horizontal fit at 320, 390, 768, and 1440 pixels.
