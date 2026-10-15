"""Isolated PDF extraction: stdin bytes, stdout JSON, no credentials in env."""
import sys,os,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
FREE=os.getenv('RL_FREE_PDF_MODE')=='true'
try:
    import resource
    resource.setrlimit(resource.RLIMIT_CPU,(35,35))
    resource.setrlimit(resource.RLIMIT_AS,((256 if FREE else 1024)*1024*1024,)*2)
    resource.setrlimit(resource.RLIMIT_FSIZE,(20*1024*1024,20*1024*1024))
except (ImportError,ValueError,OSError):pass
import pymupdf as fitz
from pdf_text import extract_page
from analyzer import analyze_document
try:
    limit=(5 if FREE else 10)*1024*1024
    data=sys.stdin.buffer.read(limit+1)
    if len(data)>limit or b'%PDF-' not in data[:1024]:raise ValueError('invalid_pdf')
    with fitz.open(stream=data,filetype='pdf') as doc:
        if doc.needs_pass:raise ValueError('encrypted_pdf')
        if not 1<=len(doc)<=(20 if FREE else 40):raise ValueError('page_limit')
        pages=[];ocr=[];total=0
        for i,p in enumerate(doc):
            if p.rect.width*p.rect.height>10000000:raise ValueError('oversized_page')
            text=extract_page(p)
            if not text.strip():
                if FREE:raise ValueError('scan_disabled')
                if len(ocr)>=8:raise ValueError('ocr_limit')
                try:
                    tp=p.get_textpage_ocr(language=os.getenv('OCR_LANGUAGES','eng'),dpi=100,full=True)
                    text=p.get_text('text',textpage=tp);ocr.append(i+1)
                except Exception:raise ValueError('ocr_unavailable') from None
            total+=len(text)
            if total>1200000 or len(text)>100000:raise ValueError('text_limit')
            pages.append({'page':i+1,'text':text})
    if not any(p['text'].strip() for p in pages):raise ValueError('empty_pdf')
    result=analyze_document('paper.pdf',pages);result['analysis_version']=5;result['ocr_pages']=ocr
    print(json.dumps({'result':result},ensure_ascii=False))
except Exception as e:
    code=str(e) if isinstance(e,ValueError) else 'unreadable_pdf'
    print(json.dumps({'error':code if code in {'scan_disabled','invalid_pdf','encrypted_pdf','page_limit','oversized_page','ocr_limit','ocr_unavailable','text_limit','empty_pdf'} else 'unreadable_pdf'}))
    sys.exit(1)
