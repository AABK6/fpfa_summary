# Deployment Architecture Refactor Plan (Azure-First, Verified 2026-03-05)

This plan updates the previous proposal with current pricing and limits, while keeping implementation simple.

## 1) What Was Outdated

- The previous version assumed external Postgres (Neon/Supabase) was the main free path.
- A fully Azure option is now viable with Azure SQL Database free offer.
- Frontend hosting can stay on Azure via Static Web Apps Free instead of GitHub Pages/Firebase.

## 2) Recommended Target Architecture (Simple + Azure-First)

- Database: Azure SQL Database free offer (serverless).
- Ingestion: GitHub Actions cron writes directly to remote DB.
- Backend API: keep current Flask app on Azure App Service Free (F1) for now.
- Frontend: Azure Static Web Apps Free.

Why this is the simplest path:
- It removes DB-in-git immediately.
- It keeps your existing Azure deployment model and Flask app.
- It avoids introducing a second cloud unless needed.

## 3) Important Cost/Limit Reality Check

- App Service Free (F1) has strict limits (60 CPU minutes/day, 1 GB RAM) and no custom domain/SSL.
- Azure SQL Database free offer is free within monthly quota (100,000 vCore seconds + 32 GB per DB, up to 10 databases).
- Azure Static Web Apps Free includes 100 GB bandwidth/month and free SSL/custom domain support.

Interpretation:
- If traffic remains low, this can stay at $0.
- If API traffic grows, App Service F1 is the first likely bottleneck.

## 4) Step-by-Step Refactor Plan

### Phase 1: Stop Git-Driven DB Deploys (immediate)

Update `.github/workflows/update_articles.yml`:
- Keep scraping/summarization steps.
- Remove `git add/commit/push` for `articles.db`.
- Remove workflow dispatch that triggers backend deployment.
- Pass DB connection via secret env var (`DATABASE_URL`).

Result: ingestion no longer redeploys backend every 4 hours.

### Phase 2: Add DB Driver Layer (keep SQLite fallback)

Refactor DB access in `app.py`, `summarize_fp.py`, and `summarize_fa_hardened.py`:
- If `DATABASE_URL` is set, use remote SQL DB.
- Else use local `articles.db` for local dev.

Practical simplification:
- Use SQLAlchemy Core for cross-DB compatibility (SQLite local + Azure SQL remote).
- Keep current schema and API response shape unchanged.

### Phase 3: Move to Azure SQL Database Free Offer

1. Create Azure SQL free database.
2. Store connection string in:
- GitHub Actions secret: `DATABASE_URL`
- Azure App Service app setting: `DATABASE_URL`
3. Run one-time migration from local SQLite to Azure SQL.

### Phase 4: Slim Backend Deployment Workflow

Update `.github/workflows/master_ppfflaskapp.yml`:
- Trigger only on backend paths.
- Zip only backend runtime files (exclude Flutter app/tests/dev artifacts).
- Keep tests in CI before deploy.

### Phase 5: Add Frontend CD on Azure Static Web Apps

Create a dedicated workflow for Flutter Web deployment to Azure Static Web Apps Free:
- Trigger on `fpfa_app/**`.
- Build with `flutter build web --dart-define=API_BASE_URL=<api-url>`.
- Deploy build output to Static Web Apps.

## 5) If Free Azure Limits Are Exceeded

### First upgrade point
- Move API off App Service F1 to either:
- App Service Basic
- Azure Container Apps (can remain low-cost with free grant depending on usage)

### If Azure SQL free quota is not enough
- Scale Azure SQL to paid tier, or
- Use external free Postgres (Neon/Supabase) as a complement.

## 6) External Complement Option (Only If Needed)

If you require PostgreSQL specifically and want perpetual free immediately:
- Keep Azure frontend/API.
- Use Neon free Postgres (serverless).

Note:
- Azure Database for PostgreSQL free entitlement is typically tied to Azure free account period (not perpetual).

## 7) Source Links (Checked 2026-03-05)

- Azure SQL Database free offer:
  - https://learn.microsoft.com/en-us/azure/azure-sql/database/free-offer?view=azuresql
- Azure Static Web Apps pricing:
  - https://azure.microsoft.com/en-us/pricing/details/app-service/static/
- Azure App Service pricing:
  - https://azure.microsoft.com/en-us/pricing/details/app-service/windows/
- Azure Functions pricing:
  - https://azure.microsoft.com/en-us/pricing/details/functions/
- Azure Functions Linux Consumption retirement notice:
  - https://learn.microsoft.com/en-us/azure/azure-functions/functions-scale
- Azure free services catalog:
  - https://azure.microsoft.com/free/free-services
- Neon pricing:
  - https://neon.tech/pricing
