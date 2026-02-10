# Open Issues Backlog (2026-02-09)

This backlog converts the remaining work from `SESSION_HANDOFF_2026-02-09.md` into trackable issues.

## Latest execution status (2026-02-10)

- ISSUE-02 (FA live ingestion): **partially validated** (URL extraction works), full summarize/insert blocked by missing `GEMINI_API_KEY` in runtime env.
- ISSUE-03 (FA Playwright fallback): **still open** due environment TLS trust failure (`ERR_CERT_AUTHORITY_INVALID`) during Playwright navigation.
- ISSUE-04 (FP live ingestion): **partially validated** (article scraping works), full summarize/insert blocked by missing `GEMINI_API_KEY` in runtime env.
- ISSUE-05 (Backend runtime smoke): **completed** in this environment (`/health`, `/api/articles`, `/` verified on Flask/FastAPI).
- ISSUE-06 (Flutter validation): **still open** (`flutter` CLI unavailable in this environment).


## Priority P0 (blockers for “fully stable”)

### [ ] ISSUE-01: Validate scheduled ingestion health in GitHub Actions

**Goal**
- Confirm `.github/workflows/update_articles.yml` is running on schedule after 2025-07-30.

**Checks**
- Inspect recent workflow runs for success/failure.
- Validate secret availability and usage (`GEMINI_API_KEY`, `MY_PAT`).
- Confirm successful `articles.db` commit + push on changed runs.

**Acceptance**
- At least one recent successful scheduled run is confirmed.
- Any failing runs have root cause identified and documented.

---

### [ ] ISSUE-02: Re-verify live Foreign Affairs ingestion (internet-enabled host)

**Goal**
- Confirm FA ingestion still works end-to-end in current site conditions.

**Run**
- `python summarize_fa_hardened.py 3`

**Checks**
- Script exits cleanly.
- New FA rows are inserted when new URLs exist.
- No infinite retries/hangs.

**Acceptance**
- Successful run log and DB verification recorded.

---

### [ ] ISSUE-03: Verify Playwright fallback path for FA scraper

**Goal**
- Confirm fallback logic works when requests path is blocked/fails.

**Checks**
- Install browser runtime if needed: `python -m playwright install --with-deps chromium`
- Run controlled test where requests path fails and fallback is used.
- Validate inserted records and clean script exit.

**Acceptance**
- Fallback usage is demonstrated and documented with outcome.

---

### [ ] ISSUE-04: Re-verify live Foreign Policy ingestion

**Goal**
- Confirm FP ingestion still works end-to-end in current site conditions.

**Run**
- `python summarize_fp.py 3`

**Checks**
- Script exits cleanly.
- New FP rows are inserted when new URLs exist.
- Summaries and metadata fields are non-empty.

**Acceptance**
- Successful run log and DB verification recorded.

## Priority P1 (high-value follow-ups)

### [x] ISSUE-05: Backend runtime smoke on non-sandbox machine

**Goal**
- Validate runtime behavior beyond unit/integration tests.

**Checks**
- Start Flask (`python app.py`) and FastAPI (`python main.py`).
- Verify `/health`, `/api/articles`, `/` responses.
- Verify HTML rendering includes recent records and static assets load.

**Acceptance**
- Both backend modes confirmed working with basic smoke output.

---

### [ ] ISSUE-06: Restore Flutter validation workflow

**Goal**
- Fix Flutter SDK permission issue and re-run static/runtime checks.

**Checks**
- Resolve lockfile permissions:
  - `/home/aabecassis/flutter/bin/cache/lockfile`
  - `/home/aabecassis/snap/flutter/common/flutter/bin/cache/lockfile`
- Run `flutter analyze`.
- Run app against local backend with `--dart-define=API_BASE_URL=...`.

**Acceptance**
- `flutter analyze` passes and app fetch path is manually verified.

## Priority P2 (cleanup/decisions)

### [ ] ISSUE-07: Decide and finalize clean working tree strategy

**Goal**
- Convert current mixed local modifications into an intentional final state.

**Checks**
- Review each modified file group (backend, workflows, Flutter, DB).
- Keep/revert each group explicitly.
- Create focused commits.

**Acceptance**
- `git status` clean after intentional commits/reverts.

---

### [ ] ISSUE-08: Decide long-term `articles.db` strategy

**Goal**
- Choose whether DB remains committed in git or moves to artifact/storage flow.

**Checks**
- Evaluate repo size/churn, merge conflict risk, and deployment needs.
- Pick one canonical strategy and document it.

**Acceptance**
- Strategy decision documented in `README.md` + workflow alignment complete.

---

### [ ] ISSUE-09: Normalize source naming conventions

**Goal**
- Ensure consistent source labels across app code/tests/data (`Foreign Affairs`/`Foreign Policy` vs `FA`/`FP`).

**Checks**
- Audit fixtures and any transform logic.
- Standardize to canonical values and update tests accordingly.

**Acceptance**
- Consistent values used across DB-facing code and tests.

---

### [x] ISSUE-10: Optional publication-date support

**Goal**
- Distinguish publication date from ingestion timestamp (`date_added`).

**Checks**
- Add schema field for publication date.
- Extract pub-date in scrapers when available.
- Update API model/UI consumption as needed.

**Acceptance**
- Publication date available end-to-end or explicitly deferred with rationale.

**Status update (2026-02-10)**
- Implemented optional `publication_date` support across scrapers, schema migration-on-start, Flask/FastAPI API outputs, and HTML date rendering fallback behavior.
