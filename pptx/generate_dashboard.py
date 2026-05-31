#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
 PMO DASHBOARD GENERATOR  —  MNC Bank
==============================================================================
 Reads a single Excel workbook (PMO_Dashboard_Input.xlsx) and regenerates the
 PowerPoint dashboard by CLONING the branded template (Dashboard_Template.pptx).

 You never edit PowerPoint by hand. Edit Excel, run this, get a fresh .pptx.

 HOW IT WORKS
 ------------
 The template deck already contains your MNC Bank branding, logo, fonts,
 background images, gauges, timeline graphics and native charts. This script
 keeps all of that and only:
   * updates the two SUMMARY bar charts (Business / Non-Business)
   * for every project, clones the matching 2-slide pair from the template
     and swaps the text + chart values with your Excel data.

 Run:   python generate_dashboard.py
 Output: 01a. PMO Dashboard - <today>.pptx
==============================================================================
"""

import copy
import datetime as _dt
import os
import sys

try:
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
except ImportError:
    sys.exit("Missing python-pptx.  Install with:  pip install python-pptx openpyxl")

try:
    import openpyxl  # noqa: F401  (used indirectly + validated here)
except ImportError:
    sys.exit("Missing openpyxl.  Install with:  pip install python-pptx openpyxl")


# ---------------------------------------------------------------------------
# CONFIG — file names (kept relative so the whole folder is portable)
# ---------------------------------------------------------------------------
def _find_input():
    """Prefer the macro-enabled .xlsm if present, else the .xlsx."""
    for name in ("PMO_Dashboard_Input.xlsm", "PMO_Dashboard_Input.xlsx"):
        cand = os.path.join(HERE, name)
        if os.path.exists(cand):
            return cand
    return os.path.join(HERE, "PMO_Dashboard_Input.xlsx")  # default for error msg


HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "Dashboard_Template.pptx")
EXCEL = None  # resolved at build()-time via _find_input()
TODAY = _dt.date.today().strftime("%d %b %Y")
OUTPUT = os.path.join(HERE, f"01a. PMO Dashboard - {TODAY}.pptx")

# Template slide indices (0-based) that act as PATTERNS to clone.
# Derived from your Dashboard_Sample.pptx:
TPL_SUMMARY_BUSINESS = 0      # slide 1  – business summary bar chart
TPL_SUMMARY_NONBUS = 1        # slide 2  – non-business summary bar chart
TPL_SECTION_DIVIDER = 2       # slide 3  – "Business Projects" section divider
TPL_PROJECT_TITLE = 3         # slide 4  – "Projects Update / <name>" title
TPL_PROJECT_DETAIL = 4        # slide 5  – gauge + about/status/recommendation
TPL_PROJECT_CHARTS = 5        # slide 6  – timeline & budget bar charts + risk/stopper


# ===========================================================================
# Excel reading
# ===========================================================================
def read_projects(path):
    """Read the 'Projects' sheet into a list of dict rows (header-keyed)."""
    wb = openpyxl.load_workbook(path, data_only=True)
    if "Projects" not in wb.sheetnames:
        sys.exit("Excel must contain a sheet named 'Projects'.")
    ws = wb["Projects"]
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        sys.exit("'Projects' sheet is empty.")
    headers = [str(h).strip() if h is not None else "" for h in rows[0]]
    out = []
    for r in rows[1:]:
        if r is None or all(c is None for c in r):
            continue
        rec = {headers[i]: r[i] for i in range(len(headers))}
        if not str(rec.get("Project Name", "")).strip():
            continue
        out.append(rec)
    return out


def read_meta(path):
    """Read the 'Settings' sheet (key/value) for the update date label etc."""
    wb = openpyxl.load_workbook(path, data_only=True)
    meta = {"Update Label": f"(Update {TODAY})"}
    if "Settings" in wb.sheetnames:
        for k, v in wb["Settings"].iter_rows(values_only=True):
            if k:
                meta[str(k).strip()] = "" if v is None else str(v)
    return meta


def pct(v):
    """Normalise a percentage cell to a 0..1 float for charts. Accepts 91, 0.91, '91%'."""
    if v is None or v == "":
        return None
    if isinstance(v, str):
        v = v.replace("%", "").strip()
    f = float(v)
    return f / 100.0 if f > 1.0 else f


def as_int_pct(v):
    """Return integer percent for text labels (e.g. 91)."""
    p = pct(v)
    return None if p is None else round(p * 100)


# ===========================================================================
# Slide cloning (python-pptx has no public clone; we deep-copy the XML)
# ===========================================================================
def clone_slide(prs, src_slide):
    """Append a deep copy of src_slide to prs and return the new slide.

    Each cloned shape's relationship ids (images, charts) are re-pointed to the
    new slide's own relationships. Chart parts are SHARED with the template and
    their cached values are edited later via direct XML (see set_bar_values),
    which sidesteps python-pptx's embedded-workbook handling entirely — your
    template's charts link their data externally, so replace_data() cannot be
    used. To keep each project's chart independent we deep-copy the chart PART
    so editing one slide's cache never changes another's."""
    new_slide = prs.slides.add_slide(src_slide.slide_layout)
    for shp in list(new_slide.shapes):
        shp._element.getparent().remove(shp._element)

    src_part = src_slide.part
    new_part = new_slide.part

    for shp in src_slide.shapes:
        el = copy.deepcopy(shp._element)
        _rewire_rels(el, shp._element, src_part, new_part)
        new_slide.shapes._spTree.append(el)
    return new_slide


def _rewire_rels(new_el, src_el, src_part, new_part):
    from pptx.oxml.ns import qn
    R_EMBED, R_ID, R_LINK = qn("r:embed"), qn("r:id"), qn("r:link")
    for src_node, new_node in zip(src_el.iter(), new_el.iter()):
        for attr in (R_EMBED, R_ID, R_LINK):
            rid = src_node.get(attr)
            if not rid:
                continue
            try:
                rel = src_part.rels[rid]
            except KeyError:
                continue
            if rel.is_external:
                new_rid = new_part.rels.get_or_add_ext_rel(rel.reltype, rel.target_ref)
            else:
                target = rel.target_part
                if "chart" in rel.reltype:
                    target = _clone_chart_part(target)
                new_rid = new_part.relate_to(target, rel.reltype)
            new_node.set(attr, new_rid)


_CHART_CLONE_N = [0]


def _clone_chart_part(chart_part):
    """Make an independent copy of a chart part by creating a fresh ChartPart
    whose XML is a deep copy of the source chart's XML. We deliberately avoid
    deepcopy on the part object itself (it drags the whole package graph and
    blows up memory). Child rels (style, colors, external data link) are
    re-related to the same targets."""
    from pptx.opc.packuri import PackURI
    from pptx.parts.chart import ChartPart
    pkg = chart_part.package
    _CHART_CLONE_N[0] += 1
    uri = PackURI("/ppt/charts/chartClone%d.xml" % _CHART_CLONE_N[0])

    new_xml = copy.deepcopy(chart_part._element)
    new_part = ChartPart(uri, chart_part.content_type, pkg, element=new_xml)

    for rid, rel in list(chart_part.rels.items()):
        if rel.is_external:
            new_part.rels.get_or_add_ext_rel(rel.reltype, rel.target_ref)
        else:
            new_part.relate_to(rel.target_part, rel.reltype)
    return new_part


# ===========================================================================
# Text replacement inside a slide
# ===========================================================================
def replace_block(shape, new_text):
    """Replace the entire text of a text-frame shape, preserving the format
    of its first run/paragraph as much as possible."""
    if not shape.has_text_frame:
        return
    tf = shape.text_frame
    lines = str(new_text).split("\n")
    # keep first paragraph's run formatting; rewrite text
    first_p = tf.paragraphs[0]
    # clear extra paragraphs
    for p in tf.paragraphs[1:]:
        p._p.getparent().remove(p._p)
    # set first line
    if first_p.runs:
        first_p.runs[0].text = lines[0]
        for extra in first_p.runs[1:]:
            extra.text = ""
    else:
        first_p.add_run().text = lines[0]
    # add remaining lines as new paragraphs cloned from the first
    for ln in lines[1:]:
        np = copy.deepcopy(first_p._p)
        first_p._p.addnext(np)
        # rewrite text of the cloned paragraph
        from pptx.text.text import _Paragraph
        para = _Paragraph(np, first_p._parent)
        if para.runs:
            para.runs[0].text = ln
            for extra in para.runs[1:]:
                extra.text = ""
        else:
            para.add_run().text = ln
        first_p = para  # chain


def find_shape_by_text(slide, contains):
    for sh in slide.shapes:
        if sh.has_text_frame and contains.lower() in sh.text_frame.text.lower():
            return sh
    return None


def _chart_series(chart):
    """Return list of (name, [value-<c:v>-elements]) for each series, by XML."""
    from pptx.oxml.ns import qn
    cs = chart._chartSpace
    out = []
    for ser in cs.findall(".//" + qn("c:ser")):
        nm_el = ser.find(".//" + qn("c:tx") + "//" + qn("c:v"))
        name = nm_el.text if nm_el is not None else ""
        v_els = ser.findall(".//" + qn("c:val") + "//" + qn("c:pt") + "/" + qn("c:v"))
        out.append((name, v_els))
    return out


def _set_series_value(chart, series_name_contains, new_value):
    """Set the single cached value of the series whose name matches. Works on
    charts with externally-linked workbooks (edits the numeric cache directly)."""
    for name, v_els in _chart_series(chart):
        if series_name_contains.lower() in (name or "").lower() and v_els:
            v_els[0].text = repr(float(new_value))
            return True
    return False


def set_two_series_bar(chart, realization, original, real_name, orig_name):
    """Update a timeline/budget two-series single-point bar chart in place."""
    _set_series_value(chart, orig_name, original)
    _set_series_value(chart, real_name, realization)


def set_summary_bar(chart, names, realizations, timelines):
    """Rewrite a multi-category summary bar chart's category labels and the two
    series caches via direct XML, matching the template's category count."""
    from pptx.oxml.ns import qn
    cs = chart._chartSpace
    # categories: update string cache pts on the first series' cat (shared cache)
    for ser in cs.findall(".//" + qn("c:ser")):
        cat = ser.find(".//" + qn("c:cat"))
        if cat is not None:
            pts = cat.findall(".//" + qn("c:pt") + "/" + qn("c:v"))
            for i, pt in enumerate(pts):
                if i < len(names):
                    pt.text = str(names[i])
    # series values
    sers = _chart_series(chart)
    for name, v_els in sers:
        vals = realizations if "realization" in name.lower() else timelines
        for i, v in enumerate(v_els):
            if i < len(vals):
                v.text = repr(float(vals[i]))


