# Data handling

Uploaded PDFs are read in memory and passed to a temporary processing subprocess. The app does not create a shared server PDF/paper/chat library or write uploads to permanent disk. Native parsing/OCR and the hosting platform may use temporary files, crash handling or access logs; configure host-level retention accordingly.

Selected extracted passages and the current question (plus the prior question for follow-up context) are sent to the configured AI provider. Gemini free-tier content may be used by Google to improve its products under the applicable terms; do not submit patient records, unpublished confidential data or documents you lack permission to send. Model answers are educational research assistance, not clinical advice.

Browser saving is opt-in and may store original PDFs, extracted text and chat in IndexedDB on the device. Turning saving off clears the stored workspace while retaining the current in-memory view. Delete local workspace removes it and clears the visible papers/history. Browser backups contain paper text/chat but no API key, session cookie or reusable server permission; treat backups as private documents.

Sessions are anonymous signed cookies and expire after 24 hours. The quota database stores pseudonymous rate/budget bucket names, counts/time periods and transient concurrency leases. IP-derived bucket names are HMAC-hashed; raw client addresses are not stored by app quota logic. Hosting logs and optional Cloudflare Turnstile have separate policies. Feedback is a downloadable local report with no remote inbox.

The server operator supplies Gemini/Turnstile keys, domains, retention controls and privacy notice/contact information for any live service. No live deployment or third-party account setup was performed by this release.
