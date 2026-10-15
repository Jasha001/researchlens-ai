"""Run after setting DATABASE_URL privately. No API calls or secret output."""
import sys,secrets,subprocess
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'backend'))
import config
from security import consume_many,capacity,connection
from fastapi import HTTPException
from concurrent.futures import ThreadPoolExecutor
if not config.DATABASE_URL:raise SystemExit('Set DATABASE_URL privately before running this check.')
key='deployment-check:'+secrets.token_hex(12)
def use(_):
    try:consume_many([(key,86400,3)]);return True
    except HTTPException as e:
        if e.status_code!=429:raise
        return False
try:
    with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(use,range(8)))
    if sum(results)!=3:raise RuntimeError()
    # An independent process must observe the same exhausted quota.
    script='from security import consume_many; from fastapi import HTTPException\ntry: consume_many([('+repr(key)+',86400,3)])\nexcept HTTPException as e: raise SystemExit(0 if e.status_code==429 else 2)\nraise SystemExit(3)'
    result=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).resolve().parent.parent/'backend',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    if result.returncode:raise RuntimeError()
    with capacity(key,1):
        try:
            with capacity(key,1):raise RuntimeError()
        except HTTPException as e:
            if e.status_code!=429:raise
    with capacity(key,1):pass
    print('PASS: PostgreSQL connectivity, atomic quotas, cross-process persistence, concurrency lease/release.')
except Exception:
    print('FAIL: database checks did not complete. No connection details were printed.')
    raise SystemExit(1) from None
finally:
    try:
        with connection() as db:
            db.execute('DELETE FROM counters WHERE bucket=?',(key,))
            db.execute('DELETE FROM leases WHERE lane=?',(key,))
    except Exception:pass
