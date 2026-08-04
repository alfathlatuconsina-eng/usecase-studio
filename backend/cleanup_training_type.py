import sys, time, csv
from app import Session, PdTraining
from sqlalchemy import select, update, func

MAP = {
    "Aritificial Intelligence": "Artificial Intelligence",
    "Branch Operation": "Branch Operations",
    "Cybersecurity": "Cyber Security",
    "Human Resource": "Human Resources",
    "Induction Retail Funding Officer": "Induction Retail Funding Officer (RFO)",
    "Industrial Relation": "Industrial Relations",
    "NEOP": "New Employee Orientation Program (NEOP)",
    "Negotiaion Skill": "Negotiation Skills",
    "Negotiation Skill": "Negotiation Skills",
    "Learning Development": "Learning & Development",
    "Presentation skill": "Presentation Skill",
    "Product knowledge": "Product Knowledge",
    "TASPEN": "Taspen",
    "Sertifikasi Frontliner": "Sertifikasi Frontliners",
    "Microsoft Power Business Intelligence": "Microsoft Power BI",
    "IT & Programming": "IT Programming",
    "APU & PPT": "APU PPT",
    "Anti Pencucian Uang dan Pencegahan Pendanaan Terorisme (APU PPT)": "APU PPT",
    "AML": "APU PPT",
    "GRC": "Governance, Risk and Compliance (GRC)",
    "SMR": "Sertifikasi Manajemen Risiko",
    "Pajak": "Perpajakan",
    "Taxation": "Perpajakan",
    "Transaksi Valas": "Transaksi Valuta Asing",
}

T = PdTraining
commit = "--commit" in sys.argv[1:]
with Session() as s:
    print("=== normalize training_type (%s) ===" % ("COMMIT" if commit else "PREVIEW"))
    total = 0
    for old, new in sorted(MAP.items()):
        n = s.execute(select(func.count()).where(T.training_type == old)).scalar()
        total += n
        print("  %5d  %-55s -> %s" % (n, old, new))
    print("  ----- %d rows / %d labels" % (total, len(MAP)))
    if not commit:
        print("PREVIEW only. Re-run with --commit to apply.")
        sys.exit(0)
    ts = time.strftime("%Y%m%d-%H%M%S")
    bak = "/tmp/training_type_backup_%s.csv" % ts
    rows = s.execute(select(T.id, T.training_type).where(T.training_type.in_(list(MAP.keys())))).all()
    with open(bak, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["id", "old"]); w.writerows(rows)
    print("Backup:", bak, "(%d rows)" % len(rows))
    changed = 0
    for old, new in MAP.items():
        changed += s.execute(update(T).where(T.training_type == old).values(training_type=new)).rowcount or 0
    s.commit()
    print("Done. Updated %d rows." % changed)
    d = s.execute(select(func.count(func.distinct(T.training_type))).where(T.training_type != "")).scalar()
    print("Distinct now:", d)
