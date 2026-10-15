"""ResearchLens v5: Gemini-ready, evidence-bound paper chat."""
import json,os,secrets,hmac,subprocess,sys
from pathlib import Path
from typing import Literal
import requests
from fastapi import FastAPI,File,HTTPException,Request,UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,ConfigDict,Field
import config
from security import SecurityMiddleware,session,new_session,set_session,csrf,consume_many,ip_key,capacity,stamp,verify_document
from analyzer import analyze_document,retrieve_chunks
from grounded import explain
from extras import healthcare,matches,PATTERNS

from security import connection
with connection() as _db:
    _db.execute('SELECT 1')

app=FastAPI(title='ResearchLens AI',docs_url=None,redoc_url=None,openapi_url=None)
if config.DEV_ORIGIN:
    app.add_middleware(CORSMiddleware,allow_origins=[config.DEV_ORIGIN],allow_credentials=True,allow_methods=['GET','POST'],allow_headers=['Content-Type','X-CSRF-Token'])
app.add_middleware(SecurityMiddleware)

class Strict(BaseModel):model_config=ConfigDict(extra='forbid')
class DocumentRequest(Strict):
    document:dict
    language:Literal['simple_en','bn']='simple_en'
    mode:Literal['student','researcher']='student'
class AskRequest(DocumentRequest):
    question:str=Field(min_length=1,max_length=1000)
    previous_question:str=Field(default='',max_length=1000)
class ComparisonRequest(Strict):documents:list[dict]=Field(min_length=2,max_length=6)
class AccessRequest(Strict):
    code:str=Field(default='',max_length=256)
    turnstile_token:str=Field(default='',max_length=2048)
class FeedbackRequest(Strict):
    rating:Literal['helpful','incorrect','unclear']
    comment:str=Field(default='',max_length=1000)
    feature:str=Field(default='',max_length=80)

@app.get('/health')
def health():return {'status':'ok','version':'5.2.0','analysis_version':5}

@app.get('/session')
def bootstrap(request:Request):
    consume_many([('bootstrap:'+ip_key(request),60,30)])
    from starlette.responses import JSONResponse
    s=session(request) or new_session()
    response=JSONResponse({'csrf':csrf(s),'authorized':bool(s.get('authorized')),'gate':'turnstile' if config.PUBLIC and config.TURNSTILE_SITE_KEY and not config.BETA_INVITE_ONLY else 'code' if config.PUBLIC else 'none','site_key':config.TURNSTILE_SITE_KEY if config.PUBLIC else '', 'privacy':'PDFs are processed temporarily by this server. Selected paper text and questions go to the configured AI provider. Do not upload private patient records or confidential research.'})
    set_session(response,s);return response

@app.post('/authorize')
def authorize(req:AccessRequest,request:Request):
    consume_many([('authorize:'+ip_key(request),3600,10)])
    s=request.state.session
    ok=not config.PUBLIC
    if config.PUBLIC and req.code and config.ACCESS_CODE:ok=hmac.compare_digest(req.code,config.ACCESS_CODE)
    if config.PUBLIC and not config.BETA_INVITE_ONLY and not ok and req.turnstile_token and config.TURNSTILE_SECRET_KEY:
        try:
            result=requests.post('https://challenges.cloudflare.com/turnstile/v0/siteverify',data={'secret':config.TURNSTILE_SECRET_KEY,'response':req.turnstile_token},timeout=(3,8),allow_redirects=False).json()
            from urllib.parse import urlsplit
            ok=result.get('success') is True and result.get('hostname')==urlsplit(config.ORIGIN).hostname and result.get('action')=='researchlens'
        except (requests.RequestException,ValueError):ok=False
    if not ok:raise HTTPException(403,'Access verification failed. Try again.')
    from starlette.responses import JSONResponse
    s['authorized']=True;response=JSONResponse({'authorized':True});set_session(response,s);return response

@app.get('/ai-status')
def ai_status():return {'provider':config.PROVIDER,'model':config.MODEL if config.PROVIDER=='gemini' else os.getenv('OLLAMA_MODEL','gemma3:4b'),'status':'key configured; availability confirmed only by a successful answer' if config.PROVIDER=='gemini' and config.GEMINI_KEY else 'API key not configured' if config.PROVIDER=='gemini' else 'local provider selected','privacy_contact':config.PRIVACY_CONTACT,'notice':'AI requests have daily limits. No key is exposed to this browser.'}

