"""Create a private public-beta environment file; never print credentials."""
import getpass,os,secrets
from pathlib import Path
from urllib.parse import urlsplit
root=Path(__file__).resolve().parent.parent
path=root/'.env.public'
if path.exists():raise SystemExit('.env.public already exists. Edit it locally; no secrets were overwritten.')
origin=input('Public HTTPS origin (for example https://research.example.org): ').strip().rstrip('/')
u=urlsplit(origin)
import re
if u.scheme!='https' or not u.hostname or not re.fullmatch(r'[A-Za-z0-9.-]+(?::[0-9]{1,5})?',u.netloc) or u.path or u.query or u.fragment or u.username:raise SystemExit('Enter a plain HTTPS origin.')
contact=input('Public contact email: ').strip()
if '@' not in contact or any(x in contact for x in '\r\n <>'):raise SystemExit('Invalid contact email.')
key=getpass.getpass('Gemini API key (hidden): ').strip()
code=getpass.getpass('Private beta access code (at least 16 characters, hidden): ').strip()
if not key or len(code)<16 or any(x in key+code for x in '\r\n'):raise SystemExit('Invalid key or access code.')
values={'AI_PROVIDER':'gemini','GEMINI_MODEL':'gemini-3.1-flash-lite','GEMINI_API_KEY':key,'PUBLIC_MODE':'true','BETA_INVITE_ONLY':'true','APP_ORIGIN':origin,'PUBLIC_HOST':u.netloc,'PRIVACY_CONTACT':contact,'SESSION_SECRET':secrets.token_urlsafe(48),'SITE_ACCESS_CODE':code,'STATE_DIR':'/data','MAX_AI_REQUESTS_PER_DAY':'100','MAX_AI_REQUESTS_PER_SESSION_DAY':'20','AI_SUPPORT_REVIEW':'true','AI_MAX_OUTPUT_TOKENS':'1600'}
# Raw env_file preserves literal punctuation; this file is for the public Compose service.
import json
fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'w') as f:
    for k,v in values.items():f.write(k+'='+v+'\n')
print('Private .env.public created. Do not upload, commit or share it.')
