"""Free-host boundaries and PostgreSQL adapter; no external API calls."""
import os,sys,subprocess,json
from pathlib import Path
from unittest.mock import patch,MagicMock
import pytest
from fastapi import HTTPException
from test_app import client,isolation,pdf,upload
import config
from security import connection


def test_free_pdf_worker_limits(client,monkeypatch):
    monkeypatch.setattr(config,'FREE_HOST_MODE',True)
    monkeypatch.setattr(config,'PDF_CONCURRENCY',1)
    monkeypatch.setattr(config,'MAX_PAGES',20)
    r=client.post('/analyze',files={'file':('scan.pdf',pdf(True))})
    assert r.status_code==422 and 'text-based' in r.text
    d=upload(client);assert d['pages']
    import pymupdf
    doc=pymupdf.open()
    for i in range(21):doc.new_page().insert_text((50,50),'This is a text page for testing.')
    data=doc.tobytes();doc.close()
    r=client.post('/analyze',files={'file':('long.pdf',data)})
    assert r.status_code==422 and '20 pages' in r.text


def test_database_outage_pauses_requests_and_redacts(client,monkeypatch):
    monkeypatch.setattr(config,'DATABASE_URL','postgresql://secret:private@bad.invalid/db')
    with patch('psycopg.connect',side_effect=RuntimeError('private password and host')):
        r=client.get('/session')
        assert r.status_code==503 and 'storage' in r.text
        assert 'private' not in r.text and 'bad.invalid' not in r.text


def test_tls_and_transaction_scoped_lock(monkeypatch):
    monkeypatch.setattr(config,'PUBLIC',True)
    monkeypatch.setattr(config,'DATABASE_URL','postgresql://never-a-real-key@localhost/db')
    with patch('psycopg.connect') as connect:
        db=connect.return_value.__enter__.return_value
        with connection() as adapter:
            adapter.execute('SELECT count FROM counters WHERE bucket=?',('example',))
        assert connect.call_args.kwargs['sslmode']=='verify-full'
        assert connect.call_args.kwargs['sslrootcert']=='system'
        assert connect.call_args.kwargs['prepare_threshold'] is None
        statements=[c.args[0] for c in db.execute.call_args_list]
        assert 'SELECT pg_advisory_xact_lock(714250129)' in statements
        assert statements[-1]=='SELECT count FROM counters WHERE bucket=%s'
        connect.return_value.__exit__.assert_called_once()


def test_render_origin_resolution_and_remote_storage(tmp_path):
    env={**os.environ,'PUBLIC_MODE':'true','FREE_HOST_MODE':'true','SITE_ACCESS_CODE':'test-private-code-123456','SESSION_SECRET':'s'*48,'RENDER_EXTERNAL_HOSTNAME':'researchlens-demo.onrender.com','DATABASE_URL':'postgresql://test:fake@localhost/test'}
    env.pop('APP_ORIGIN',None);env.pop('STATE_DIR',None)
    p=subprocess.run([sys.executable,'-c','import config; print(config.ORIGIN,config.MAX_PAGES,config.MAX_PDF_BYTES)'],env=env,cwd=Path(__file__).parent,capture_output=True)
    assert p.returncode==0,p.stderr.decode()
    assert p.stdout.strip()==b'https://researchlens-demo.onrender.com 20 5242880'
    env.pop('DATABASE_URL')
    env['STATE_DIR']=str(tmp_path)
    p=subprocess.run([sys.executable,'-c','import config'],env=env,cwd=Path(__file__).parent,capture_output=True)
    assert p.returncode!=0 and b'PostgreSQL' in p.stderr


def test_missing_local_condition_is_rejected():
    from grounded import validate_points
    sources=[{'id':'S1','page':4,'snippet':'If the model is highly non-linear even in the locality of the prediction, there may not be a faithful explanation.'}]
    claim=lambda text:{'points':[{'label':'Limitations','text':text,'source_ids':['S1']}]}
    assert not validate_points(claim('If the model is highly non-linear, LIME may fail.'),sources,'simple_en')[0]
    assert validate_points(claim('If the model is highly non-linear locally, a faithful explanation may not exist.'),sources,'simple_en')[0]
