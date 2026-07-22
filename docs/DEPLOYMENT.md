# Deployment and operations

Runbook updated on July 22, 2026. It describes the checked-in target; it does not claim that unmerged changes are live.

## Production targets

| Component | Target |
| --- | --- |
| Web reader | `https://ppf-fpfa-summary-prod.web.app` |
| Public API | `https://fpfa-summary-api-1076204999548.europe-west1.run.app` |
| Article store | `firestore://ppf-fpfa-summary-prod/articles` |
| Ingestion | GitHub Actions every four hours |
| Android | Firebase App Distribution |

## Deployment order

1. Backend: `.github/workflows/master_ppfflaskapp.yml`
2. Web reader: `.github/workflows/deploy_flutter_static_web_apps.yml`
3. Android: `.github/workflows/deploy_android.yml`
4. Scheduled ingestion: `.github/workflows/update_articles.yml`
5. Legacy redirect: manual, after production verification

The backend goes first because the public contract removes `article_text`, enforces `limit`, deduplicates summaries, and narrows CORS. The Flutter client accepts the old payload during the transition.

## Required GitHub configuration

Repository variables:

- `GCP_PROJECT_ID` — defaults to `ppf-fpfa-summary-prod`
- `GCP_REGION` — defaults to `europe-west1`
- `GCP_BACKEND_SERVICE` — defaults to `fpfa-summary-api`
- `GCP_ARTIFACT_REPOSITORY` — defaults to `fpfa`
- `ARTICLES_COLLECTION` — defaults to `articles`
- `API_BASE_URL_PROD` — production Cloud Run URL
- `WEB_BASE_URL_PROD` — production Firebase Hosting URL
- `FIREBASE_ANDROID_APP_ID` — production Android app
- `GCP_WORKLOAD_IDENTITY_PROVIDER`
- `GCP_DEPLOYER_SERVICE_ACCOUNT`
- `GCP_RUNTIME_SERVICE_ACCOUNT`
- `GCP_FIREBASE_SERVICE_ACCOUNT`
- `GCP_INGEST_SERVICE_ACCOUNT`

Secrets:

- `GEMINI_API_KEY` — exposed to ingestion as `FPFA_GEMINI_API_KEY`
- `ANDROID_KEYSTORE_BASE64` — base64-encoded production keystore
- `ANDROID_KEYSTORE_PASSWORD` — keystore password
- `ANDROID_KEY_ALIAS` — production signing alias
- `ANDROID_KEY_PASSWORD` — signing-key password

Deployments use Workload Identity Federation. Long-lived service-account JSON is not part of the active workflows.
Keep an encrypted, off-repository backup of the Android keystore and its password. Losing either prevents future updates signed as the same application.

## Backend gate

The workflow installs the pinned dependencies, runs every Python test, compiles the sources, runs the live parser canary, and builds one uniquely tagged image. It deploys that image as a tagged revision with no traffic, smokes the candidate URL, promotes it to 100%, and smokes the canonical production URL. A failed post-promotion smoke routes traffic back to the prior revision.

The smoke test checks health, CORS, limits, ordering, deduplication, required fields, payload size, and exclusion of `article_text`.

```powershell
python scripts/smoke_test_api.py --base-url https://fpfa-summary-api-1076204999548.europe-west1.run.app
```

## Web gate

The workflow pins Flutter `3.44.6` and Firebase CLI `15.24.0`. It enforces formatting, analysis, tests, and a release build with local CanvasKit, then uploads that exact tested bundle. The deployment job downloads the artifact instead of rebuilding after authentication and waits for the bounded, body-free production API contract before publishing. After deployment, Playwright checks 320, 390, 768, and 1440 pixel viewports and preserves screenshots for 14 days.

```powershell
Set-Location fpfa_app
flutter pub get
dart format --output=none --set-exit-if-changed lib test integration_test
flutter analyze
flutter test
flutter build web --release --no-web-resources-cdn --dart-define=API_BASE_URL=https://fpfa-summary-api-1076204999548.europe-west1.run.app
Set-Location ..
firebase deploy --project ppf-fpfa-summary-prod --only hosting --non-interactive
python scripts/smoke_test_web.py --base-url https://ppf-fpfa-summary-prod.web.app --api-base-url https://fpfa-summary-api-1076204999548.europe-west1.run.app
```

A successful upload is not publication proof. The browser smoke result is.

## Android gate

The Android workflow applies the same format, analysis, and test gates. It fails closed unless all four production-signing secrets exist, builds with the production API define, scans all compiled `libapp.so` files for the production endpoint and forbidden loopback URLs, verifies the APK signature is not the Android debug certificate, archives that APK, waits for the bounded, body-free production API contract, then distributes the same file.

The release manifest disables cleartext traffic. The debug manifest permits it for local Flask development.

## Ingestion gate

The scheduled workflow uses a dedicated ingestion identity and prevents overlapping runs. Each run:

1. reconciles prepared or running Gemini batches;
2. writes completed results to the article store;
3. scrapes eligible articles from both sources;
4. persists stable request hashes before networking;
5. submits one structured Gemini Batch.

The default model is `gemini-3.6-flash`. A prepared ledger entry is not a completed summary, and a scheduled workflow marked successful may still leave a provider batch pending for the next run.

```powershell
$env:FPFA_GEMINI_API_KEY = '...'
$env:FPFA_GEMINI_MODEL = 'gemini-3.6-flash'
$env:ARTICLE_STORE = 'firestore'
$env:FIRESTORE_PROJECT_ID = 'ppf-fpfa-summary-prod'
$env:ARTICLES_COLLECTION = 'articles'
python update_articles.py 1
```

When a source layout changes, run `python scripts/live_parser_canary.py`. A healthy metadata path does not prove full-text extraction; inspect each source result.

## Legacy host retirement

`firebase.legacy.json` contains a permanent redirect from the retired project. Deploy it only after both production smoke tests pass:

```powershell
firebase deploy --project pressreview-458312 --config firebase.legacy.json --only hosting:pressreview-458312 --non-interactive
```

Then verify both `/` and an arbitrary deep path redirect permanently to `https://ppf-fpfa-summary-prod.web.app`. This production-changing command is intentionally absent from automation.

## Failure and rollback

- Backend failure before deployment: production is unchanged.
- Backend smoke failure after deployment: route Cloud Run traffic to the last known-good revision.
- Web smoke failure: restore the last known-good Firebase Hosting release and retain the screenshots.
- Android verification failure: do not distribute the APK.
- Ingestion failure: inspect the stored batch ledger before rerunning; blind retries can duplicate provider cost.

Record the workflow run, deployed revision or Hosting release, smoke result, public URL, and rollback point. A green build alone proves very little.
