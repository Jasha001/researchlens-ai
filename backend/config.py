"""Server-only configuration. No environment values are returned to clients."""
import os,secrets
from pathlib import Path
from urllib.parse import urlsplit
from dotenv import load_dotenv
ROOT=Path(__file__).resolve().parent.parent
load_dotenv(ROOT/'.env',override=False)
DATABASE_URL=os.getenv('DATABASE_URL','').strip()
FREE_HOST_MODE=os.getenv('FREE_HOST_MODE','false').lower()=='true'
BETA_INVITE_ONLY=os.getenv('BETA_INVITE_ONLY','true').lower()=='true'
PUBLIC=os.getenv('PUBLIC_MODE','false').lower()=='true'
render_host=os.getenv('RENDER_EXTERNAL_HOSTNAME','')
ORIGIN=(os.getenv('APP_ORIGIN') or ('https://'+render_host if PUBLIC and render_host else 'http://localhost:8182')).rstrip('/')
parts=urlsplit(ORIGIN)
if parts.scheme not in ('http','https') or not parts.hostname or parts.path or parts.query or parts.fragment or parts.username:
    raise RuntimeError('APP_ORIGIN must be a plain http(s) origin.')
SECRET=os.getenv('SESSION_SECRET','')
ACCESS_CODE=os.getenv('SITE_ACCESS_CODE','')
TURNSTILE_SITE_KEY=os.getenv('TURNSTILE_SITE_KEY','')
TURNSTILE_SECRET_KEY=os.getenv('TURNSTILE_SECRET_KEY','')
if PUBLIC:
    if parts.scheme!='https':raise RuntimeError('Public mode requires an HTTPS APP_ORIGIN.')
    if BETA_INVITE_ONLY and len(ACCESS_CODE)<16:raise RuntimeError('Invited beta requires SITE_ACCESS_CODE of at least 16 characters (Turnstile alone is insufficient).')
    if not DATABASE_URL and not os.getenv('STATE_DIR'):raise RuntimeError('Public mode requires explicit persistent STATE_DIR.')
    if len(SECRET)<32:raise RuntimeError('Public mode requires a SESSION_SECRET of at least 32 characters.')
    if not (len(ACCESS_CODE)>=12 or (TURNSTILE_SITE_KEY and TURNSTILE_SECRET_KEY)):
        raise RuntimeError('Public mode requires Turnstile keys or a SITE_ACCESS_CODE of at least 12 characters.')
SECRET=SECRET or secrets.token_urlsafe(48)
ALLOWED_HOSTS={parts.hostname}
if not PUBLIC:ALLOWED_HOSTS.update(('localhost','127.0.0.1','testserver'))
DEV_ORIGIN=os.getenv('DEV_ORIGIN','') if not PUBLIC else ''
DATA_DIR=Path(os.getenv('STATE_DIR',str(ROOT/'runtime')))
if not DATABASE_URL:DATA_DIR.mkdir(parents=True,exist_ok=True)
BUDGET_DB=DATA_DIR/'limits.sqlite3'

def integer(name,default,low,high):
    value=int(os.getenv(name,str(default)))
    if not low<=value<=high:raise RuntimeError(f'{name} is outside allowed bounds.')
    return value
MAX_PDF_BYTES=(5 if FREE_HOST_MODE else 10)*1024*1024
MAX_BODY_BYTES=(6 if FREE_HOST_MODE else 12)*1024*1024
MAX_AI_DAY=integer('MAX_AI_REQUESTS_PER_DAY',100,1,10000)
MAX_AI_SESSION_DAY=integer('MAX_AI_REQUESTS_PER_SESSION_DAY',20,1,200)
MAX_OUTPUT=integer('AI_MAX_OUTPUT_TOKENS',1600,256,4096)
MAX_PAGES=20 if FREE_HOST_MODE else 40
PROVIDER=os.getenv('AI_PROVIDER','gemini')
if PROVIDER not in ('gemini','ollama'):raise RuntimeError('AI_PROVIDER must be gemini or ollama.')
MODEL=os.getenv('GEMINI_MODEL','gemini-3.1-flash-lite')
GEMINI_KEY=os.getenv('GEMINI_API_KEY','')
REVIEW=os.getenv('AI_SUPPORT_REVIEW','true').lower()=='true'

if PUBLIC and PROVIDER!='gemini':raise RuntimeError('Public beta supports Gemini only.')

PRIVACY_CONTACT=os.getenv("PRIVACY_CONTACT","")

if FREE_HOST_MODE and PUBLIC and not DATABASE_URL:raise RuntimeError('Free public hosting requires persistent PostgreSQL DATABASE_URL.')
PDF_CONCURRENCY=1 if FREE_HOST_MODE else 2
