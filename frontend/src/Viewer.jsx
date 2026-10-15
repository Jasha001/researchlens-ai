import React,{useEffect,useRef,useState} from 'react';
import * as pdfjs from 'pdfjs-dist';
import 'pdfjs-dist/web/pdf_viewer.css';
import worker from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
pdfjs.GlobalWorkerOptions.workerSrc=worker;
export default function Viewer({file,evidence,onClose}){
 const canvas=useRef(),layer=useRef(),[error,setError]=useState(''),[page,setPage]=useState(evidence.page||1),[count,setCount]=useState(1);
 useEffect(()=>setPage(evidence.page||1),[evidence]);
 useEffect(()=>{let disposed=false,task,render;
 (async()=>{try{setError('');task=pdfjs.getDocument({isEvalSupported:false, data:new Uint8Array(await file.arrayBuffer())});const doc=await task.promise;if(disposed)return;setCount(doc.numPages);const p=await doc.getPage(Math.min(Math.max(page,1),doc.numPages));const viewport=p.getViewport({scale:1.2});canvas.current.width=viewport.width;canvas.current.height=viewport.height;layer.current.replaceChildren();layer.current.style.setProperty('--scale-factor','1.2');render=p.render({canvasContext:canvas.current.getContext('2d'),viewport});await render.promise;if(disposed)return;const text=await p.getTextContent();const tl=new pdfjs.TextLayer({textContentSource:text,container:layer.current,viewport});await tl.render();if(disposed)return;
 const normalized=x=>x.toLowerCase().replace(/\s+/g,' ').trim();const quote=normalized(evidence.snippet||'');for(const span of layer.current.querySelectorAll('span')){const t=normalized(span.textContent);if(t.length>3&&quote.includes(t))span.classList.add('highlight')}
 }catch(e){if(!disposed)setError('PDF viewer could not render this page. Re-upload the original PDF if needed.')}})();return()=>{disposed=true;render?.cancel();task?.destroy()};
 },[file,page,evidence]);
 return <div className="viewerOverlay" role="dialog" aria-modal="true" aria-label="PDF source"><div className="viewer"><div className="viewerTools"><button onClick={onClose}>Close</button><button disabled={page<=1} onClick={()=>setPage(p=>p-1)}>Previous</button><span>Page {page} / {count}</span><button disabled={page>=count} onClick={()=>setPage(p=>p+1)}>Next</button></div><p>Matching text fragments are highlighted. Check the surrounding context.</p>{error&&<p role="alert">{error}</p>}<blockquote>{evidence.snippet}</blockquote><div className="pdfPage"><canvas ref={canvas}/><div className="textLayer" ref={layer}/></div></div></div>
}
