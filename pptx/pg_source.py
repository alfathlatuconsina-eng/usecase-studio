#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Reads PMO projects from the SAME PostgreSQL database the web dashboard uses,
and returns rows shaped exactly like the Excel reader did — so the existing
generate_dashboard.py logic works unchanged.

Set DATABASE_URL to point at your Postgres (defaults to local dev).
"""
import os
from sqlalchemy import create_engine, text

DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres@localhost:5432/pmo",
)

# DB column  ->  key expected by generate_dashboard.py
def _row_to_generator_dict(r):
    return {
        "Project Name": r.name,
        "Group": r.group,
        "Status": r.status,
        "Project Nature": r.nature,
        "Realization %": _n(r.real),
        "Targeted Timeline %": _n(r.tl),
        "Budget Original %": _n(r.bo),
        "Budget Realization %": _n(r.br),
        "Target Date": r.target,
        "Original Target": r.orig,
        "Ownership": r.owner,
        "PM Team": r.pm,
        "Current Phase": r.phase,
        "Next Activities": r.next_act,
        "Risk": r.risk or "—",
        "Stopper": r.stop or "—",
        "PMO Recommendation": r.reco,
        # fields the web form doesn't capture yet -> left blank, slides still build
        "Targeted Aim": "",
        "Background": "",
        "Objective": "",
        "Notes": "",
        "Issues at Hand": "",
        "Challenges": "",
    }


def _n(v):
    if v is None:
        return ""
    f = float(v)
    return int(f) if f == int(f) else f


def read_projects_from_pg(_path_ignored=None):
    eng = create_engine(DB_URL, pool_pre_ping=True)
    with eng.connect() as c:
        rows = c.execute(text(
            "SELECT name, \"group\", status, nature, real, tl, bo, br, "
            "target, orig, owner, pm, phase, next_act, risk, stop, reco "
            "FROM projects ORDER BY sort, id")).fetchall()
    return [_row_to_generator_dict(r) for r in rows]


def read_meta_from_pg(_path_ignored=None):
    import datetime as dt
    return {"Update Label": f"(Update {dt.date.today().strftime('%d %b %Y')})"}