# ===========================================================================
# Build
# ===========================================================================
def build():
    global EXCEL
    EXCEL = _find_input()
    if not os.path.exists(TEMPLATE):
        sys.exit(f"Template not found: {TEMPLATE}")
    if not os.path.exists(EXCEL):
        sys.exit(f"Excel input not found: {EXCEL}")

    projects = read_projects(EXCEL)
    meta = read_meta(EXCEL)
    update_label = meta.get("Update Label", f"(Update {TODAY})")

    prs = Presentation(TEMPLATE)

    # --- capture template pattern slides BEFORE we start appending ---
    tpl_summary_bus = prs.slides[TPL_SUMMARY_BUSINESS]
    tpl_summary_non = prs.slides[TPL_SUMMARY_NONBUS]
    tpl_divider = prs.slides[TPL_SECTION_DIVIDER]
    tpl_title = prs.slides[TPL_PROJECT_TITLE]
    tpl_detail = prs.slides[TPL_PROJECT_DETAIL]
    tpl_charts = prs.slides[TPL_PROJECT_CHARTS]

    business = [p for p in projects if str(p.get("Group", "")).strip().lower().startswith("bus")]
    nonbus = [p for p in projects if not str(p.get("Group", "")).strip().lower().startswith("bus")]

    # ---- 1. update the two summary charts in place ----
    _update_summary(tpl_summary_bus, business, update_label)
    _update_summary(tpl_summary_non, nonbus, update_label)

    # ---- 2. clone divider + project pairs for each group ----
    # (we clone divider/title/detail/charts so the originals stay as patterns;
    #  but slides 3-6 ARE QRIS already, so we will rebuild the project area)
    # Strategy: keep slides 1 & 2 (summaries). Delete templated project slides
    # 3..end, then rebuild from scratch by cloning the patterns we captured.
    _delete_from_index(prs, TPL_SECTION_DIVIDER)  # removes slides 3..N

    for grp_name, grp in (("Business Projects", business), ("Non Business Projects", nonbus)):
        if not grp:
            continue
        div = clone_slide(prs, tpl_divider)
        _set_divider_title(div, grp_name)
        for proj in grp:
            t = clone_slide(prs, tpl_title)
            _fill_title(t, proj)
            d = clone_slide(prs, tpl_detail)
            _fill_detail(d, proj)
            c = clone_slide(prs, tpl_charts)
            _fill_charts(c, proj)

    prs.save(OUTPUT)
    print(f"OK  ->  {OUTPUT}")
    print(f"     {len(business)} business + {len(nonbus)} non-business projects")


