# Deployment Architecture Refactor Plan (Zero-Cost / Free Tier Focus)

This document outlines a detailed refactor plan to stabilize the deployment pipeline, decouple the database from version control, and establish a frontend deployment strategy—all while maintaining a **$0/month** operational cost.

## 1. Architecture Overview

### Current Architecture (Problematic)
- **Data:** `articles.db` (SQLite) is committed directly to the GitHub repository every 4 hours.
- **Backend:** Azure Web App redeploys entirely every 4 hours due to the DB commit, pulling the entire repo (including the Flutter app).
- **Frontend:** No continuous deployment.

### Proposed Architecture (Free & Scalable)
- **Database:** **Neon** or **Supabase** (Free Tier Serverless PostgreSQL).
- **Data Ingestion:** GitHub Actions (Cron) runs the scraper and writes directly to the remote Postgres database.
- **Backend (Flask API):** Azure Web App (Free Tier). Only redeploys when backend *code* changes. Deployment payload is minimized.
- **Frontend (Flutter Web):** GitHub Pages or Firebase Hosting (Free Tier). Deploys automatically when Flutter code changes.

---

## 2. Step-by-Step Refactor Plan

### Phase 1: Database Migration (SQLite -> Free PostgreSQL)
To stop committing binary files to Git, we will move the database to a free cloud Postgres provider. **Neon.tech** or **Supabase** are highly recommended as they offer generous free tiers specifically designed for serverless/hobby projects.

1. **Provision the Database:**
   - Create a free account on [Neon](https://neon.tech/) or [Supabase](https://supabase.com/).
   - Create a new project and copy the `DATABASE_URL` connection string.

2. **Update Application Code:**
   - Add `psycopg2-binary` to `requirements.txt` to support Postgres connections.
   - Modify the database connection logic in the Flask app and scrapers to use the `DATABASE_URL` environment variable.
   - *Fallback:* If `DATABASE_URL` is not set, default back to local SQLite (`articles.db`) so local development remains seamless.

3. **Cleanup Git:**
   - Add `articles.db` to `.gitignore`.
   - Run `git rm --cached articles.db` to remove it from version control tracking.

---

### Phase 2: Decouple Data Ingestion from Deployments
Currently, the scraper cron job triggers a full backend deployment. We will change this so it only updates the remote database.

1. **Update `.github/workflows/update_articles.yml`:**
   - Add the `DATABASE_URL` to your GitHub Repository Secrets.
   - Expose the `DATABASE_URL` to the Python scraper step as an environment variable.
   - **Remove** the Git commit, Git push, and "Dispatch deployment workflow" steps completely. The action should just run the Python scripts and succeed.

---

### Phase 3: Optimize Backend Deployments (Azure Web App)
The backend should only deploy when API code changes, and it shouldn't waste time packaging the Flutter app.

1. **Update `.github/workflows/master_ppfflaskapp.yml`:**
   - **Fix the Trigger:** Change the `on: push` block to only trigger on backend changes:
     ```yaml
     on:
       push:
         branches:
           - master
         paths:
           - 'app.py'
           - 'main.py'
           - 'models/**'
           - 'services/**'
           - 'requirements.txt'
     ```
   - **Shrink the Zip Payload:** Modify the zipping command to exclude the Flutter app and test files. Instead of `zip release.zip ./* -r`, use:
     ```yaml
     - name: Zip artifact for deployment
       run: zip release.zip app.py main.py requirements.txt models/ services/ static/ templates/ -r
     ```
   - **Set Environment Variables:** Ensure your Azure Web App is configured with the new `DATABASE_URL` and `GEMINI_API_KEY` environment variables in the Azure Portal configuration settings.

---

### Phase 4: Establish Frontend CD (Flutter to GitHub Pages)
Since GitHub Pages is completely free and natively integrated, it's the perfect place to host the Flutter Web build.

1. **Create `.github/workflows/deploy_flutter_web.yml`:**
   - Create a new workflow to build and deploy the Flutter app:

   ```yaml
   name: Deploy Flutter Web to GitHub Pages

   on:
     push:
       branches:
         - master
       paths:
         - 'fpfa_app/**'

   jobs:
     build-and-deploy:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v4
         
         - name: Set up Flutter
           uses: subosito/flutter-action@v2
           with:
             flutter-version: '3.x'
             channel: 'stable'
             
         - name: Install dependencies
           run: flutter pub get
           working-directory: fpfa_app

         - name: Build Web
           # Replace the URL with your actual Azure Web App URL
           run: flutter build web --dart-define=API_BASE_URL=https://ppfflaskapp.azurewebsites.net
           working-directory: fpfa_app

         - name: Deploy to GitHub Pages
           uses: peaceiris/actions-gh-pages@v3
           with:
             github_token: ${{ secrets.GITHUB_TOKEN }}
             publish_dir: ./fpfa_app/build/web
   ```
2. **Enable GitHub Pages:**
   - Go to your repository settings on GitHub.
   - Under "Pages", set the source to `GitHub Actions`.

---

## Summary of Benefits
* **Cost:** $0/month.
* **Performance:** Azure app no longer goes down every 4 hours for unnecessary redeployments.
* **Storage:** Git repository stops bloating from binary `.db` files.
* **Deployments:** Backend deployments are tiny and fast. Frontend deployments are automated and completely free.
