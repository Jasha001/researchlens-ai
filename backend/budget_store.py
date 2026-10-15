"""Durable quota storage: local SQLite or TLS PostgreSQL (Neon compatible).

Every PostgreSQL transaction holds the same transaction-scoped advisory lock.
This serializes small quota updates across connections/processes; no transaction
or connection survives a provider call. Never fall back to ephemeral quotas.
"""
from contextlib import contextmanager
import sqlite3
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

@contextmanager
def connection():
    try:
        if config.DATABASE_URL:
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
    except Exception:
        # No DSN, database password, SQL or provider response in client errors.
        raise HTTPException(503,'Usage storage is temporarily unavailable. Retry shortly; AI access is paused.') from None
