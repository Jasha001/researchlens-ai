# Security controls and boundaries

Implemented controls:

- Gemini API key is read only by the backend. It is sent in the provider's `x-goog-api-key` header, not a URL. Provider response/error text is not reflected to users. No client key-entry API exists.
- Static server exposes only compiled frontend assets, never `.env`, backend source, SQLite state or uploaded files. API docs/schema endpoints are disabled.
- Signed, HttpOnly, SameSite=Strict sessions; Secure cookies in public mode. Requests need a per-session CSRF token and an allowed Origin. Hostnames are restricted. Public mode uses an HTTPS configured origin.
- Source permissions are HMAC-signed and bind the exact PDF page text to one browser session. Modifying text or copying a paper permission into another session is rejected. Tokens expire after 24 hours. There is no shared server paper/chat library.
- Gemini receives bounded selected paper text and a bounded question. No browsing, function calling, file fetching, arbitrary URL input, execution or model-selected tools are enabled. Prompt injection may still affect an answer's quality, but the model has no API key or system secrets in its prompt and no actions to execute.
- Source IDs are assigned by the backend; model output cannot invent citation page numbers/quotes. Exact numeric tokens, selected method names, language and counts are checked. A second model request reviews claim support. These checks do not prove semantic truth or eliminate hallucinations.
- SQLite enforces a global daily provider-call budget, per-session budget, request/upload rates and concurrency leases. Failed attempts count; requests are not retried automatically. Budgets must reside on persistent storage. Limits do not determine your Google project's billing tier.
- PDF input is checked for size/signature, pages, extracted text size and OCR-page limits. Processing runs in a child process with no API/signing/access secrets in its environment, a 45-second deadline, CPU/memory limits where supported and bounded output. No user-supplied filenames become filesystem paths.
- Docker uses a non-root user. The included Compose configuration drops Linux capabilities, enables no-new-privileges, limits memory/CPU/PIDs and makes the app filesystem read-only with a small temporary filesystem. Native PDF/OCR parsers remain an attack surface; the child process is resource isolation, not a complete sandbox or network-isolated VM. Server-level isolation and dependency updates remain necessary.
- CSP blocks inline JavaScript, framing and objects; only the optional Turnstile script/frame domain is allowed. React renders all model/PDF/user content as escaped text. Original PDFs are drawn with PDF.js rather than served as executable documents. PDF matching highlights are approximate.
- Browser storage is opt-in. PDF/text/chat are never stored in the quota database. Only pseudonymous bucket names, counts/time periods and short-lived concurrency leases are stored. Reverse-proxy/hosting access logs may still record client metadata separately.

Public mode refuses to start without: HTTPS APP_ORIGIN, SESSION_SECRET >=32 characters, and Turnstile keys or SITE_ACCESS_CODE >=12 characters. Access codes are suitable for a limited beta; Turnstile is the public visitor option. Neither makes the site bot-proof. Global caps bound provider-call consumption; bot activity can still deny service to legitimate readers.

`X-Forwarded-For` is deliberately ignored. Behind a hosting proxy, the observed proxy IP may cause visitors to share a rate bucket. Do not trust all forwarding headers to improve this; configure only your host's documented trusted proxy if changing this behavior. Signed session quotas and global budgets still apply.

Run one service instance with one persistent quota database for this starter release. Separate replicas with independent databases each get their own quota, so do not scale horizontally without shared quota enforcement.

No program can guarantee complete safety after publication. Before launch: perform live Gemini checks, test your real HTTPS domain/cookies/Turnstile, verify quota persistence through a restart, set Google API restrictions where available, keep billing disabled for a free-only project, and test hosting/resource limits. Remove confidential documents from any test workspace. See VALIDATION.md for what has and has not been verified.
