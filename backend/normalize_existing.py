#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-time backfill: apply the normalize.py rules to rows already imported into
pd_training and pd_ikatan_dinas. The Excel importer is append-only, so existing
rows must be cleaned in place after the rules are introduced.

Usage:
    cd /opt/pmo/backend && source venv/bin/activate
    python normalize_existing.py          # apply
    python normalize_existing.py --dry    # preview only, no writes

Idempotent: running it again after a clean pass changes nothing.
"""

import sys
from sqlalchemy import select, update, func

from app import Session, PdTraining, PdIkatanDinas
from normalize import normalize_directorate, normalize_classification


def _backfill(session, model, column, fn, dry):
    """Map each distinct value through fn and UPDATE the rows that change."""
    col = getattr(model, column)
    pairs = session.execute(
        select(col, func.count()).group_by(col)
    ).all()
    changed_vals = changed_rows = 0
    for old, n in pairs:
        new = fn(old or "")
        if new != (old or ""):
            changed_vals += 1
            changed_rows += n
            print(f"  {model.__tablename__}.{column}: {old!r} -> {new!r}  ({n} rows)")
            if not dry:
                session.execute(
                    update(model).where(col == old).values(**{column: new})
                )
    return changed_vals, changed_rows


def main():
    dry = "--dry" in sys.argv
    print("DRY RUN — no writes\n" if dry else "Applying normalization\n")
    total_rows = 0
    with Session() as s:
        for model, column, fn in (
            (PdTraining,   "directorate",             normalize_directorate),
            (PdTraining,   "training_classification", normalize_classification),
            (PdIkatanDinas, "training_classification", normalize_classification),
        ):
            cv, cr = _backfill(s, model, column, fn, dry)
            print(f"-> {model.__tablename__}.{column}: {cv} distinct value(s), {cr} row(s) updated\n")
            total_rows += cr
        if not dry:
            s.commit()
    print(f"Done. {total_rows} row(s) {'would be ' if dry else ''}updated.")


if __name__ == "__main__":
    main()
