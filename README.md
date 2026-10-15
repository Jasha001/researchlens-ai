# Historical v5.0/v5.1 material

For v5.2 use FREE_LAUNCH.md and VALIDATION_FREE.md.

# Version 5.1 invited beta

Start with START_HERE.md and LAUNCH_BETA.md. This package is not deployed. Public launch instructions below from v5 are superseded by LAUNCH_BETA.md.

# ResearchLens AI 5.0 — Gemini-ready

One-server research-paper reader with PDF/OCR extraction, Bengali/simple-English explanation, paper questions, source viewer/highlights, opt-in browser library and chat history, comparison, healthcare evidence screening, BibTeX/RIS export and local feedback reports.

Begin with START_HERE.md. Gemini key is supplied later on the server; the compiled frontend is included, so ordinary local use requires Python 3.11+, not Node or Ollama.

Public-use safeguards are described in SECURITY.md. Deployment configuration is supplied, but there is no live site and no live Gemini test yet. An automated evidence check is not a guarantee of factual correctness.

Development: install backend/requirements.txt and backend/requirements-dev.txt in a development virtual environment. Run `python -m pytest backend/test_app.py -q`. Backend: `uvicorn main:app --app-dir backend --host 127.0.0.1 --port 8182 --no-proxy-headers`. For Vite development set `DEV_ORIGIN=http://localhost:5180` on the backend, then in frontend run `npm ci` and `npm run dev -- --port 5180 --strictPort`.

Do not commit/share `.env` or runtime/. Package only source, examples and compiled frontend assets.
