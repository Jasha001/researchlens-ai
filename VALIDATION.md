# Historical v5.0/v5.1 material

For v5.2 use FREE_LAUNCH.md and VALIDATION_FREE.md.

# Historical version 5.0 report

For the current release see VALIDATION_BETA.md.

# Validation — ResearchLens v5.0.0

Validated October 7, 2026 in the execution environment.

## Completed

- **21 backend/security tests passed.** Includes upload validation and real scanned-PDF OCR; worker timeout/failure and credential-free environment; signed source tampering, cross-session and expiry rejection; Host/Origin/CSRF enforcement; body size limits including chunked requests; question bounds; public-mode startup prerequisites; access-code and Turnstile hostname/action verification; daily budget/concurrency enforcement and concurrent atomic quota consumption; Gemini header/schema/error/429 transport behavior; source/language/numeric checks; comparison and healthcare screening.
- **Real CheXNet PDF** (arXiv 1711.05225v3) processed through the app: 7 pages, year 2017, objective, 121-layer DenseNet, F1 score 0.435, actual source page ranges and a limitations paragraph continued across a figure/page boundary. No stored real user files or API keys are included in this ZIP.
- **Headless Chromium browser flow:** PDF upload; English and Bengali response rendering; paper question UI; source page viewer and matching highlights; opt-in IndexedDB paper/chat persistence through reload; healthcare screening; comparison; citation/backup downloads; desktop and 390-pixel mobile layout with no horizontal overflow; HttpOnly session and no observed JavaScript errors. **AI responses in this browser test were explicit fixtures, not live Gemini.**
- Frontend production build passed; compiled JS/CSS/PDF worker and locally bundled Bengali fonts included.
- npm production dependency audit: zero reported vulnerabilities. Python requirements pip-audit: zero reported known vulnerabilities at this check. Audits are point-in-time checks, not proof of safety.
- Mac starter/configuration scripts passed shell syntax checks on Linux.

## Not completed

- Live Gemini authentication, availability in the user's project, response accuracy or natural Bengali quality: no user key was provided. Configured status indicates configuration presence only.
- Real-domain HTTPS, Secure cookie behavior, real Turnstile challenges, reverse-proxy/hosting configuration or persistent-volume permissions.
- Container image build/Compose execution: no Docker runtime in this environment.
- macOS script execution or user-machine installation.
- Multi-instance/distributed load tests, independent penetration test, or an assessment that guarantees safety after publication.

## Remaining boundaries

Source linking, numerical checks and an automated support review can still miss a wrong claim. Users should inspect the original. Typical-column layout extraction and OCR are heuristics; uncommon layouts, figures/tables and badly scanned papers can remain incomplete. Comparison is excerpt/evidence-based, not a fully verified systematic review. Healthcare screening is based on mentions; research directions are prompts, not established novel gaps. See SECURITY.md and DEPLOYMENT.md before public launch.
