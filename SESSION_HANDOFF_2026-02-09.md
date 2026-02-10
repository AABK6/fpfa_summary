# FPFA Repo Handoff (2026-02-09)

This document captures what was verified, what was uncovered, and what still needs testing/fixes before considering the repo fully clean and production-stable.

## 1) Scope covered in this pass

- Scraper pipeline review (`summarize_fa_hardened.py`, `summarize_fp.py`, workflows, tests)
- DB state inspection (`articles.db`)
- Backend test/runtime checks (Flask + FastAPI test suite)
- Flutter static check attempt
- Repo cleanliness/status review

## 2) Verified current state

### Automated tests

- Backend tests pass:
  - Command: `.venv/bin/python3.11 -m pytest tests -q`
  - Result: `16 passed in 1.37s`

### Database snapshot (local working copy)

Snapshot time: 2026-02-09.

- Total rows: `2880`
- By source:
  - `Foreign Affairs`: `499`
  - `Foreign Policy`: `2381`
- Ingestion timestamp range (`date_added`): `2025-03-01 03:18:17` → `2026-02-09 20:35:25`
- Latest `Foreign Affairs` ingestion timestamp: `2026-02-09 05:25:53`
- Latest `Foreign Policy` ingestion timestamp: `2026-02-09 20:35:25`

Important: the schema stores `date_added` (ingestion time), not article publication date. “Last articles” in DB means most recently ingested entries.

### Last 10 Foreign Affairs rows in DB (by `date_added` DESC)

1. `2026-02-09 05:25:53` — *Beijing’s Growth Model Is Still Broken*
2. `2026-02-09 05:25:38` — *Europe Needs an Army*
3. `2026-02-06 08:35:28` — *Europe’s Next Hegemon*
4. `2026-02-06 08:35:12` — *The Real Risks of the Saudi-UAE Feud*
5. `2026-02-05 08:37:04` — *The Limits of Russian Power*
6. `2026-02-05 08:36:48` — *Strength Over Peace*
7. `2026-02-04 08:35:26` — *Trouble Is Brewing in Syria*
8. `2026-02-04 08:35:02` — *The Free World Needs Taiwan*
9. `2026-02-04 08:34:43` — *There Is Only One Sphere of Influence*
10. `2026-02-03 08:31:28` — *The Paradox of Wartime Commerce*

## 3) Key findings uncovered

### A) Why it looked “stopped in July 2025”

- Git history for committed `articles.db` updates on this branch stops at `2025-07-30`.
- Local `articles.db` currently contains entries through `2026-02-09`.
- Conclusion: local/manual ingestion has newer data, but committed branch history did not continue after July 2025 (likely workflow/push/secret/scheduler issue on GitHub side).

### B) Scraper architecture status

- `summarize_fa.py` is now a deprecation compatibility shim forwarding to `summarize_fa_hardened.py`.
- Canonical FA path is `summarize_fa_hardened.py`:
  - Requests-first
  - Optional Playwright fallback
  - Bounded retries
- Legacy Selenium/undetected-chromedriver dependencies were removed from `requirements.txt`.
- Removed obsolete exploratory scripts:
  - `testvpn.py`
  - `test_scraping_methods.py`

### C) CI/workflow normalization status

- `.github/workflows/update_articles.yml` now:
  - Uses modern action versions
  - Runs fail-fast ingestion
  - Commits only `articles.db` when changed
  - Pushes/dispatches deployment only if DB changed
- `.github/workflows/master_ppfflaskapp.yml` now runs `pytest` over `tests/` instead of a manual subset.

### D) Runtime/tooling constraints discovered in this environment

- Outbound DNS/network is blocked in this sandbox (requests to external domains fail resolution), so live scraping against real FA/FP sites cannot be re-validated here.
- Local server bind attempts via `uvicorn` failed in sandbox (`could not bind on any address`), so full HTTP smoke via local port could not be confirmed in this environment.
- `flutter analyze` currently fails due Flutter SDK cache lockfile permission issue:
  - `/home/aabecassis/flutter/bin/cache/lockfile`
  - `/home/aabecassis/snap/flutter/common/flutter/bin/cache/lockfile`

