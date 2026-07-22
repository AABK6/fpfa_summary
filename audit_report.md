# Security audit status

Updated July 22, 2026. This file replaces the obsolete January audit; it records the checked-in controls, not a claim that an unmerged revision is live.

## Resolved boundaries

- The public API reads a summary-only SQL/Firestore projection. It cannot load or serialize `article_text`.
- Requests are limited to 50 records, response fields have explicit size ceilings, CORS is allowlisted, and security headers are emitted by the API and Firebase Hosting.
- Publisher collection requires HTTPS, validates the publisher host and every redirect, rejects non-public DNS targets, streams bounded responses, limits HTML, paragraph, JSON-LD, node, depth, and candidate counts, and runs Playwright without `--no-sandbox`.
- Gemini receives untrusted article text separately from the system instruction. Oversized prompts, unsupported labels, invented quotations, and substantially ungrounded summaries fail closed before persistence.
- Flutter streams responses under a two-megabyte cap, validates field sizes and publisher provenance, and commits one versioned cache envelope atomically.
- Android release builds require a production keystore and reject debug signing. Gradle 8.14.4 is checksum-pinned.
- GitHub Actions use immutable commit SHAs. Web deploys the exact tested artifact; Cloud Run tests a no-traffic candidate before promotion and rolls back on a failed production smoke.
- Docker and Cloud Build contexts exclude credentials, environment files, cookies, backups, databases, mobile builds, and test output. The runtime image uses an explicit file allowlist.

## Verification

- `python -m pytest tests -q`: 82 passed.
- `pip-audit -r requirements.txt`: no known vulnerabilities.
- `flutter analyze`: no issues.
- `flutter test` plus the integration boot test: 28 unit/widget tests and one boot test passed.
- Release web and APK builds passed. The web bundle self-hosts CanvasKit; the CSP permits only the pinned Google Fonts host for Flutter's font fallback. The APK uses a 4096-bit RSA production certificate, verifies under APK signature schemes v1/v2, contains the production API URL, and contains no loopback API URL.
- The live parser canary passed.

Production is authoritative only after the GitHub deployment workflows and public API/browser smoke tests pass. A green local build is evidence, not magic.
