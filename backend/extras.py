"""Evidence-led helpers and bounded public-beta request handling."""
import os, re, time, threading
from collections import OrderedDict, deque
from fastapi import HTTPException
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse


PATTERNS = {
 'Dataset / participants': r'\b(dataset|participants|patients|sample size|cohort)\b',
 'Bias / fairness': r'\b(bias|fairness|subgroup|demographic)\b',
 'Explainability method': r'\b(SHAP|LIME|explainab\w*|interpret\w*|saliency|Grad.CAM)\b',
 'External validation': r'\b(external validation|independent cohort|external dataset)\b',
 'Clinical evaluation': r'\b(clinical trial|prospective study|clinical evaluation|clinical deployment)\b',
 'Ethics / consent': r'\b(informed consent|ethics|institutional review|IRB)\b',
 'Data / code availability': r'\b(code availability|data availability|github|source code)\b',
}
def matches(document, pattern):
    found=[]
    for p in document.get('pages', [])[:100]:
        text=str(p.get('text',''))[:100000]
        m=re.search(pattern,text,re.I)
        if m:
            found.append({'page':p.get('page'), 'snippet':text[max(0,m.start()-160):min(len(text),m.end()+240)]})
        if len(found)==3: break
    return found

def healthcare(document):
    return [{'label':label,'status':'Mention found — inspect context' if (e:=matches(document,pattern)) else 'Not found in extracted text','evidence':e} for label,pattern in PATTERNS.items()]

