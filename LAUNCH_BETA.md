# Historical v5.0/v5.1 material

For v5.2 use FREE_LAUNCH.md and VALIDATION_FREE.md.

# ResearchLens AI 5.1 — invited public beta

This is a deployment candidate, not a live website or a guarantee of security. The local Mac app still works. No cloud plan, domain, billing or deployment is created by this ZIP.

## Prepared behavior
- Public visitors enter an owner-held access code (16+ characters); Turnstile alone cannot enter the default invited beta.
- Gemini key stays on the server; default model is gemini-3.1-flash-lite, used successfully in the owner's local v5 tests. Availability/quota must still be checked in the actual deployment.
- Anonymous session-bound paper tokens, CSRF, strict origins, Secure HttpOnly cookies, upload bounds, isolated resource-limited parser child and durable SQLite request budgets remain enabled.
- Global limit defaults to 100 provider calls/day. Most answers make two calls, so this is approximately 50 complete answers, not 100 users. Failed calls also count; there is no automatic paid fallback. A user can create new anonymous sessions: session limits are not per-person limits. The global cap remains the cost boundary.
- The public UI explicitly says Beta. Instructions/review now preserve local/global scope and distinguish black-box predictors from explainers. This reduces a known failure mode, but cannot guarantee truthful output.

## Option A: managed Docker host
Use Dockerfile. One replica, one worker, at least 2GB RAM initially. Mount persistent storage at /data writable by UID 10001. Never use ephemeral storage for limits. Supply server environment (no VITE_ secrets):
PUBLIC_MODE=true, BETA_INVITE_ONLY=true, APP_ORIGIN=https://the-real-host,
STATE_DIR=/data, SESSION_SECRET=(48+ random characters), SITE_ACCESS_CODE=(16+ random characters),
GEMINI_API_KEY=(private key), GEMINI_MODEL=gemini-3.1-flash-lite,
MAX_AI_REQUESTS_PER_DAY=100, MAX_AI_REQUESTS_PER_SESSION_DAY=20, AI_SUPPORT_REVIEW=true,
PRIVACY_CONTACT=(your public contact email).
The host sets PORT if required. Health endpoint is /health, with the real hostname in Host. Match APP_ORIGIN exactly; no trailing path. The app rejects hostnames not configured in APP_ORIGIN. Keep HTTPS termination enabled. Costs require owner review before creating a paid service.

## Option B: your own Linux server + HTTPS proxy
Requires Docker Engine, Compose >=2.30, a domain pointed at the server, free ports 80/443 and sufficient RAM. This route is supplied for review, not executed.
1. Run `python3 scripts/configure_public.py` locally. It privately creates .env.public; enter your domain/contact/key/code without posting secrets in chat. It does not replace local .env.
2. Transfer the source plus private .env.public securely to your server. Restrict its permissions to the operator. Never put it in GitHub.
3. Run `docker compose --env-file .env.public -f compose.public.yaml config --quiet` (do not print the expanded configuration: it contains secrets).
4. Run `docker compose --env-file .env.public -f compose.public.yaml up --build -d`.
5. Caddy obtains HTTPS certificates for the configured hostname. Only the proxy is internet-facing; the backend has no published host port. Persistent named volumes hold quotas/certificates. Caddy receives no AI/session/access secrets.
6. Stop public access with the same Compose invocation followed by `down`; do not use `down -v` unless intentionally deleting quota/certificate state.

## Required checks on the real host before inviting anyone
- HTTPS redirect, certificate and exact-origin login; wrong code blocked; valid code succeeds; secure cookie flags present.
- Two independent browsers: a paper token from A rejected by B, and no shared paper/chat list.
- English/Bengali questions on multiple public papers; unsupported questions refused; local/nonlinear caveats preserved; quotes/page links manually checked.
- 429 behavior and counters retained across process/container restarts, including errors. One replica only.
- Public requests to /.env, /.env.public, /backend/config.py and /data/limits.sqlite3 return no files.
- Test malformed/oversized PDFs and small concurrent load. Native parser isolation is not a full malware sandbox; no penetration test has been completed.
- Confirm Google's current terms/free quota; request caps are not dollar billing caps. Leave paid billing disabled if free-only operation is required.
- Publish an actual contact email and review privacy wording for the host. App does not intentionally save server PDFs/chats, but host logs/temp files have separate retention.

Known proxy limitation: forwarded IP headers are intentionally ignored. Behind one proxy, IP limits may be shared by all visitors (conservative throttling). Avoid changing trust blindly. Sharing an access code is not individual identity or access revocation; rotate it and SESSION_SECRET to invalidate all sessions if needed.

## Research scope
The public assistant is a portfolio/demo product. ESP keyword-versus-semantic retrieval evaluation and the independent XAI paper remain separate; no research result is claimed by this release.

References checked 2026-10-15:
https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite
https://ai.google.dev/gemini-api/docs/pricing
https://caddyserver.com/docs/quick-starts/https
https://caddyserver.com/docs/caddyfile/directives/reverse_proxy
