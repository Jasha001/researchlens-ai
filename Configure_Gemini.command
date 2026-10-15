#!/bin/bash
set -e
cd "$(dirname "$0")"
echo 'Paste your Gemini API key here. It will not be shown or added to shell history.'
read -r -s -p 'Gemini API key: ' rl_api_key
printf '\n'
if [ -z "$rl_api_key" ]; then echo 'No key entered. Nothing changed.'; exit 1; fi
if ! command -v python3 >/dev/null; then echo 'Python 3 is required.'; exit 1; fi
printf '%s' "$rl_api_key" | python3 -c '
import sys,os,json,tempfile
from pathlib import Path
key=sys.stdin.read().strip()
if len(key)>200 or any(c.isspace() for c in key):raise SystemExit("Invalid key format.")
p=Path(".env")
content=p.read_text() if p.exists() else Path(".env.example").read_text()
lines=content.splitlines()
lines=[x for x in lines if not x.startswith("GEMINI_API_KEY=")]
lines.append("GEMINI_API_KEY="+json.dumps(key))
with tempfile.NamedTemporaryFile("w",dir=p.parent,delete=False) as out:
    os.chmod(out.name,0o600)
    out.write("\n".join(lines)+"\n")
os.replace(out.name,p)
print("Server configuration saved. Restart ResearchLens. Do not share the .env file.")
'
unset rl_api_key
