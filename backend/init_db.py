#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Initialise the PMO database:
  * creates tables
  * creates an admin login (email + password you pass in or defaults)
  * seeds the current PMO projects (only if the table is empty)

Usage:
  python init_db.py                       # uses defaults below
  python init_db.py admin@mncbank.co.id MyStrongPass
"""
import sys
import bcrypt
from sqlalchemy import select, func
from app import (Base, engine, Session, User, Project,
                 PeopleTraining, PeopleEvaluation, PeopleCertification)

DEFAULT_EMAIL = "admin@mncbank.co.id"
DEFAULT_PASSWORD = "pmo2026"   # change this — or pass args

PEOPLE_TRAININGS = [
    dict(name="Risk Management Fundamentals", category="Compliance", method="Classroom",
         organizer="OJK Institute", date_start="2026-01-20", date_end="2026-01-22",
         target_pax=30, actual_pax=28, status="Completed", budget=50, realization=48.5,
         notes="Annual compliance training for all risk staff."),
    dict(name="Python for Data Analytics", category="Technical", method="Virtual",
         organizer="Digital Learning Hub", date_start="2026-02-10", date_end="2026-02-12",
         target_pax=20, actual_pax=18, status="Completed", budget=30, realization=28,
         notes="Introductory Python course for analyst team."),
    dict(name="Leadership Excellence Program", category="Leadership", method="Classroom",
         organizer="HR Development", date_start="2026-03-03", date_end="2026-03-05",
         target_pax=15, actual_pax=14, status="Completed", budget=80, realization=77.5,
         notes="For mid-level managers."),
    dict(name="AML/CFT Certification Refresher", category="Regulatory", method="E-Learning",
         organizer="PPATK", date_start="2026-04-07", date_end="2026-04-07",
         target_pax=100, actual_pax=95, status="Completed", budget=10, realization=9.5,
         notes="Mandatory annual AML/CFT refresher for compliance staff."),
    dict(name="Project Management Professional (PMP) Prep", category="Technical", method="Virtual",
         organizer="PMI Indonesia", date_start="2026-05-05", date_end="2026-05-09",
         target_pax=10, actual_pax=9, status="Completed", budget=40, realization=38,
         notes="PMP exam preparation for PMO staff."),
    dict(name="Digital Banking Innovation Summit", category="Soft Skills", method="Classroom",
         organizer="ISEI", date_start="2026-06-15", date_end="2026-06-16",
         target_pax=25, actual_pax=None, status="Planned", budget=60, realization=None,
         notes="Upcoming conference on digital banking trends."),
    dict(name="Cybersecurity Awareness Training", category="Technical", method="E-Learning",
         organizer="IT Security Team", date_start="2026-07-01", date_end="2026-07-31",
         target_pax=250, actual_pax=None, status="Planned", budget=15, realization=None,
         notes="Annual mandatory cybersecurity awareness for all staff."),
    dict(name="Communication & Presentation Skills", category="Soft Skills", method="Classroom",
         organizer="HR Development", date_start="2026-08-11", date_end="2026-08-12",
         target_pax=20, actual_pax=None, status="Planned", budget=35, realization=None,
         notes="Presentation skills for front-liners and analysts."),
]

PEOPLE_EVALS = [
    # training_id references positions 1–5 above (seeded in order)
    dict(training_id=1, reaction_score=4.2, learning_score=78.5, respondents=28,
         notes="Well received; content was relevant and practical."),
    dict(training_id=2, reaction_score=4.5, learning_score=82.0, respondents=18,
         notes="Participants rated the hands-on exercises highly."),
    dict(training_id=3, reaction_score=4.7, learning_score=88.0, respondents=14,
         notes="Excellent facilitator; all participants recommend repeat."),
    dict(training_id=4, reaction_score=3.8, learning_score=72.0, respondents=90,
         notes="Content was mandatory; slightly dry but comprehensive."),
    dict(training_id=5, reaction_score=4.6, learning_score=85.5, respondents=9,
         notes="High engagement; 7 out of 9 plan to take the PMP exam."),
]

PEOPLE_CERTS = [
    dict(name="OJK Risk Management Certification Level 1", holder="Risk Management Group",
         cert_type="Certification", issue_date="2024-06-01", expiry_date="2026-06-01",
         status="Expiring", notes="Mass renewal required for 15 staff."),
    dict(name="PPATK AML/CFT Certification", holder="Compliance Department",
         cert_type="Certification", issue_date="2025-04-07", expiry_date="2027-04-07",
         status="Active", notes="Renewed after April 2026 training."),
    dict(name="Bank Indonesia RTGS Operator License", holder="Operations Group",
         cert_type="License", issue_date="2023-03-15", expiry_date="2026-03-15",
         status="Expired", notes="Renewal pending resubmission to Bank Indonesia."),
    dict(name="ISO 27001 Internal Auditor", holder="IT Security / Risk",
         cert_type="Certification", issue_date="2024-09-01", expiry_date="2026-09-01",
         status="Active", notes="Expires Sep 2026; renewal planned Q3 2026."),
    dict(name="Monthly Regulatory Report (LBU) — OJK", holder="Finance Group",
         cert_type="Reporting", issue_date="2026-05-01", expiry_date="2026-06-30",
         status="Active", notes="Monthly deadline — June report due 30 Jun 2026."),
    dict(name="Annual SKAI Internal Audit Report", holder="Internal Audit",
         cert_type="Reporting", issue_date="2026-01-01", expiry_date="2026-12-31",
         status="Active", notes="Annual submission to OJK."),
    dict(name="PMP Certification — PMO Staff", holder="PMO Team",
         cert_type="Certification", issue_date="2023-05-15", expiry_date="2026-05-15",
         status="Expired", notes="3 staff expired May 2026; renewal PDUs in progress."),
    dict(name="SWIFT Operator Certification", holder="Treasury Operations",
         cert_type="Certification", issue_date="2024-11-01", expiry_date="2026-11-01",
         status="Active", notes="Expiry Nov 2026; renewal reminder set for Aug 2026."),
]

SEED = [
    dict(sort=1, name="QRIS Acquiring", group="Business", status="In-Progress", nature="Technology Dev.", real=91, tl=100, bo=100, br=66, target="02 Jun 2026", orig="02 Mar'26", owner="Digital Business / Digital Technology", pm="Aditya Fatur / Naufal / Lilia", phase="Submit dokumen & surat pernyataan ke Bank Indonesia; workshop FDS dengan tim MTN.", next="Workshop Technical FDS 03 Jun; set-up 04-05 Jun 2026.", risk="Keterlambatan pemenuhan dokumen di beberapa kesempatan.", stop="Kesalahan UAT (2025); assessment (Mar'26); kekurangan dokumen (Mei'26).", reco="Telah dilakukan arrangement untuk percepatan set-up FDS."),
    dict(sort=2, name="API Management", group="Business", status="In-Progress", nature="API Management", real=60, tl=66.7, bo=100, br=66, target="31 Jul 2026", orig="", owner="Digital Business / Technology / Credit Card", pm="Yudi Y / Bowie / David B / Donny A", phase="UAT API On-Boarding; instalasi & assessment API Savings (22 API).", next="Pentest; tuning server; daftar SNAP BI.", risk="Penjadwalan Pentest menyebabkan delivery mundur 1 pekan.", stop="Kesalahan UAT (Des'25); assessment (Mar'26); dokumen (Mei'26).", reco="Percepatan rekomendasi ASPI & izin paralel."),
    dict(sort=3, name="Konversi Valas ke Rupiah", group="Business", status="In-Progress", nature="FX Conversion", real=93, tl=100, bo=None, br=None, target="04 Jun 2026", orig="31 Mar'26", owner="Treasury", pm="Aditya Fatur / Purbayu", phase="Deploy to Production 30 Apr'26; issue rekonsiliasi & spread harga.", next="Dokumen pelaporan OJK & BI; rekonsiliasi.", risk="Dokumen ke regulator & BI belum disiapkan.", stop="—", reco="Mendorong kesiapan dokumen ke regulator."),
    dict(sort=4, name="Dormant Account Classification", group="Business", status="In-Progress", nature="Core Banking", real=93, tl=100, bo=100, br=55, target="19 Jun 2026", orig="01 Mei'26", owner="Liabilities Product Development Group", pm="Yani / Naufal / Imelda / Vita", phase="SIT selesai; UAT tertunda (Dev environment dipakai Digital s/d 11 Jun).", next="Rekening saldo 0 ditutup otomatis; finalisasi timeline Silverlake.", risk="UAT belum jalan akibat sharing resource.", stop="—", reco="Monitor timeline keseluruhan dengan Silverlake."),
    dict(sort=5, name="Data Center Migration", group="Non-Business", status="In-Progress", nature="Infrastructure", real=95, tl=100, bo=100, br=88, target="25 Jun 2026", orig="30 Apr'26", owner="Technology Dir.", pm="Yudi Y / Irfan Rifai / Bowie", phase="Relokasi koneksi & perangkat dari MNC Tower Lt4; menunggu Telkom.", next="Percepatan procurement & PO.", risk="Proses Telkom belum dapat dimonitor.", stop="—", reco="Komunikasi intensif dengan Telkom."),
    dict(sort=6, name="Fraud Detection System (FDS)", group="Non-Business", status="In-Progress", nature="Fraud Detection", real=15, tl=15.62, bo=100, br=55, target="16 Jan 2027", orig="", owner="Risk Management Group", pm="Reza / Khabi / Michael Satrio", phase="Finalisasi Field Mapping & Table Reference [03–05 Jun'26].", next="Formulasi TSD & FSD; diskusi Branch Field Mapping.", risk="Risiko keterlambatan diskusi Table Activity; investigasi PTAP.", stop="Finalisasi PKS oleh RMG; GBG menunggu Predator Config.", reco="Monitoring agar timeline on-track."),
    dict(sort=7, name="OPICS", group="Non-Business", status="In-Progress", nature="Treasury System", real=95, tl=100, bo=100, br=74, target="W1 Jun 2026", orig="02 Apr", owner="Treasury Group", pm="Vicco / Purbayu / Ananda Dessi", phase="Validasi & compile skenario 8 Jun; migrasi 09–12 Jun 2026.", next="Input transaksi; verify; migrasi & upgrade OPICS & GRIT.", risk="Potensi selisih pembukuan saat parallel run.", stop="Error BSIP saat EOD UAT (30 Apr) masih investigasi PTAP.", reco="Monitoring hasil test rutin."),
    dict(sort=8, name="Enhancement RTGS", group="Non-Business", status="Completed", nature="Automation", real=100, tl=100, bo=100, br=88, target="05 May 2026", orig="30 Apr", owner="Digital Business / IT Technology", pm="Bowie / Rina M", phase="RTGS naik production; re-deploy job handler 05 Mei.", next="Monitoring.", risk="Data cleansing mungkin tidak signifikan turunkan CPU.", stop="CPU tinggi akibat junk data 2025.", reco="—"),
    dict(sort=9, name="QRIS CPM", group="Non-Business", status="In-Progress", nature="QRIS", real=75, tl=100, bo=None, br=None, target="W2 Jun 2026", orig="", owner="Digital Business Group", pm="Aditya Fatur / Bowie", phase="Progress SIT; perlu Pentest & audit eksternal.", next="Go-Live W2 Juni.", risk="Perlu persiapan dokumen ke regulator.", stop="—", reco="Percepatan ke ASPI/OJK/BI."),
    dict(sort=10, name="QRIS Credit Card", group="Non-Business", status="In-Progress", nature="QRIS", real=75, tl=75, bo=None, br=None, target="W4 Jun 2026", orig="", owner="Credit Card Group", pm="Bowie", phase="Done development Ascend; progress SIT.", next="Go-Live W2 Juni.", risk="Belum siap dokumen ASPI; Pentest belum dijadwalkan.", stop="—", reco="Percepatan ke regulator."),
    dict(sort=11, name="EOD 24/7 (Night Mode)", group="Non-Business", status="In-Progress", nature="Core Banking", real=5, tl=4, bo=None, br=None, target="10 Oct 2026", orig="", owner="IT Group / Digital Business", pm="Aditya Fatur / Naufal", phase="Kick-off 14 Mei; development Silverlake sejak 18 Mei.", next="Penyusunan BRD; Core Development.", risk="—", stop="—", reco="—"),
]


def main():
    email = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EMAIL
    password = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PASSWORD

    Base.metadata.create_all(engine)
    print("Tables created.")

    # --- lightweight migration for upgrades from v1 ---
    # create_all() adds NEW tables (audit_log) but won't add the `role`
    # column to an existing v1 `users` table, so add it if missing.
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'viewer'"))
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT now()"))
    print("Schema up to date (columns ensured).")

    with Session() as s:
        # admin user (upsert by email)
        user = s.scalar(select(User).where(User.email == email.lower()))
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        if user:
            user.pw_hash = pw_hash
            user.role = "admin"
            print(f"Updated password for {email} (role: admin)")
        else:
            s.add(User(email=email.lower(), pw_hash=pw_hash, role="admin"))
            print(f"Created admin user {email} (role: admin)")
        s.commit()

        # seed projects only if empty
        count = s.scalar(select(func.count(Project.id)))
        if count == 0:
            for row in SEED:
                s.add(Project(**row))
            s.commit()
            print(f"Seeded {len(SEED)} projects.")
        else:
            print(f"Projects table already has {count} rows — not seeding.")

        # seed people tables only if empty
        tr_count = s.scalar(select(func.count(PeopleTraining.id)))
        if tr_count == 0:
            for row in PEOPLE_TRAININGS:
                s.add(PeopleTraining(**row))
            s.flush()  # get IDs before seeding evaluations
            # evaluations reference training IDs 1..5 by insertion order
            all_tr = s.scalars(select(PeopleTraining).order_by(PeopleTraining.id)).all()
            id_map = {i+1: t.id for i, t in enumerate(all_tr)}
            for row in PEOPLE_EVALS:
                ev = dict(row)
                ev["training_id"] = id_map.get(ev["training_id"], ev["training_id"])
                s.add(PeopleEvaluation(**ev))
            for row in PEOPLE_CERTS:
                s.add(PeopleCertification(**row))
            s.commit()
            print(f"Seeded {len(PEOPLE_TRAININGS)} trainings, {len(PEOPLE_EVALS)} evaluations, "
                  f"{len(PEOPLE_CERTS)} certifications.")
        else:
            print(f"People tables already have {tr_count} training rows — not seeding.")

    print("\nDone. Start the server with:  python app.py")
    print(f"Login with: {email} / {password}")


if __name__ == "__main__":
    main()
