#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate the PMO PowerPoint deck from the SAME PostgreSQL database that powers
the web dashboard — one source of truth for both.

Usage:
  python generate_from_db.py

It monkey-patches the proven generate_dashboard.py to read from Postgres
instead of Excel, then runs its build(). The template (Dashboard_Template.pptx)
must be in this folder.
"""
import os
import generate_dashboard as gen
import pg_source

# Redirect the generator's data input to PostgreSQL
gen.read_projects = pg_source.read_projects_from_pg
gen.read_meta = pg_source.read_meta_from_pg

# The generator checks for an EXCEL file path before building; point its
# input-existence check at something always-true (the template) and skip Excel.
HERE = os.path.dirname(os.path.abspath(__file__))
gen.TEMPLATE = os.path.join(HERE, "Dashboard_Template.pptx")


def _find_input_override():
    # generator calls _find_input(); return the template path just so the
    # os.path.exists() guard passes — read_projects is already patched to PG.
    return gen.TEMPLATE


gen._find_input = _find_input_override

if __name__ == "__main__":
    print("Generating deck from PostgreSQL …")
    gen.build()
