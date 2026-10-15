# Version 5.2 validation — 2026-10-15

30 automated tests pass across test_app.py and test_free_host.py. Existing PDF/OCR/security behavior remains tested in local mode. New free-mode tests exercise actual text-PDF extraction, scanned-PDF rejection and a 21-page PDF rejection. Other checks cover Render origin resolution, mandatory remote storage, error redaction/fail-closed behavior on database failure, TLS/SQL adapter calls (mocked), and rejection of a known missing-local-condition claim. SQLite atomicity and separate-process durability tests pass.

Production frontend build and Python compilation pass. The frontend runtime dependencies did not change from v5.1's zero-known-advisory production audit. Backend dependency audit status is recorded separately during package preparation; audits are point-in-time findings, not a security guarantee.

IMPORTANT: Actual PostgreSQL/Neon transaction execution, pooled connectivity and TLS could not be validated in this environment. Attempts to run an isolated local PostgreSQL server were blocked by environment user/process permissions. PostgreSQL adapter tests use mocks, not an actual Neon account. Use scripts/check_database.py after privately configuring the real database; it checks real concurrency limits and cross-process persistence without AI calls. Successful mock tests must not be reported as a live Postgres result.

No live Render build, Blueprint API validation, Docker/container run, 512MB-host memory test, cold start, end-to-end browser pass, new live Gemini call, penetration/load test or public deployment was performed. The owner has previously tested v5.1 live Gemini locally; that does not validate v5.2 deployment.

The current package is an implementation candidate with a documented deployment checklist, not an already-running or guaranteed-secure service. No hosting subscription, purchase or paid API upgrade has been enabled. No user secret, personal paper/chat or runtime database is in the ZIP.
