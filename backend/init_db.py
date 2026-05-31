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
from app import Base, engine, Session, User, Project

DEFAULT_EMAIL = "admin@mncbank.co.id"
DEFAULT_PASSWORD = "pmo2026"   # change this — or pass args

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

    print("\nDone. Start the server with:  python app.py")
    print(f"Login with: {email} / {password}")


if __name__ == "__main__":
    main()
