# -*- coding: utf-8 -*-
"""
Shared normalization rules for People-Development imports.

Source spreadsheets mix clean directorate names with branch codes that leaked
into the directorate column, and carry a couple of over-long classification
labels. These helpers canonicalize both so dashboards group cleanly. They are
used by import_pd_excel.py (at import time) and normalize_existing.py (one-time
backfill of already-imported rows) — keep the two in sync by editing only here.
"""

import re

_CODE_PREFIX = re.compile(r"^\s*\d{4,6}\s*-\s*")   # e.g. "04101 - KC DENPASAR"
_WS = re.compile(r"\s+")
_BRANCH = re.compile(r"^(kc|kcp|kk|kantor cabang)\b", re.IGNORECASE)


def _clean_ws(s):
    return _WS.sub(" ", (s or "").strip())


def normalize_directorate(value):
    """Canonicalize the pd_training.directorate column.

    Real directorates ('Direktorat ...') are kept verbatim. Branch codes/names
    that leaked into the field are bucketed so they stop polluting the
    directorate breakdown.
    """
    s = _clean_ws(value)
    if not s:
        return ""
    s = _CODE_PREFIX.sub("", s).strip()   # drop a leading "NNNNN - " branch code
    low = s.lower()
    if low.startswith("direktorat"):
        return s                          # genuine directorate — keep as recorded
    if "kantor pusat" in low:
        return "Kantor Pusat"
    if "external" in low:
        return "External Participants"
    if _BRANCH.match(low):
        return "Kantor Cabang"
    if low == "commissioner":
        return "Commissioner"
    return s


def normalize_classification(value):
    """Canonicalize a training_classification label.

    pd_training values are already clean and pass through unchanged. The only
    fix needed is collapsing the over-long 'Certification ...' ikatan-dinas
    labels (one carries a 'Managter' typo) into a single 'Certification' bucket.
    """
    s = _clean_ws(value)
    if not s:
        return ""
    if s.lower().startswith("certification "):
        return "Certification"
    return s
