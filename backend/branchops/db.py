"""Akses PostgreSQL untuk modul Branch Operations.

Memakai database yang SAMA dengan platform (pmo), tapi seluruh tabel modul ini
ber-prefix branchops_ sehingga tidak menyentuh tabel dashboard lain.

DATABASE_URL platform berformat SQLAlchemy (postgresql+psycopg2://...);
di sini dikonversi ke DSN psycopg2 biasa.
"""
from __future__ import annotations

import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool

_pool: ThreadedConnectionPool | None = None


def _dsn() -> str:
    url = os.environ.get("DATABASE_URL",
                         "postgresql+psycopg2://postgres@localhost:5432/pmo")
    return url.replace("postgresql+psycopg2://", "postgresql://", 1)


def init_pool(dsn=None, minconn=1, maxconn=6):
    global _pool
    if _pool is None:
        _pool = ThreadedConnectionPool(minconn, maxconn, dsn or _dsn())
    return _pool


@contextmanager
def conn():
    pool = init_pool()
    c = pool.getconn()
    try:
        yield c
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        pool.putconn(c)


@contextmanager
def cur(dict_rows=True):
    with conn() as c:
        factory = psycopg2.extras.RealDictCursor if dict_rows else None
        with c.cursor(cursor_factory=factory) as k:
            yield k


def q(sql, params=None):
    with cur() as k:
        k.execute(sql, params or ())
        return [dict(r) for r in k.fetchall()]


def q1(sql, params=None):
    r = q(sql, params)
    return r[0] if r else None


def execute(sql, params=None):
    with cur() as k:
        k.execute(sql, params or ())
        return k.rowcount


# --------------------------------------------------------------------------
def get_settings() -> dict:
    out = {}
    for r in q("SELECT kunci, nilai FROM branchops_settings"):
        v = r["nilai"]
        try:
            out[r["kunci"]] = int(v)
        except (TypeError, ValueError):
            try:
                out[r["kunci"]] = float(v)
            except (TypeError, ValueError):
                out[r["kunci"]] = v
    return out


def set_setting(kunci, nilai, user_email=None):
    execute("""INSERT INTO branchops_settings (kunci, nilai, updated_by, updated_at)
               VALUES (%s,%s,%s, now())
               ON CONFLICT (kunci) DO UPDATE
                 SET nilai=EXCLUDED.nilai, updated_by=EXCLUDED.updated_by, updated_at=now()""",
            (kunci, str(nilai), user_email))


def get_branches() -> dict:
    return {b["branch_code"]: b for b in
            q("SELECT * FROM branchops_branches ORDER BY branch_code")}


def audit(user_email, action, entity=None, entity_id=None, detail=None):
    """Jejak audit modul ini sendiri; tidak menyentuh audit_log milik PMO."""
    import json
    try:
        execute("""INSERT INTO branchops_audit (user_email, action, entity, entity_id, detail)
                   VALUES (%s,%s,%s,%s,%s)""",
                (user_email, action, entity,
                 str(entity_id) if entity_id is not None else None,
                 json.dumps(detail, default=str) if detail else None))
    except Exception:      # audit tidak boleh menggagalkan aksi utama
        pass
