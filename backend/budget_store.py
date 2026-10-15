"""Durable quota storage: local SQLite or TLS PostgreSQL (Neon compatible).

Every PostgreSQL transaction holds the same transaction-scoped advisory lock.
This serializes small quota updates across connections/processes; no transaction
or connection survives a provider call. Never fall back to ephemeral quotas.
"""
from contextlib import contextmanager
import sqlite3,logging
from urllib.parse import urlsplit
from fastapi import HTTPException
import config

class PostgresAdapter:
    def __init__(self,conn):self.conn=conn
    def execute(self,sql,args=()):
        # All statements are fixed application SQL, never user-supplied SQL.
        if sql=='BEGIN IMMEDIATE':return None
        return self.conn.execute(sql.replace('?','%s'),args)
    def executemany(self,sql,rows):
        with self.conn.cursor() as cur:cur.executemany(sql.replace('?','%s'),rows)

def diagnostic_code(exc):
    # Match provider details privately; emit only fixed, non-sensitive categories.
    message=str(exc).lower()
    state=getattr(exc,'sqlstate',None)
    if state in ('28P01','28000') or any(x in message for x in ('password authentication failed','authentication failed','no password supplied')):return 'DB_AUTH'
    if any(x in message for x in ('certificate verify failed','root certificate','sslrootcert','ssl error','ssl is not enabled','channel binding')):return 'DB_TLS'
    if any(x in message for x in ('could not translate host','name or service not known','failed to resolve','nodename nor servname')):return 'DB_DNS'
    if state in ('57014','55P03') or 'timeout' in message or 'timed out' in message:return 'DB_TIMEOUT'
    if state=='42501' or 'permission denied' in message:return 'DB_PERMISSION'
    if state=='3D000' or 'database does not exist' in message:return 'DB_NAME'
    if any(x in message for x in ('invalid connection option','missing "="','invalid uri','invalid percent-encoded','invalid port')):return 'DB_URL_FORMAT'
    if state and state.startswith('42'):return 'DB_SCHEMA'
    return 'DB_UNAVAILABLE'

@contextmanager
def connection():
    try:
        if config.DATABASE_URL:
            # Reject copied shell snippets, unexpanded passwords and outer quotes.
            value=config.DATABASE_URL
            if not value.startswith(('postgresql://','postgres://')) or any(c in value for c in ('\n','\r')):
                raise HTTPException(503,'Database configuration needs a connection URL only. Code: DB_URL_FORMAT')
            try:
                parsed=urlsplit(value)
                if not parsed.hostname or not parsed.username or not parsed.password or parsed.path in ('','/') or parsed.fragment or any(c in value for c in ('<password>','[YOUR-PASSWORD]')):raise ValueError()
                parsed.port
            except ValueError:
                raise HTTPException(503,'Database connection URL is incomplete or malformed. Code: DB_URL_FORMAT') from None
            import psycopg
            kwargs={'connect_timeout':15,'prepare_threshold':None,'application_name':'researchlens-quotas'}
            if config.PUBLIC:
                # Use the platform trust store and verify the server identity.
                kwargs.update(sslmode='verify-full',sslrootcert='system')
            with psycopg.connect(config.DATABASE_URL,**kwargs) as conn:
                conn.execute("SET LOCAL statement_timeout = '5s'")
                conn.execute("SET LOCAL lock_timeout = '4s'")
                conn.execute('SELECT pg_advisory_xact_lock(714250129)')
                conn.execute('CREATE TABLE IF NOT EXISTS counters (bucket TEXT, period BIGINT, count INTEGER NOT NULL, PRIMARY KEY(bucket,period))')
                conn.execute('CREATE TABLE IF NOT EXISTS leases (id TEXT PRIMARY KEY, lane TEXT, expires DOUBLE PRECISION)')
                yield PostgresAdapter(conn)
        else:
            conn=sqlite3.connect(config.BUDGET_DB,timeout=5)
            try:
                conn.execute('PRAGMA journal_mode=WAL')
                conn.execute('CREATE TABLE IF NOT EXISTS counters (bucket TEXT, period INTEGER, count INTEGER NOT NULL, PRIMARY KEY(bucket,period))')
                conn.execute('CREATE TABLE IF NOT EXISTS leases (id TEXT PRIMARY KEY, lane TEXT, expires REAL)')
                with conn:yield conn
            finally:conn.close()
    except HTTPException:raise
    except Exception as exc:
        code=diagnostic_code(exc)
        logging.getLogger('uvicorn.error').error('Quota storage failure: %s',code)
        # No DSN, database password, SQL or provider response in client errors.
        raise HTTPException(503,'Usage storage is temporarily unavailable. Retry shortly; AI access is paused. Code: '+code) from None
