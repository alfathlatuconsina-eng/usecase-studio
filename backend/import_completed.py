#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
One-time import of COMPLETED projects (from the "29th May 2026 - completed" deck)
into the PMO `projects` table.

Safe to run more than once:
  * a project is only added if no existing project has the same name
  * nothing is deleted or overwritten

Completed projects use real/tl/bo/br = 100 so they render as fully done and are
counted by the dashboard "Completed" card automatically.

Run locally:   py import_completed.py
Run on VPS:    venv/bin/python import_completed.py
"""
from sqlalchemy import select, func
from app import Session, Project

# Each completed project mapped to the existing `projects` schema.
COMPLETED = [
    dict(name="Revamp Website", group="Non-Business", nature="Website Revamp",
         target="22 Apr 2026 (Live)", orig="01 Apr'26",
         owner="Corporate Secretary",
         phase="Live-run per 22 Apr 2026; site accessible at https://mncbank.co.id/",
         next="Post Implementation Review (PIR)."),
    dict(name="TabMotion NTB WNA", group="Business", nature="Digital Onboarding (WNA)",
         target="12 Nov 2025 (Go-Live)", orig="31 Jan 2026",
         owner="Digital Business Dir.",
         phase="Dev/SIT/UAT/Regresi/PAT completed Oct'25; Go-Live 12 Nov'25.",
         next="Live to Appstore 12 Nov'25; Playstore 6 Nov'25."),
    dict(name="GiroMotion ETB WNA", group="Business", nature="Digital Onboarding (WNA)",
         target="18 Des 2025 (Go-Live)", orig="31 Jan 2026",
         owner="Digital Business Dir.",
         phase="BRD→Live Nov-Des'25; Live to store 19 Des'25.",
         next="Go-Live 18 Des'25; reported to OJK & BI."),
    dict(name="Secured Credit Card (Nasabah NTB)", group="Business", nature="Credit Card",
         target="December 2025",
         owner="Credit Card Group",
         phase="Deploy to Production; Released APK/IPA 16 Des'25.",
         next="Enhancement Secure Card for ETB customers (BRD in progress)."),
    dict(name="EBIZZ Banking (Upgrade Database)", group="Non-Business", nature="Infrastructure / Database",
         target="07 Feb 2026",
         owner="IT Group",
         phase="Upgrade DB & engine, tuning, bug-fixing; Stress/SIT/UAT in parallel.",
         next="Go-Live 7 Feb'26."),
    dict(name="Call Center", group="Non-Business", nature="Service / Operations",
         target="01 Sep 2025 (Go-Live)",
         owner="Digital Business Dir.",
         phase="UAT form fully approved; cost memo approved by BoD.",
         next="Go-Live 1 Sep 2025."),
    dict(name="KRI Rating", group="Non-Business", nature="Corporate Rating",
         target="20 Jun 2025",
         owner="Financial Control / Corporate Secretary",
         phase="Final KRI rating for MNC Bank: single 'A' rating.",
         next="—"),
    dict(name="RDN Institusi (eBIZ Banking)", group="Business", nature="Product Development",
         target="10 Oct 2025 (Live)",
         owner="Digital Business / IT Group",
         phase="SIT/UAT/Regresi/PAT completed; LIVE 10 October 2025.",
         next="Reported to OJK."),
]


def main():
    with Session() as s:
        # existing names (case-insensitive) so we don't duplicate
        existing = {n.lower() for n in s.scalars(select(Project.name)).all()}
        max_sort = s.scalar(select(func.max(Project.sort))) or 0

        added = 0
        for row in COMPLETED:
            if row["name"].lower() in existing:
                print(f"  skip (already exists): {row['name']}")
                continue
            max_sort += 1
            s.add(Project(
                sort=max_sort,
                status="Completed",
                real=100, tl=100, bo=100, br=100,
                risk="—", stop="—", reco="—",
                **row,
            ))
            existing.add(row["name"].lower())
            added += 1
            print(f"  added: {row['name']}")

        s.commit()
        total_completed = s.scalar(
            select(func.count(Project.id)).where(Project.status == "Completed"))
        print(f"\nDone. Added {added} new completed project(s).")
        print(f"Total completed projects now in DB: {total_completed}")


if __name__ == "__main__":
    main()
