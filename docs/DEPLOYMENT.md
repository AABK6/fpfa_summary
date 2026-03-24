# Deployment And Operations

Verified against the checked-in repository on March 24, 2026.

## Deployment Matrix

### 1. Scheduled ingestion

- Workflow: `.github/workflows/update_articles.yml`
- Trigger: every 4 hours plus manual dispatch
- Runtime: GitHub Actions `ubuntu-latest`
- Purpose: scrape Foreign Affairs and Foreign Policy, summarize, write to DB
- Required secrets:
  - `GEMINI_API_KEY`
  - `DATABASE_URL_PROD` or `DATABASE_URL`

This job does not run inside Azure App Service.

### 2. Backend CI and deployment

- Workflow: `.github/workflows/master_ppfflaskapp.yml`
- Runtime for CI steps: GitHub Actions `ubuntu-latest`
- Deployment target: Azure Web App
- Default app name: `PPFFlaskApp`
- Required Azure auth material:
  - `AZUREAPPSERVICE_CLIENTID_836431FB628F4A2FACD9AC713C3A6789`
  - `AZUREAPPSERVICE_TENANTID_C226E8028E2A4E1DB2E94375D7B29B45`
  - `AZUREAPPSERVICE_SUBSCRIPTIONID_9088E3A46BFB4EA0B2375DF4A5BAEF7D`

### 3. Web frontend deployment

- Workflow: `.github/workflows/deploy_flutter_static_web_apps.yml`
- Runtime for build: GitHub Actions `ubuntu-latest`
- Deployment target: Azure Static Web Apps
- Build-time variable:
  - `API_BASE_URL_PROD` or fallback `https://ppfflaskapp.azurewebsites.net`
- Required secret:
  - `AZURE_STATIC_WEB_APPS_API_TOKEN_PROD`

### 4. Android distribution

- Workflow: `.github/workflows/deploy_android.yml`
- Runtime for build: GitHub Actions `ubuntu-latest`
- Distribution target: Firebase App Distribution
- Required secret:
  - `FIREBASE_SERVICE_ACCOUNT_KEY`
- Firebase project metadata:
  - `.firebaserc`
  - `fpfa_app/android/app/google-services.json`

This is Firebase distribution, not Firebase Hosting.

## Where To Look When Something Fails

### If `Update articles / run-scripts` fails

Check in this order:

1. GitHub Actions step logs for the failing run.
2. GitHub Actions secrets:
   - `GEMINI_API_KEY`
   - `DATABASE_URL_PROD` or `DATABASE_URL`
3. Azure SQL connectivity:
   - server reachable from public GitHub-hosted runners
   - login/user still valid
   - firewall/network rules allow external runner IPs or the chosen access model
4. Site drift on the source websites:
   - run `python scripts/live_parser_canary.py`

Usually not useful for this failure:

- Azure App Service logs, because ingestion does not run there.

### If backend deploy fails

Check:

1. GitHub Actions logs in `master_ppfflaskapp.yml`
2. Azure login secrets / OIDC configuration
3. Azure Web App deployment logs
4. Post-deploy smoke test output from `scripts/smoke_test_api.py`

### If Flutter web deploy fails

Check:

1. GitHub Actions logs in `deploy_flutter_static_web_apps.yml`
2. `API_BASE_URL_PROD`
3. Azure Static Web Apps token secret

### If Android distribution fails

Check:

1. GitHub Actions logs in `deploy_android.yml`
2. Firebase service account secret
3. Firebase App Distribution project/app ID alignment

## Current Ambiguities In The Repo

- Both `app.py` and `main.py` expose similar APIs, but they bind to different local ports:
  - Flask: `5000`
  - FastAPI: `8000`
- The Flutter app defaults to port `8000`, so local Flutter + Flask requires an explicit `API_BASE_URL`.
- Deployment workflows target Azure for web/backend and Firebase for Android distribution.
- Older design notes mention a future `fpfa` package/CLI; that package is not present in this branch.

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

### Validate ingestion locally against remote DB

```bash
export GEMINI_API_KEY=...
export DATABASE_URL=...
python summarize_fa_hardened.py 1
python summarize_fp.py 1
```

### Validate deployed API

```bash
python scripts/smoke_test_api.py --base-url https://ppfflaskapp.azurewebsites.net
```
