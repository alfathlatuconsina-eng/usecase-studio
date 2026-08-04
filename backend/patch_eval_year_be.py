import time, shutil
p = "app.py"
s = open(p, encoding="utf-8").read()
bak = p + ".bak-evyear-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copy(p, bak)

def rep(old, new):
    global s
    assert old in s, "NOT FOUND: " + old[:60]
    s = s.replace(old, new, 1)

rep("    E, F = PdEvaluateEvent, PdEvaluateFacilitator\n",
    "    E, F = PdEvaluateEvent, PdEvaluateFacilitator\n"
    "    f_year = (request.args.get('year') or '').strip()\n"
    "    ce = [func.substr(E.start_date, 1, 4) == f_year] if f_year else []\n"
    "    cf = [func.substr(F.start_date, 1, 4) == f_year] if f_year else []\n")

rep("        ev_count = s.scalar(select(func.count()).select_from(E))\n",
    "        ev_count = s.scalar(select(func.count()).select_from(E).where(*ce))\n")

rep("        ev_avgs = s.execute(select(*[func.avg(c) for _, c in EVENT_DIMS])).one()\n",
    "        ev_avgs = s.execute(select(*[func.avg(c) for _, c in EVENT_DIMS]).where(*ce)).one()\n")

rep("        fc_count = s.scalar(select(func.count()).select_from(F))\n",
    "        fc_count = s.scalar(select(func.count()).select_from(F).where(*cf))\n")

rep("        fc_distinct = s.scalar(select(func.count(func.distinct(F.facilitator_nip)))\n"
    "                               .where(F.facilitator_nip != \"\"))\n",
    "        fc_distinct = s.scalar(select(func.count(func.distinct(F.facilitator_nip)))\n"
    "                               .where(F.facilitator_nip != \"\", *cf))\n")

rep("        fc_avgs = s.execute(select(*[func.avg(c) for _, c in FAC_DIMS])).one()\n",
    "        fc_avgs = s.execute(select(*[func.avg(c) for _, c in FAC_DIMS]).where(*cf)).one()\n")

rep("            .where(F.facilitator_nip != \"\")\n"
    "            .group_by(F.facilitator_nip, F.facilitator_name)\n",
    "            .where(F.facilitator_nip != \"\", *cf)\n"
    "            .group_by(F.facilitator_nip, F.facilitator_name)\n")

rep("        ranked.sort(key=lambda x: x[\"avg_score\"], reverse=True)\n",
    "        ranked.sort(key=lambda x: x[\"avg_score\"], reverse=True)\n\n"
    "        _yrs = set()\n"
    "        for col in (E.start_date, F.start_date):\n"
    "            _yrs |= {r[0] for r in s.execute(\n"
    "                select(func.substr(col, 1, 4)).where(col != \"\").distinct()).all()}\n"
    "        opt_years = sorted((y for y in _yrs if y and y.strip()), reverse=True)\n")

rep("                \"bottom\": ranked[-10:][::-1] if len(ranked) > 10 else [],\n"
    "            },\n"
    "        })\n",
    "                \"bottom\": ranked[-10:][::-1] if len(ranked) > 10 else [],\n"
    "            },\n"
    "            \"filters\": {\"applied\": {\"year\": f_year}, \"years\": opt_years},\n"
    "        })\n")

open(p, "w", encoding="utf-8").write(s)
print("OK: backend eval year filter applied")
print("Backup:", bak)
PYEOFcat >> /opt/pmo/backend/patch_eval_year_be.py <<'PYEOF'

rep("        fc_distinct = s.scalar(select(func.count(func.distinct(F.facilitator_nip)))\n"
    "                               .where(F.facilitator_nip != \"\"))\n",
    "        fc_distinct = s.scalar(select(func.count(func.distinct(F.facilitator_nip)))\n"
    "                               .where(F.facilitator_nip != \"\", *cf))\n")

rep("        fc_avgs = s.execute(select(*[func.avg(c) for _, c in FAC_DIMS])).one()\n",
    "        fc_avgs = s.execute(select(*[func.avg(c) for _, c in FAC_DIMS]).where(*cf)).one()\n")

rep("            .where(F.facilitator_nip != \"\")\n"
    "            .group_by(F.facilitator_nip, F.facilitator_name)\n",
    "            .where(F.facilitator_nip != \"\", *cf)\n"
    "            .group_by(F.facilitator_nip, F.facilitator_name)\n")

rep("        ranked.sort(key=lambda x: x[\"avg_score\"], reverse=True)\n",
    "        ranked.sort(key=lambda x: x[\"avg_score\"], reverse=True)\n\n"
    "        _yrs = set()\n"
    "        for col in (E.start_date, F.start_date):\n"
    "            _yrs |= {r[0] for r in s.execute(\n"
    "                select(func.substr(col, 1, 4)).where(col != \"\").distinct()).all()}\n"
    "        opt_years = sorted((y for y in _yrs if y and y.strip()), reverse=True)\n")

rep("                \"bottom\": ranked[-10:][::-1] if len(ranked) > 10 else [],\n"
    "            },\n"
    "        })\n",
    "                \"bottom\": ranked[-10:][::-1] if len(ranked) > 10 else [],\n"
    "            },\n"
    "            \"filters\": {\"applied\": {\"year\": f_year}, \"years\": opt_years},\n"
    "        })\n")

open(p, "w", encoding="utf-8").write(s)
print("OK: backend eval year filter applied")
print("Backup:", bak)