## 4) What remains to test (priority order)

### P0 (must verify before declaring “perfectly stable”)

1. **GitHub scheduled ingestion health**
   - Check `update_articles.yml` runs after 2025-07-30.
   - Confirm failures (if any), especially around secrets (`GEMINI_API_KEY`, `MY_PAT`) and push permissions.
2. **Live end-to-end FA scrape (internet-enabled environment)**
   - Run `python summarize_fa_hardened.py 3`.
   - Confirm new FA rows are inserted.
   - Confirm requests path succeeds when possible.
3. **Playwright fallback verification**
   - In a scenario where requests path fails/blocked, ensure fallback inserts rows and exits cleanly.
4. **Live end-to-end FP scrape**
   - Run `python summarize_fp.py 3` and verify inserts and content quality.

### P1 (high value, next)

5. **Backend runtime smoke in non-sandbox host**
   - Start Flask and FastAPI processes.
   - Verify `/health`, `/api/articles`, and `/` render correctly.
6. **Flutter static + runtime verification**
   - Fix SDK lockfile permissions and rerun `flutter analyze`.
   - Run app against local backend and verify deck/error/empty states manually.

## 5) What remains to fix/decide

1. **Repo cleanliness decision**
   - Many files remain modified in working tree.
   - Decide final keep/revert set, then commit intentionally.
2. **DB freshness strategy**
   - Decide whether `articles.db` should continue being committed, or move to artifact/storage-based pipeline.
3. **Source naming consistency**
   - Normalize source values (`Foreign Affairs`/`Foreign Policy` vs `FA`/`FP` in some tests/data fixtures) if needed.
4. **Optional data model improvement**
   - If needed for product UX, add publication date column and parser extraction; `date_added` is currently ingestion-time only.

## 6) Quick reproducibility commands

### DB sanity checks

```bash
python3 - <<'PY'
import sqlite3
conn = sqlite3.connect("articles.db")
cur = conn.cursor()
print(cur.execute("SELECT COUNT(*) FROM articles").fetchone()[0])
print(cur.execute("SELECT source, COUNT(*) FROM articles GROUP BY source ORDER BY source").fetchall())
print(cur.execute("SELECT MIN(date_added), MAX(date_added) FROM articles").fetchone())
print(cur.execute("SELECT id, title, date_added FROM articles WHERE source='Foreign Affairs' ORDER BY datetime(date_added) DESC LIMIT 10").fetchall())
conn.close()
PY
```

### Test suite

```bash
.venv/bin/python3.11 -m pytest tests -q
```

### Manual ingestion (internet + Gemini key required)

```bash
export GEMINI_API_KEY=...
python summarize_fa_hardened.py 7
python summarize_fp.py 7
```

---

## Addendum (2026-02-10 follow-up execution)

A follow-up execution pass was run to advance outstanding items.

### Completed in this pass

- Backend runtime smoke succeeded for both servers:
  - Flask: `/health`, `/api/articles`
  - FastAPI: `/health`, `/api/articles`, `/`
- Test suite still passing:
  - `pytest tests -q` → `29 passed`

### Still blocked / partial

- `python summarize_fa_hardened.py 3` still exits immediately when `GEMINI_API_KEY` is missing.
- `python summarize_fp.py 3` still scrapes live URLs/content but cannot summarize/insert without `GEMINI_API_KEY`.
- Playwright fallback path for FA could not be fully validated because browser navigation in this environment returns `ERR_CERT_AUTHORITY_INVALID` for Foreign Affairs HTTPS pages.
- Flutter checks remain blocked because `flutter` CLI is unavailable in this environment.

### Net status impact

- P1 backend runtime smoke is now verified.
- P0 ingestion items remain open until a runtime with valid Gemini key + stable TLS trust is used for full end-to-end summarize/insert verification.