def _delete_from_index(prs, start_idx):
    """Remove all slides from start_idx (0-based) to the end — both the entries
    in the slide id list AND the underlying slide parts, so their partnames
    (slide6.xml ...) are freed and cloned slides don't collide."""
    from pptx.oxml.ns import qn
    xml_slides = prs.slides._sldIdLst
    slide_ids = list(xml_slides)
    pres_part = prs.part
    for sid in slide_ids[start_idx:]:
        rId = sid.get(qn("r:id"))
        try:
            pres_part.drop_rel(rId)
        except Exception:
            pass
        xml_slides.remove(sid)


def _update_summary(slide, group, update_label):
    names = [p["Project Name"] for p in group]
    reals = [pct(p.get("Realization %")) or 0 for p in group]
    times = [pct(p.get("Targeted Timeline %")) or 0 for p in group]
    for sh in slide.shapes:
        if sh.has_chart and sh.chart.chart_type.name == "BAR_CLUSTERED":
            set_summary_bar(sh.chart, names, reals, times)
    # Update the dated subtitle only — match a shape that already starts with
    # "(Update" so we never clobber the main "Project Management Dashboard" title.
    for sh in slide.shapes:
        if sh.has_text_frame:
            txt = sh.text_frame.text.strip()
            if txt.lower().startswith("(update"):
                replace_block(sh, update_label)
                break


