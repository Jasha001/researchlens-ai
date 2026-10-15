"""Signed sessions/documents, CSRF checks and durable SQLite budgets."""
import base64,hashlib,hmac,json,secrets,sqlite3,time
from contextlib import contextmanager
from urllib.parse import urlsplit
from fastapi import HTTPException,Request
from starlette.responses import JSONResponse
import config
COOKIE='rl_session'

def sign(data):
    raw=base64.urlsafe_b64encode(json.dumps(data,separators=(',',':'),sort_keys=True).encode()).decode().rstrip('=')
    mac=hmac.new(config.SECRET.encode(),raw.encode(),hashlib.sha256).hexdigest()
    return raw+'.'+mac

def unsign(value):
    try:
        raw,mac=value.split('.')
        expected=hmac.new(config.SECRET.encode(),raw.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(mac,expected):return None
        obj=json.loads(base64.urlsafe_b64decode(raw+'='*((-len(raw))%4)))
        if not isinstance(obj,dict) or obj.get('exp',0)<time.time():return None
        return obj
    except (ValueError,TypeError,UnicodeError,AttributeError):return None

def session(request):
    s=unsign(request.cookies.get(COOKIE,''))
    return s if s and isinstance(s.get('sid'),str) and len(s['sid'])==32 and s.get('kind')=='session' and s.get('public')==config.PUBLIC else None

def set_session(response,s):
    response.set_cookie(COOKIE,sign(s),max_age=86400,httponly=True,secure=config.PUBLIC,samesite='strict',path='/')

def csrf(s):return hmac.new(config.SECRET.encode(),('csrf:'+s['sid']).encode(),hashlib.sha256).hexdigest()
def new_session():return {'sid':secrets.token_hex(16),'exp':int(time.time())+86400,'kind':'session','public':config.PUBLIC,'authorized':not config.PUBLIC}
def ip_key(request):
    # Deliberately ignore spoofable X-Forwarded-For. Configure trusted proxy separately.
    addr=request.client.host if request.client else 'unknown'
    return hmac.new(config.SECRET.encode(),addr.encode(),hashlib.sha256).hexdigest()[:32]

from budget_store import connection

def consume_many(limits):
    now=time.time()
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM counters WHERE period < ?', (int(now)-172800,))
        values=[]
        for name,seconds,maximum in limits:
            period=int(now//seconds)*seconds
            row=db.execute('SELECT count FROM counters WHERE bucket=? AND period=?',(name,period)).fetchone()
            count=row[0] if row else 0
            if count>=maximum:raise HTTPException(429,'Usage limit reached. Please try again later.',headers={'Retry-After':str(seconds)})
            values.append((name,period,count+1))
        db.executemany('INSERT INTO counters VALUES (?,?,?) ON CONFLICT(bucket,period) DO UPDATE SET count=excluded.count',values)

@contextmanager
def capacity(lane,maximum,ttl=130):
    token=secrets.token_hex(16)
    with connection() as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('DELETE FROM leases WHERE expires < ?',(time.time(),))
        count=db.execute('SELECT COUNT(*) FROM leases WHERE lane=?',(lane,)).fetchone()[0]
        if count>=maximum:raise HTTPException(429,'Service is busy. Please retry shortly.',headers={'Retry-After':'10'})
        db.execute('INSERT INTO leases VALUES (?,?,?)',(token,lane,time.time()+ttl))
    try:yield
    finally:
        with connection() as db:db.execute('DELETE FROM leases WHERE id=?',(token,))

def canonical(document):
    pages=document.get('pages')
    if not isinstance(pages,list) or not 1<=len(pages)<=config.MAX_PAGES:raise HTTPException(422,'Invalid paper pages.')
    total=0
    for i,p in enumerate(pages):
        if not isinstance(p,dict) or p.get('page')!=i+1 or not isinstance(p.get('text'),str):raise HTTPException(422,'Invalid paper page structure.')
        total+=len(p['text'])
        if len(p['text'])>100000 or total>1200000:raise HTTPException(413,'Extracted paper text is too large.')
    return json.dumps(pages,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()

def stamp(document,s):
    digest=hashlib.sha256(canonical(document)).hexdigest()
    document['document_token']=sign({'kind':'paper','sid':s['sid'],'digest':digest,'exp':int(time.time())+86400})
    return document

def verify_document(document,s):
    token=unsign(document.get('document_token',''))
    digest=hashlib.sha256(canonical(document)).hexdigest()
    if not token or token.get('kind')!='paper' or token.get('sid')!=s['sid'] or not hmac.compare_digest(token.get('digest',''),digest):
        raise HTTPException(403,'Paper permission expired or source text changed. Upload the original PDF again.')
    return document

class SecurityMiddleware:
    def __init__(self,app):self.app=app
    async def __call__(self,scope,receive,send):
        if scope['type']!='http':return await self.app(scope,receive,send)
        req=Request(scope);path=req.url.path
        async def respond(code,msg):return await JSONResponse({'detail':msg},status_code=code)(scope,receive,secured_send)
        async def secured_send(message):
            if message['type']=='http.response.start':
                csp="default-src 'self'; script-src 'self' https://challenges.cloudflare.com; worker-src 'self' blob:; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self'; connect-src 'self' https://challenges.cloudflare.com; frame-src https://challenges.cloudflare.com; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
                headers=[(b'x-content-type-options',b'nosniff'),(b'x-frame-options',b'DENY'),(b'referrer-policy',b'no-referrer'),(b'permissions-policy',b'camera=(), microphone=(), geolocation=()'),(b'content-security-policy',csp.encode()),(b'cache-control',b'no-store')]
                if config.PUBLIC:headers.append((b'strict-transport-security',b'max-age=31536000'))
                message['headers']=message.get('headers',[])+headers
            await send(message)
        if req.url.hostname not in config.ALLOWED_HOSTS:return await respond(400,'Invalid host.')
        origin=req.headers.get('origin')
        allowed={config.ORIGIN}
        if config.DEV_ORIGIN:allowed.add(config.DEV_ORIGIN)
        if origin and origin not in allowed:return await respond(403,'Origin not allowed.')
        if req.method=='POST':
            if not origin:return await respond(403,'Origin header required.')
            s=session(req)
            if not s or not hmac.compare_digest(req.headers.get('x-csrf-token',''),csrf(s)):return await respond(403,'Session expired. Refresh the page.')
            if config.PUBLIC and path!='/authorize' and not s.get('authorized'):return await respond(403,'Complete site access verification first.')
            scope.setdefault('state',{})['session']=s
            try:consume_many([('ip:'+ip_key(req),60,30)])
            except HTTPException as e:return await respond(e.status_code,e.detail)
            try:
                if int(req.headers.get('content-length','0'))>config.MAX_BODY_BYTES:return await respond(413,'Request too large.')
            except ValueError:return await respond(400,'Invalid Content-Length.')
            # Buffer once, with a deadline/size bound including chunked bodies.
            import asyncio
            body=bytearray()
            try:
                async with asyncio.timeout(15):
                    while True:
                        msg=await receive()
                        if msg['type']=='http.disconnect':return
                        body.extend(msg.get('body',b''))
                        if len(body)>config.MAX_BODY_BYTES:return await respond(413,'Request too large.')
                        if not msg.get('more_body'):break
            except TimeoutError:return await respond(408,'Upload took too long.')
            delivered=False
            async def replay():
                nonlocal delivered
                if not delivered:delivered=True;return {'type':'http.request','body':bytes(body),'more_body':False}
                return await receive()
            return await self.app(scope,replay,secured_send)
        await self.app(scope,receive,secured_send)
