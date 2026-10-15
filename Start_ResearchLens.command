#!/bin/bash
set -e
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null; then echo 'Install Python 3.11 or newer first.'; exit 1; fi
python3 -c 'import sys; assert sys.version_info >= (3,11), "Python 3.11 or newer is required."'
if [ ! -x backend/.venv/bin/python ] || ! backend/.venv/bin/python -m pip --version >/dev/null 2>&1; then
  if [ -e backend/.venv ]; then mv backend/.venv "backend/.venv-incomplete-$(date +%s)"; fi
  python3 -m venv backend/.venv
fi
source backend/.venv/bin/activate
python -m pip install --disable-pip-version-check -r backend/requirements.txt
if [ ! -f .env ]; then cp .env.example .env; chmod 600 .env; fi
python - <<'PYSETUP'
from pathlib import Path
import secrets,os
p=Path('../.env') if not Path('.env').exists() else Path('.env')
s=p.read_text()
lines=s.splitlines()
lines=[('SESSION_SECRET='+secrets.token_urlsafe(48)) if x.strip()=='SESSION_SECRET=' else x for x in lines]
p.write_text('\n'.join(lines)+'\n');os.chmod(p,0o600)
PYSETUP
echo 'Open http://localhost:8182. Keep this Terminal open. Gemini can be configured later.'
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8182 --no-proxy-headers --no-access-log --limit-concurrency 16
