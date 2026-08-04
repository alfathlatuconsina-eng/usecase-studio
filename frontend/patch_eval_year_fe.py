import time, shutil
p = "people.html"
s = open(p, encoding="utf-8").read()
bak = p + ".bak-evyear-" + time.strftime("%Y%m%d-%H%M%S")
shutil.copy(p, bak)

old1 = '        <div class="cards" id="pd-ev-kpis"></div>\n'
bar = ('        <div class="toolbar" id="pd-ev-filters" style="margin-bottom:14px">\n'
       '          <select id="pd-ev-f-year" onchange="loadEvalAnalytics(true)"><option value="">All Years</option></select>\n'
       '          <button class="btn-add" style="margin-left:auto;background:var(--gray-line);color:var(--text)" onclick="document.getElementById(\'pd-ev-f-year\').value=\'\';loadEvalAnalytics(true)">Reset</button>\n'
       '        </div>\n')
assert old1 in s, "pd-ev-kpis div not found"
s = s.replace(old1, bar + old1, 1)

old2 = ("async function loadEvalAnalytics() {\n"
        "  if (evalAnalyticsLoaded) return;\n"
        "  evalAnalyticsLoaded = true;\n"
        "  try {\n"
        "    const evR = await fetch('/api/people/pd/evaluate/analytics', { headers: authHdr() });\n"
        "    if (!evR.ok) throw new Error('eval analytics fetch failed');\n"
        "    const ev = await evR.json();\n")
new2 = ("async function loadEvalAnalytics(force) {\n"
        "  if (evalAnalyticsLoaded && !force) return;\n"
        "  evalAnalyticsLoaded = true;\n"
        "  try {\n"
        "    const _y = (document.getElementById('pd-ev-f-year') || {}).value || '';\n"
        "    const _qs = _y ? ('?year=' + encodeURIComponent(_y)) : '';\n"
        "    const evR = await fetch('/api/people/pd/evaluate/analytics' + _qs, { headers: authHdr() });\n"
        "    if (!evR.ok) throw new Error('eval analytics fetch failed');\n"
        "    const ev = await evR.json();\n"
        "    if (ev.filters) {\n"
        "      const _sel = document.getElementById('pd-ev-f-year');\n"
        "      if (_sel && !_sel.dataset.filled) {\n"
        "        _sel.dataset.filled = '1';\n"
        "        ev.filters.years.forEach(yr => { const o = document.createElement('option'); o.value = yr; o.textContent = yr; _sel.appendChild(o); });\n"
        "        _sel.value = ev.filters.applied.year || '';\n"
        "      }\n"
        "    }\n")
assert old2 in s, "loadEvalAnalytics signature not found"
s = s.replace(old2, new2, 1)

open(p, "w", encoding="utf-8").write(s)
print("OK: frontend eval year filter applied")
print("Backup:", bak)
