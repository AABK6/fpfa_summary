# Foreign Policy & Foreign Affairs Summaries

This repository contains a small Flask backend that serves article summaries from `articles.db` and a Flutter front-end (`fpfa_app`) that displays them.

## Running the backend

```bash
pip install -r requirements.txt
python app.py
```

The API will be available at `http://localhost:5000/api/articles` by default.

## CLI and pipeline

Run the unified pipeline and scrapers without starting the server:

```bash
# List latest URLs per source
python -m fpfa.cli crawl fa --limit 3
python -m fpfa.cli crawl fp --limit 3

# Run end-to-end (Foreign Affairs + Foreign Policy)
# Requires GEMINI_API_KEY unless using --stub or --dry-run
export GEMINI_API_KEY=your_key_here
python -m fpfa.cli run --sources fa,fp --limit 3

# Use stub summarizer (no LLM calls) and persist
python -m fpfa.cli run --sources fa --limit 2 --stub

# Dry run (no DB writes, stub summarizer)
python -m fpfa.cli run --sources fp --limit 2 --dry-run

# Enable detailed logs
python -m fpfa.cli run --sources fa,fp --limit 3 --verbose
# or very detailed
python -m fpfa.cli run --sources fa --limit 1 --debug
# or explicit level
python -m fpfa.cli run --sources fp --limit 2 --log-level INFO
```

Environment config:
- `FPFA_DB_PATH`: Path to the SQLite DB (defaults to `articles.db` in project root)
- `FPFA_MODEL_CORE`, `FPFA_MODEL_DETAIL`, `FPFA_MODEL_QUOTES`: Override Gemini model IDs

## Migrations

The backend now stores quotes in both the legacy `supporting_data_quotes` field and a new `quotes_json` column.
To backfill existing rows:

```bash
python -m fpfa.cli migrate quotes-json
```

## Running the Flutter app

From the `fpfa_app` directory, run `flutter run`. The app expects the backend URL specified by the `API_BASE_URL` compile-time environment variable. If none is supplied, it defaults to `http://localhost:5000` (or `http://10.0.2.2:5000` when running on the Android emulator).

Example:

```bash
flutter run -d chrome --dart-define=API_BASE_URL=http://192.168.1.100:5000
```

## Troubleshooting
If the Flutter app displays **"Failed to load articles"**, confirm the backend is reachable and that the app is using the correct API URL.

1. Start the Flask server (from this directory):
   ```bash
   pip install -r requirements.txt
   python app.py
   ```
2. Verify the endpoint returns data:
   ```bash
   curl http://localhost:5000/api/articles | head
   ```
   You should see JSON output.
3. Run the Flutter app with an explicit API URL (adjust if the server runs elsewhere):
   ```bash
   flutter run -d edge --dart-define=API_BASE_URL=http://localhost:5000
   ```
4. Ensure `articles.db` exists in the project root so the backend can read the database.

## Testing

This repo includes pytest tests for scrapers, API, and the pipeline.

```bash
pytest -q
```

Tests avoid network calls by using HTML fixtures and a stub summarizer.

Live (network) tests are available but skipped by default. To enable them:

```bash
export LIVE_TESTS=1
pytest -m live -q
```

These tests fetch real pages from Foreign Affairs and Foreign Policy to verify selectors and parsing.

### Quick commands

- Run all offline tests (no network):
  ```bash
  pytest -q
  ```
- Run only scraper unit tests (fixtures):
  ```bash
  pytest tests/test_scrapers.py -q
  ```
- Run API tests against the app factory (temp SQLite DB):
  ```bash
  pytest tests/test_api_factory.py -q
  ```
- Run pipeline integration (stub summarizer, no network):
  ```bash
  pytest tests/test_pipeline.py -q
  ```
- Run live scraper tests (real websites):
  ```bash
  export LIVE_TESTS=1
  pytest tests/test_live_scrapers.py -q
  ```
- Run live pipeline dry-run (no DB writes):
  ```bash
  export LIVE_TESTS=1
  pytest tests/test_live_pipeline.py -q
  ```
- Run live server endpoint test (requires backend running on `http://localhost:5000`):
  ```bash
  # In one terminal
  python app.py

  # In another terminal
  export LIVE_TESTS=1
  pytest tests/test_api.py -q
  ```
