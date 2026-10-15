# Historical v5.0/v5.1 material

For v5.2 use FREE_LAUNCH.md and VALIDATION_FREE.md.

# Version 5.1 validation — 2026-10-15

25 backend/security tests pass. Includes invited-code enforcement (Turnstile cannot bypass), anonymous paper-token separation between independent HTTPS clients, secure cookie/headers, Origin/CSRF rejection, secret-file non-exposure, durable quota across separate processes, atomic limits, actual generated-PDF parsing/OCR, and mocked provider behavior.
Production frontend build passes. npm production dependency audit reports zero known advisories at this check. Shell scripts pass bash syntax checks; the public config script compiles.

AI responses in automated tests are mocked. The owner previously tested live Gemini 3.1 Flash-Lite English/Bengali responses locally in v5, including one unsupported-question refusal and observed wording errors. Version 5.1 prompt changes have NOT been tested against a real key; source checking is not a correctness guarantee.

No Docker daemon or Caddy executable was available for end-to-end container/proxy validation in this environment. Compose/Caddy configurations are supplied for review and real-host testing, not asserted deployed. No new interactive browser pass was run for 5.1; the prior v5 browser tests do not prove 5.1 deployment behavior. No penetration test, public load test, cloud account change, purchase, public URL or live hosting has occurred.

Before inviting users follow LAUNCH_BETA.md's actual-host checks. Quota STATE_DIR must be mounted persistently; an explicit environment variable alone cannot prove physical persistence. No raw secrets, runtime database, personal PDF or saved conversation is included in this ZIP.