def _set_divider_title(slide, title):
    # divider's main title text shape
    best = None
    for sh in slide.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip():
            if best is None or len(sh.text_frame.text) < len(best.text_frame.text):
                best = sh
    # pick the shape whose text looks like a section title
    target = find_shape_by_text(slide, "Business") or best
    if target:
        replace_block(target, title)


def _fill_title(slide, p):
    t = find_shape_by_text(slide, "QRIS Acquiring")
    if not t:
        # fallback: the longest non-"Projects Update" text
        for sh in slide.shapes:
            if sh.has_text_frame and "projects update" not in sh.text_frame.text.lower() \
               and sh.text_frame.text.strip():
                t = sh
    if t:
        replace_block(t, p["Project Name"])


def _fill_detail(slide, p):
    # gauge needle (doughnut "Pointer" series): map realization 0..100 onto the
    # half-circle. Template uses [first, 3, 197-first] summing to 200.
    real = as_int_pct(p.get("Realization %")) or 0
    first = max(0, min(197, round(real * 1.97)))
    for sh in slide.shapes:
        if sh.has_chart and sh.chart.chart_type.name == "DOUGHNUT":
            from pptx.oxml.ns import qn
            for ser in sh.chart._chartSpace.findall(".//" + qn("c:ser")):
                nm = ser.find(".//" + qn("c:tx") + "//" + qn("c:v"))
                if nm is not None and "pointer" in (nm.text or "").lower():
                    vs = ser.findall(".//" + qn("c:val") + "//" + qn("c:pt") + "/" + qn("c:v"))
                    if len(vs) >= 3:
                        vs[0].text = str(first)
                        vs[1].text = "3"
                        vs[2].text = str(197 - first)

    mapping = {
        "Project : QRIS Acquiring": f"Project : {p['Project Name']}",
        "Realization:\n91%": f"Realization:\n{as_int_pct(p.get('Realization %')) or 0}%",
        "Project Nature": _kv("Project Nature", p.get("Project Nature")),
        "Ownership": _kv("Ownership", p.get("Ownership")),
        "Targeted/Aim": _kv("Targeted/Aim", p.get("Targeted Aim")),
        "Targeted Fulfilment": _fulfilment(p),
        "Background :": _about_block(p),
        "Current Phase :": _status_block(p),
        "Issues at Hand :": _reco_block(p),
    }
    for needle, value in mapping.items():
        sh = find_shape_by_text(slide, needle)
        if sh and value is not None:
            replace_block(sh, value)


