# Foreign Policy & Foreign Affairs Summaries

This repository stores summarized articles in `articles.db`, serves them through a Python backend, and displays them in the Flutter app under `fpfa_app/`.

## Canonical ingestion path

Use these scripts for article ingestion:

- `summarize_fa_hardened.py` for Foreign Affairs (requests-first, optional Playwright fallback)
- `summarize_fp.py` for Foreign Policy (requests-based)

`summarize_fa.py` is kept only as a compatibility shim and forwards to `summarize_fa_hardened.py`.

### Run ingestion manually

```bash
pip install -r requirements.txt
python summarize_fa_hardened.py 7
python summarize_fp.py 7
```

Both scripts require `GEMINI_API_KEY` for summary generation.

## Data freshness and branch sync

`articles.db` is committed to git and can differ between branches.

If your local DB looks stale:

```bash
git fetch origin
git checkout origin/master -- articles.db
```

Then check newest rows:

```bash
python - <<'PY'
import sqlite3
conn = sqlite3.connect("articles.db")
print(conn.execute("SELECT MAX(date_added) FROM articles").fetchone()[0])
conn.close()
PY
```

## Run the backend

Flask backend:

```bash
pip install -r requirements.txt
python app.py
```

FastAPI backend:

```bash
pip install -r requirements.txt
python main.py
```

Endpoints:

- Flask: `http://localhost:5000/api/articles`
- FastAPI: `http://localhost:8000/api/articles`

### Backend behavior

Canonical article ordering policy: **newest first**.

- Both Flask (`app.py`) and FastAPI (`main.py` via `services/article_service.py`) return `/api/articles`
  sorted by `date_added DESC`.
- The first item in API responses (and the first rendered card in the HTML template) is the
  most recently added article.

## Run the Flutter app

From `fpfa_app/`:

```bash
flutter run --dart-define=API_BASE_URL=http://localhost:5000
```

Default base URL behavior:

- Web/Desktop: `http://localhost:5000`
- Android emulator: `http://10.0.2.2:5000`

## Automation

The scheduled updater is `.github/workflows/update_articles.yml` and runs every 4 hours.
It executes:

- `python summarize_fa_hardened.py 7`
- `python summarize_fp.py 7`

Operational behavior:

- Fails fast if ingestion fails (no silent `continue-on-error`).
- Commits only `articles.db` when content changed.
- Triggers deployment workflow only after a successful DB update commit.

## Repository cleanup notes

Removed obsolete experimental files:

- `testvpn.py` (contained hardcoded proxy credentials and was not part of production flow)
- `test_scraping_methods.py` (manual exploratory script, not part of CI/production)

## Session handoff and open issues

Latest detailed audit/handoff:

- `SESSION_HANDOFF_2026-02-09.md`

Actionable issue tracker derived from remaining test/fix work:

- `OPEN_ISSUES_2026-02-09.md`
