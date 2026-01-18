# Backend Audit Report

## Dependency Vulnerabilities
A `safety check` was performed on `requirements.txt` (2026-01-18). The following critical vulnerabilities were found:

### Critical / High Severity
- **flask-cors (<4.0.1, <6.0.0):** Multiple vulnerabilities including Improper Output Neutralization, Improper Handling of Case Sensitivity, and Improper Input Validation (Regex flaws).
- **werkzeug (<3.1.4):** Denial of Service (DoS) via Windows special device names.
- **urllib3 (<2.5.0, <2.6.0):** Redirect bypass and DoS vulnerabilities (decompression bombs).
- **requests (<2.32.4):** Credential leak via `.netrc` on specific URLs.
- **jinja2 (<3.1.6):** Sandbox escape via `|attr` filter.
- **flask (<3.1.1):** Session signing vulnerability (incorrect fallback key).

**Recommendation:** Immediate upgrade of all these packages to their latest secure versions is required.

## Codebase Security Analysis

### `app.py` (Flask Backend)
- **Debug Mode Enabled:** `app.run(..., debug=True)` is hardcoded. This is a significant security risk in production (RCE possible). **Fix:** Use environment variables to toggle debug mode or disable it by default.
- **CORS Configuration:** `CORS(app)` enables CORS for all routes and origins. While convenient, it should be restricted to the frontend's domain in production.
- **Database Access:** Uses `sqlite3` with parameterized queries (`LIMIT ?`). This protects against SQL injection in the `get_latest_articles` function.

### `summarize_fa.py` (Foreign Affairs Scraper)
- **Insecure Deserialization:** The script uses `pickle.load()` to read cookies from `fa_cookies.pkl`. If this file is tampered with by an attacker, it can lead to Remote Code Execution (RCE). **Fix:** Use JSON for storing cookies instead of pickle.
- **Driver Patching:** Uses `undetected_chromedriver` which patches the browser binary. This is often brittle and can introduce stability issues. The "Hardened" version (`summarize_fa_hardened.py`) using Playwright is a better alternative.

### `summarize_fp.py` (Foreign Policy Scraper)
- **Regex Sanitization:** Uses `re.sub` to remove scripts. This is generally fragile but less risky than execution.
- **Database:** Correctly uses parameterized queries.

### `summarize_fa_hardened.py`
- **Modern Alternative:** Uses Playwright, which is more robust than `undetected_chromedriver`.
- **Database:** Correctly uses parameterized queries.

## Architecture Observations
- The backend relies on standalone scripts running (presumably via cron) to populate a SQLite database.
- `articles.db` is a single point of failure and contention if write/read load increases.

# Frontend Audit Report (Flutter)

## Dependency Analysis
- **SDK Version:** `">=2.17.0 <4.0.0"` allows for a wide range of versions. It is recommended to pin this to a more recent stable version to ensure consistency.
- **Packages:** `http: ^1.1.0` and `flutter_lints: ^3.0.0` are standard.

## Code Security & Quality
- **Hardcoded Backend URLs:** The `_loadArticles` method contains hardcoded fallback URLs (`http://10.0.2.2:5000` and `http://localhost:5000`). This is a bad practice and makes the app brittle across different environments.
- **Cleartext Traffic:** The app uses `http://` which is insecure. Android and iOS modern policies default to blocking cleartext traffic, which will likely cause issues in release builds unless explicitly allowed in manifest/plist files. **Fix:** Plan to move to HTTPS or configure network security config for dev.
- **State Management:** The app relies heavily on `setState` and complex manual state tracking (e.g., `_DeckState`). This is error-prone and hard to test.
- **UI Logic Coupling:** Business logic (parsing dates, handling API errors) is tightly coupled with UI widgets.