@app.post('/analyze')
def analyze(request:Request,file:UploadFile=File(...)):
    consume_many([('uploads:session:'+request.state.session['sid'],3600,10),('uploads:global',86400,500)])
    filename=Path((file.filename or '').replace('\\','/')).name[:200]
    if not filename.lower().endswith('.pdf'):raise HTTPException(400,'Please upload a PDF file.')
    data=file.file.read(config.MAX_PDF_BYTES+1)
    if len(data)>config.MAX_PDF_BYTES:raise HTTPException(413,f'PDF limit is {config.MAX_PDF_BYTES//(1024*1024)} MB.')
    if not data or b'%PDF-' not in data[:1024]:raise HTTPException(400,'This file is not a readable PDF.')
    worker=Path(__file__).with_name('pdf_worker.py')
    # Worker gets no Gemini, Turnstile, access-code or signing secrets.
    env={k:os.environ[k] for k in ['PATH','TESSDATA_PREFIX','OCR_LANGUAGES','LANG','SYSTEMROOT'] if k in os.environ}
    env['RL_FREE_PDF_MODE']='true' if config.FREE_HOST_MODE else 'false'
    with capacity('pdf',config.PDF_CONCURRENCY,ttl=60):
        try:
            completed=subprocess.run([sys.executable,'-I',str(worker)],input=data,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=45,env=env,check=False)
            payload=json.loads(completed.stdout)
        except subprocess.TimeoutExpired:raise HTTPException(422,'PDF processing exceeded 45 seconds. Use fewer pages or a text-based PDF.') from None
        except (ValueError,OSError):raise HTTPException(422,'PDF could not be processed safely.') from None
    if 'result' not in payload:
        messages={'ocr_unavailable':'Scanned PDF needs Tesseract OCR support on the server.','ocr_limit':'Maximum 8 scanned pages per PDF.','page_limit':f'PDF limit is {config.MAX_PAGES} pages.','scan_disabled':'This free-hosted beta accepts text-based PDFs only; scanned PDFs need OCR on a larger server.','encrypted_pdf':'Password-protected PDFs are not supported.'}
        raise HTTPException(422,messages.get(payload.get('error'),'PDF could not be read safely. Use a smaller, unencrypted PDF.'))
    d=payload['result'];d['filename']=filename
    return stamp(d,request.state.session)

def paper(req,request):return verify_document(req.document,request.state.session)

@app.post('/explain')
@app.post('/understand')
def explain_paper(req:DocumentRequest,request:Request):return explain(paper(req,request),req.language,request.state.session['sid'],mode=req.mode)

@app.post('/ask')
def ask_paper(req:AskRequest,request:Request):
    if not req.question.strip():raise HTTPException(422,'Type a question first.')
    return explain(paper(req,request),req.language,request.state.session['sid'],question=req.question.strip(),mode=req.mode,previous_question=req.previous_question)

@app.post('/healthcare')
def checklist(req:DocumentRequest,request:Request):return {'items':healthcare(paper(req,request)),'notice':'Evidence screening only; a mention does not establish clinical readiness.'}

@app.post('/research-gaps')
def gaps(req:DocumentRequest,request:Request):
    d=paper(req,request)
    sources=retrieve_chunks(d['pages'],'limitations future work',top_k=3)
    return {'gaps':[{'gap':'Inspect this passage for a possible follow-up research question.','why_it_matters':'Confirm novelty with a wider literature search.','type':'review_prompt','evidence':[{'page':c['page'],'snippet':c['text'][:700]}]} for c in sources]}

@app.post('/comparison')
@app.post('/compare')
def comparison(req:ComparisonRequest,request:Request):
    items=[]
    for d in req.documents:
        verify_document(d,request.state.session)
        fresh=analyze_document(d.get('filename','paper.pdf'),d['pages'])
        items.append({'title':fresh['metadata']['title'],'methodology':fresh['methodology'],'results':fresh['results'],'limitations':fresh['limitations'],'dataset':matches(d,PATTERNS['Dataset / participants'])})
    return {'papers':items}

@app.post('/feedback')
def feedback(req:FeedbackRequest):return {'persisted':False,'message':'Feedback saved only in your downloaded report.'}

@app.exception_handler(Exception)
async def generic_error(request:Request,exc:Exception):
    from starlette.responses import JSONResponse
    return JSONResponse({'detail':'The request could not be completed. Please retry.'},status_code=500)

_dist=Path(__file__).resolve().parent.parent/'frontend'/'dist'
if _dist.exists():app.mount('/',StaticFiles(directory=_dist,html=True),name='website')