def _fill_charts(slide, p):
    # title
    title = find_shape_by_text(slide, "Update Status")
    if title:
        replace_block(title, f"Update Status – {p['Project Name']}")
    # charts: there are two BAR_CLUSTERED — timeline (first) & budget (second)
    bar_charts = [sh for sh in slide.shapes
                  if sh.has_chart and sh.chart.chart_type.name == "BAR_CLUSTERED"]
    real_t = pct(p.get("Realization %")) or 0
    orig_t = pct(p.get("Targeted Timeline %")) or 1.0
    real_b = pct(p.get("Budget Realization %"))
    orig_b = pct(p.get("Budget Original %")) or 1.0
    if bar_charts:
        set_two_series_bar(bar_charts[0].chart, real_t, orig_t,
                           "Realization", "Original Timeline")
    if len(bar_charts) > 1 and real_b is not None:
        set_two_series_bar(bar_charts[1].chart, real_b, orig_b,
                           "Realization", "Original Budget")
    # risk & stopper
    risk = find_shape_by_text(slide, "keterlambatan") or find_shape_by_text(slide, "Terdapat")
    if risk and p.get("Risk"):
        replace_block(risk, str(p["Risk"]))
    stop = find_shape_by_text(slide, "Kesalahan dalam mengirimkan")
    if stop and p.get("Stopper"):
        replace_block(stop, str(p["Stopper"]))


# --- text block helpers ----------------------------------------------------
def _kv(label, value):
    return None if value in (None, "") else f"{label} :\n{value}"


def _fulfilment(p):
    tgt = p.get("Target Date") or ""
    orig = p.get("Original Target") or ""
    s = f"Targeted Fulfilment :\n{tgt}"
    if orig:
        s += f"\n(rencana awal {orig})"
    return s


def _about_block(p):
    parts = []
    if p.get("Background"):
        parts.append(f"Background :\n{p['Background']}")
    if p.get("Objective"):
        parts.append(f"\nObjective :\n{p['Objective']}")
    if p.get("Notes"):
        parts.append(f"\nNotes :\n{p['Notes']}")
    return "\n".join(parts) if parts else None


def _status_block(p):
    parts = []
    if p.get("Current Phase"):
        parts.append(f"Current Phase :\n{p['Current Phase']}")
    if p.get("Next Activities"):
        parts.append(f"\nNext Activities :\n{p['Next Activities']}")
    return "\n".join(parts) if parts else None


def _reco_block(p):
    parts = []
    parts.append(f"Issues at Hand :\n{p.get('Issues at Hand') or '-'}")
    if p.get("Challenges"):
        parts.append(f"\nChallenges :\n{p['Challenges']}")
    if p.get("PMO Recommendation"):
        parts.append(f"\nPMO Recommendation (overall):\n{p['PMO Recommendation']}")
    return "\n".join(parts)


if __name__ == "__main__":
    build()
