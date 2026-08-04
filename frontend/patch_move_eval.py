import time, shutil
p = "people.html"
s = open(p, encoding="utf-8").read()
bak = p + ".bak-moveeval-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copy(p, bak)

# 1. extract Evaluations section from PD tab (ASCII anchors)
i = s.index("<!-- Evaluations -->"); i = s.rindex("\n", 0, i) + 1
j = s.index("<!-- Ikatan Dinas -->"); j = s.rindex("\n", 0, j) + 1
eval_block = s[i:j]
assert "pd-fc-bottom" in eval_block, "eval block extraction failed"
s = s[:i] + s[j:]

# 2. insert into Evaluation Results tab, after the table
a0 = s.index('<tbody id="ev-tbody"></tbody>')
close = s.index("\n    </div>", a0)
s = s[:close+1] + eval_block + s[close+1:]

# 3. strip eval fetch+render from loadPdAnalytics (slice over unicode region)
a = s.index("const [evR, idR] = await Promise.all([")
b = s.index("const ik = id.kpis;")
repl = ("const idR = await fetch('/api/people/pd/ikatan-dinas/analytics', { headers: authHdr() });\n"
        "    if (!idR.ok) throw new Error('analytics fetch failed');\n"
        "    const id = await idR.json();\n\n"
        "    // Ikatan Dinas\n"
        "    ")
s = s[:a] + repl + s[b:]

# 4. point loadPdAnalytics catch fallback at the PD tab (pd-id-kpis)
s = s.replace("getElementById('pd-ev-kpis')", "getElementById('pd-id-kpis')", 1)

NEW = '''let evalAnalyticsLoaded = false;
async function loadEvalAnalytics() {
  if (evalAnalyticsLoaded) return;
  evalAnalyticsLoaded = true;
  try {
    const evR = await fetch('/api/people/pd/evaluate/analytics', { headers: authHdr() });
    if (!evR.ok) throw new Error('eval analytics fetch failed');
    const ev = await evR.json();
    document.getElementById('pd-ev-kpis').innerHTML =
        kpiCard('blue',  'Events Evaluated', fmtNum(ev.event.count),              'programs with feedback') +
        kpiCard('green', 'Event Avg',        ev.event.overall_avg ?? '\\u2014',    'out of 5.0') +
        kpiCard('teal',  'Facilitators',     fmtNum(ev.facilitator.facilitators), 'distinct facilitators') +
        kpiCard('orange','Facilitator Avg',  ev.facilitator.overall_avg ?? '\\u2014', 'out of 5.0');
    const dimItems = o => Object.entries(o).map(([k2, v]) => ({ label: k2.replace(/_/g, ' '), value: v }));
    renderBars('pd-ev-dim', dimItems(ev.event.by_dimension),       'teal', v => v == null ? '\\u2014' : Number(v).toFixed(2));
    renderBars('pd-fc-dim', dimItems(ev.facilitator.by_dimension), 'blue', v => v == null ? '\\u2014' : Number(v).toFixed(2));
    renderRank('pd-fc-top',    ev.facilitator.top);
    renderRank('pd-fc-bottom', ev.facilitator.bottom);
  } catch (e) {
    console.error('loadEvalAnalytics error:', e);
    evalAnalyticsLoaded = false;
    document.getElementById('pd-ev-kpis').innerHTML =
      '<div class="no-data" style="flex:1 1 100%">Failed to load evaluation analytics. Reopen the tab to retry.</div>';
  }
}

'''
s = s.replace("let pdLoaded = false;", NEW + "let pdLoaded = false;", 1)

s = s.replace(
  "if (tab === 'pd') loadPdAnalytics();   // lazy-load on first open",
  "if (tab === 'pd') loadPdAnalytics();   // lazy-load on first open\n    if (tab === 'evaluation') loadEvalAnalytics();",
  1)

open(p, "w", encoding="utf-8").write(s)
print("OK: moved Evaluations section into the Evaluation Results tab")
print("Backup:", bak)
