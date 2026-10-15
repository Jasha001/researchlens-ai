# Historical v5.0/v5.1 material

For v5.2 use FREE_LAUNCH.md and VALIDATION_FREE.md.

# Version 5.1: read LAUNCH_BETA.md first

Invited beta defaults now require a 16-character access code, plus explicit persistent STATE_DIR. Turnstile-only access requires explicitly disabling BETA_INVITE_ONLY and is outside the recommended launch configuration.

# Hosting the Gemini release

Nothing has been published by this package. The Mac starter binds to localhost.

## Public configuration

Use your host's server environment settings for secrets; never include them in frontend build variables. Set:

```text
AI_PROVIDER=gemini
GEMINI_API_KEY=<your server secret>
GEMINI_MODEL=<a model available in your free-tier project>
PUBLIC_MODE=true
APP_ORIGIN=https://your-real-domain.example
SESSION_SECRET=<random secret of at least 32 characters>
STATE_DIR=/data
MAX_AI_REQUESTS_PER_DAY=100
MAX_AI_REQUESTS_PER_SESSION_DAY=20
AI_SUPPORT_REVIEW=true
```

Generate a signing secret locally with `python3 -c 'import secrets; print(secrets.token_urlsafe(48))'`. Keep it stable and private. Changing it expires sessions and paper permissions.

For open public access, register your actual domain in Cloudflare Turnstile and set both `TURNSTILE_SITE_KEY` (public widget key) and `TURNSTILE_SECRET_KEY` (server secret). Server verification requires successful challenge, matching hostname and action `researchlens`. Never use test keys in production. The frontend loads the challenge only when public mode requires it.

Alternatively set `SITE_ACCESS_CODE` to a strong random code of at least 12 characters for an invited beta. Visitors must enter it; do not put it in a public URL. An access code is not individual account authentication and can be shared by recipients.

Read official setup: https://developers.cloudflare.com/turnstile/get-started/ . No third-party signup or key provisioning has been done for you.

## Container and proxy

The Dockerfile builds the frontend and installs Tesseract. Build/start with your host's normal Docker workflow, or copy `.env.example` to `.env`, configure it securely and run `docker compose up --build` on your own server.

The included Compose service binds only to `127.0.0.1:8182`. Put it behind an HTTPS reverse proxy using the exact configured APP_ORIGIN host. Use an upload body limit of 12 MB, upload timeout of 15 seconds and upstream timeout around 150 seconds; keep proxy logs free of request bodies/credentials. The app normally does two AI calls, each bounded by provider timeouts.

Create a persistent volume at `/data`, writable by container UID 10001. The service must be able to create a SQLite WAL database there. Do not expose the volume or mount it into the web root. The default Compose named volume persists quotas across restarts. Managed hosts may need volume permissions configured explicitly. The app will fail closed if quota storage cannot be used.

Keep one worker / one service replica. Global limits are shared only through this one database. Use host-level CPU/memory/PID limits equivalent to compose.yaml when your host does not use Compose. Health path: `/health`.

The process ignores proxy forwarding headers. This is conservative but may make per-IP limits shared behind a proxy. Only change proxy trust after verifying the hosting provider's routing; do not trust arbitrary forwarded IP headers.

## Launch checks still required

1. Use your own free-tier Gemini key and verify Bengali/English answers on multiple papers. Review source support and failure/429 handling. Configured status is not a live connectivity test.
2. Verify real-domain HTTPS, Secure/HttpOnly session cookies, Origin/CSRF enforcement and Turnstile success/failure.
3. Restart the service and confirm quota counts persist. Confirm there is no `.env`, source or database served publicly.
4. Verify host upload/memory/deadline limits and moderate multi-user behavior. This package has no distributed load/penetration testing.
5. Keep API billing disabled for free-only use. Server request caps do not override Google account billing. Free-tier data handling and model availability are governed by Google's current terms/pricing.

References: https://ai.google.dev/gemini-api/docs/api-key , https://ai.google.dev/gemini-api/docs/pricing , https://ai.google.dev/gemini-api/docs/rate-limits .
