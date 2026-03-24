# Deployment And Operations

Verified against the checked-in repository on March 24, 2026.

## Deployment Matrix

### 1. Scheduled ingestion

- Workflow: `.github/workflows/update_articles.yml`
- Trigger: every 4 hours plus manual dispatch
- Runtime: GitHub Actions `ubuntu-latest`
- Purpose: scrape Foreign Affairs and Foreign Policy, summarize, write into Firestore
- Required secrets:
  - `GEMINI_API_KEY`
  - `FIREBASE_SERVICE_ACCOUNT_KEY`
- Required vars:
  - `GCP_PROJECT_ID` (default: `pressreview-458312`)
  - `ARTICLES_COLLECTION` (default: `articles`)

This job no longer depends on Azure SQL.

### 2. Backend CI and deployment

- Workflow: `.github/workflows/master_ppfflaskapp.yml`
- Runtime for CI steps: GitHub Actions `ubuntu-latest`
- Deployment target: Cloud Run
- Default service name: `fpfa-summary-api`
- Default region: `europe-west1`
- Required secret:
  - `FIREBASE_SERVICE_ACCOUNT_KEY`
- Optional vars:
  - `GCP_PROJECT_ID`
  - `GCP_REGION`
  - `GCP_BACKEND_SERVICE`
  - `GCP_ARTIFACT_REPOSITORY`
  - `ARTICLES_COLLECTION`

Runtime env pushed into Cloud Run:

- `ARTICLE_STORE=firestore`
- `FIRESTORE_PROJECT_ID=<project>`
- `ARTICLES_COLLECTION=<collection>`

### 3. Web frontend deployment

- Workflow: `.github/workflows/deploy_flutter_static_web_apps.yml`
- Runtime for build: GitHub Actions `ubuntu-latest`
- Deployment target: Firebase Hosting
- Build-time variable:
  - `API_BASE_URL_PROD` or fallback `https://fpfa-summary-api-1028212947283.europe-west1.run.app`
- Required secret:
  - `FIREBASE_SERVICE_ACCOUNT_KEY`
- Config files:
  - `.firebaserc`
  - `firebase.json`

### 4. Android distribution

- Workflow: `.github/workflows/deploy_android.yml`
- Runtime for build: GitHub Actions `ubuntu-latest`
- Distribution target: Firebase App Distribution
- Required secret:
  - `FIREBASE_SERVICE_ACCOUNT_KEY`

## Lowest-Cost Rationale

This repo is intentionally avoiding the expensive defaults:

- No Cloud SQL: Firestore is the default production store to avoid a constant database bill.
- No always-on VM: Cloud Run scales to zero for the API.
- No dedicated frontend server: Flutter web is served from Firebase Hosting.
- No extra scheduler service yet: ingestion stays on GitHub Actions, which is cheaper than standing up more GCP runtime just to run scraping every 4 hours.

## Required GCP Services

The project should have these enabled:

- Cloud Run API
- Cloud Build API
- Artifact Registry API
- Firestore API
- Firebase Hosting

The Firestore database already needs to exist in Native mode.

## Where To Look When Something Fails

### If `Update articles / run-scripts` fails

Check in this order:

1. GitHub Actions step logs for the failing run
2. GitHub secrets:
   - `GEMINI_API_KEY`
   - `FIREBASE_SERVICE_ACCOUNT_KEY`
3. Firestore access:
   - service account permissions
   - target project ID / collection name
4. Source-site drift:
   - run `python scripts/live_parser_canary.py`

### If backend deploy fails

Check:

1. GitHub Actions logs in `master_ppfflaskapp.yml`
2. GCP auth using `FIREBASE_SERVICE_ACCOUNT_KEY`
3. Artifact Registry repository existence / permissions
4. Cloud Run deploy output
5. Post-deploy smoke test output from `scripts/smoke_test_api.py`

### If Flutter web deploy fails

Check:

1. GitHub Actions logs in `deploy_flutter_static_web_apps.yml`
2. `API_BASE_URL_PROD`
3. Firebase Hosting deploy output
4. `firebase.json` rewrite config

### If Android distribution fails

Check:

1. GitHub Actions logs in `deploy_android.yml`
2. Firebase service account secret
3. Firebase App Distribution project/app ID alignment

## Runtime Storage Modes

### Production

Set:

```bash
export ARTICLE_STORE=firestore
export FIRESTORE_PROJECT_ID=pressreview-458312
export ARTICLES_COLLECTION=articles
```

### Local SQLite

Unset Firestore env and run locally:

```bash
unset ARTICLE_STORE
unset FIRESTORE_PROJECT_ID
python app.py
```

### Legacy SQL mode

The storage layer still understands `DATABASE_URL` for SQLite / SQLAlchemy URLs, but GCP production is no longer expected to use Azure SQL.

## Practical Checks

### Validate backend locally with Flask

```bash
python app.py
curl http://localhost:5000/health
curl http://localhost:5000/api/articles
```

### Validate backend locally with FastAPI

```bash
python main.py
curl http://localhost:8000/health
curl http://localhost:8000/api/articles
```

### Validate ingestion against Firestore

```bash
export GEMINI_API_KEY=...
export ARTICLE_STORE=firestore
export FIRESTORE_PROJECT_ID=pressreview-458312
python summarize_fa_hardened.py 1
python summarize_fp.py 1
```

### Validate deployed API

```bash
python scripts/smoke_test_api.py --base-url https://fpfa-summary-api-1028212947283.europe-west1.run.app
```
