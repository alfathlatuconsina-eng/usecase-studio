# CLAUDE.md — UseCase Studio dashboards (local development)

This is a personal showcase project. It is now FIVE dashboards served by ONE Flask app from ONE shared PostgreSQL database (`pmo`), plus a PowerPoint generator that reads the same database. I develop LOCALLY on Windows; a copy is also deployed to a VPS, but that is separate.

## IMPORTANT — work locally only

- All work happens on THIS local machine and the LOCAL PostgreSQL database.  
- Do NOT connect to, SSH into, or run commands against the VPS (159.65.139.45) unless I explicitly ask in that message.  
- Treat the VPS as production. I push to it manually myself, later.

## Tech stack (do not change without asking)

- Backend: Python 3.13 \+ Flask (gunicorn only in production, not locally)  
- Database: PostgreSQL 18, local, accessed via SQLAlchemy  
- Auth: JWT tokens; passwords hashed with bcrypt  
- Frontend: ONE self-contained HTML file per dashboard (vanilla JS \+ CSS, no build step, no frameworks). Each dashboard stays a single file — do not split a dashboard into separate .js/.css files, and do not merge dashboards.  
- PowerPoint: python-pptx, in the pptx/ folder, reads from the same database
- make sure mobile friendly

## Folder structure

- backend/            Flask API (app.py — ALL five dashboards live in this one file), DB init (init\_db.py), requirements.txt, .env  
- backend/branchops/  the only module split out: its own Blueprint (url\_prefix /api/branchops), schema.sql, Excel ingest (ingest.py), analytics.py, storage.py, db.py  
- frontend/           one HTML file per dashboard \+ one login page each, plus landing.html (the public front page) and about.html  
- pptx/               PowerPoint generator \+ template (PMO only)  
- uploads/            files uploaded through the E-Library module  
- deploy/             scripts for moving Branch Ops data between local and VPS,
  plus their runbooks. `deploy/masuk/`, `deploy/keluaran/` and `deploy/cadangan/`
  hold DATA and are gitignored per-folder — the scripts themselves are code and
  ARE tracked (see the `!deploy/*.sql` line in .gitignore; without it the
  blanket `*.sql` rule silently swallows them)

## How to run LOCALLY (this is the default for everything)

- Database: local PostgreSQL 18\. Its bin folder is C:\\Program Files\\PostgreSQL\\18\\bin (must be on PATH for psql).  
- The app connects via the DATABASE\_URL in the local .env file. It should point at the LOCAL database, e.g. postgresql+psycopg2://postgres:@localhost:5432/pmo  
- Start the backend: from backend/, run  py \-3 app.py  (or double-click backend/run\_local.bat, which also installs missing packages first). Then open [http://localhost:8000](http://localhost:8000)  
- Never point DATABASE\_URL at the VPS during local development.  
- Note: README.md still says "install Python 3.12". The version I actually run is 3.13 — trust this file, not the README, until the README is updated.

## Pulling Branch Ops data from the VPS to local (deploy/) — Aug 2026

I sometimes want the VPS's Branch Ops data on this machine. `deploy/` holds
the tooling; `deploy/5-tarik-dari-vps.md` is the runbook. Claude cannot run
any of it — no route to the VPS, and no route to PostgreSQL on this machine
either — so these are always scripts I run myself.

Rules learned the hard way, do not undo:

- **Structure AND data are copied together** (`pg\_dump --clean --if-exists`),
  not data alone. A data-only load assumes both sides have identical columns.
  They do not: branchops\_branches on the VPS still has the old `region`
  column that was dropped locally by hapus-kolom-region-lama.sql, so a
  data-only load fails on the first row. Copying the structure removes that
  whole class of failure.
- **Emptying and loading must be ONE transaction.** The first version ran
  TRUNCATE in a separate psql call; when the load failed, the TRUNCATE had
  already committed and the tables were left EMPTY. DDL is transactional in
  PostgreSQL, so `psql -1` covers DROP/CREATE/INSERT together — a failure
  now leaves the old data untouched and nothing needs restoring.
- After loading, `backend/branchops/schema.sql` is re-applied to put the
  local-only migrations back (region\_class, branch\_codes, the jatah CHECK).
  It is idempotent, so this is safe.
- **Sequences are not carried by `pg\_dump --data-only`.** Explicit ids do
  not advance a sequence, so the next Excel upload fails with "duplicate
  key" while the data looks perfectly fine. `deploy/6b-selesaikan-lokal.sql`
  resets them. `deploy/1-export-lokal.bat` has the same hole in the other
  direction — run the setval block on the VPS if you ever push data there.
- **branchops\_users and branchops\_audit are never copied.** Overwriting
  users replaces local password hashes with the VPS's and can lock me out;
  the local audit trail is the record of what I did on this machine.
- Files moved between the machines contain REAL customer names — masking is
  in masking.py at the API layer, not at rest. Delete them from `/tmp` on the
  VPS and from `deploy/masuk/` when finished.
- `deploy/9-pulihkan-lokal.bat` restores from the per-table backup taken
  before an import. `deploy/7-batalkan-batch.sql` cancels or deletes a single
  batch from SQL — but it does NOT re-run reconciliation, which the app does
  automatically; prefer the Unggah tab button.

## Known data problems — found 6 Aug 2026, not yet fixed

Recorded so a future session does not rediscover them as bugs in the code.
Delete these notes once the data is corrected.

- **batch 27** — `05c. Data Break Deposito IT - 03August2026.xlsx`, committed
  4 Aug 2026 12:48 WIB. All 43 rows have `tgl\_break` = 1984-05-24, and the
  other date columns range from 1928 to 2311. The raw cells in branchops\_stg
  show those values came in the file itself; as\_date() only passes through
  what openpyxl returns and never guesses. This one batch is why the date
  filter defaulted to 1984. Times, names, amounts and rates in the same file
  are fine — only the three date columns are broken.
  `deploy/masuk/batch27-REKONSTRUKSI-untuk-diperbaiki.xlsx` rebuilds the file
  from staging, with the bad cells highlighted.
- **batch 16** — `04c. Data Break Deposito IT 24 - 31July2026.xlsx`. Rows
  2–13 are dated 3–19 June 2026, one per business day, and look synthetic:
  names unpadded (the real IT export is fixed-width 20 chars, and one name
  is 22), every nominal a round million, penalties at exact tenths of a
  percent, an account number containing 1234567. Rows 14–202 are the real
  July data. Batches 10, 11, 12, 14 and 15 are the same file left in draft.
- **batch 21** — one pencairan row with `tgl\_input` 2025-04-30 but
  `tgl\_pencairan` 2026-07-30, in a file covering 24–31 July 2026. Almost
  certainly a year typo. tgl\_input is a locked field, so fixing it needs a
  re-upload or direct SQL.

## Logins and roles (already built — preserve this behaviour)

Each dashboard has its OWN user table and its OWN login endpoint. A token issued for one dashboard must never grant access to another — tokens carry the module name (see make\_token / require in app.py).

- POST /api/pmo/login        → users            (legacy /api/login still works)  
- POST /api/people/login     → people\_users  
- POST /api/quality/login    → quality\_users  
- POST /api/elibrary/login   → elibrary\_users  
- POST /api/branchops/login  → branchops\_users

Roles: admin (full access incl. user management \+ change history), editor (add/edit/delete records), viewer (read-only). Some modules also use super\_admin for managing that module's own users.

Roles are enforced on the BACKEND via the require(\*roles) decorator, not just hidden in the UI. Never weaken this — never move an access check into JS only.

## Hard rules — do not break these

- Work locally only; never touch the VPS unless I say so in that message.  
- Do NOT add new dependencies (Python packages, JS libraries, frameworks) without asking me first and explaining why.  
- Keep each dashboard as ONE self-contained HTML file — no build tools.  
- Always preserve backend role enforcement and the audit log on changes.  
- Ask before any destructive command (dropping databases, deleting files, git operations that lose work). My local `pmo` DB has already been dropped/recreated once — be extra careful here.  
- Before editing, briefly tell me your plan and wait for my OK on big changes.

## My context

- I'm not a professional developer — explain changes in plain terms.  
- Prefer small, clear, well-commented changes over clever or complex ones.  
- When something could break my data, tell me to back up first.

## The dashboards — keep them separate

All five share the single `pmo` database, so the boundary between them is the TABLE PREFIX and the API PREFIX, not separate databases or folders. When working on one dashboard, do not read, write, alter or drop another dashboard's tables, routes or HTML file.

### 1\. PMO dashboard — tracks project progress

- Frontend: frontend/index.html (login: login.html)  
- API: /api/projects, /api/users, /api/audit  
- Tables: projects, users, audit\_log  
- Also feeds the PowerPoint generator in pptx/

### 2\. People Development — tracks learning and development activities

- Frontend: frontend/people.html (login: people-login.html)  
- API: /api/people/\*  
- Tables: people\_training, people\_evaluation, people\_certifications, people\_users

### 3\. Service Quality — tracks Service Quality and Excellence activities

- Frontend: frontend/quality.html (login: quality-login.html)  
- API: /api/quality/\*  
- Tables: quality\_branches, quality\_users  
- The database ALSO contains quality\_survey (120 rows). It is orphaned on
  purpose — see "Dead tables" below. Do not wire it up without asking.

### 4\. E-Library — repository of internal and external documents

- Frontend: frontend/elibrary.html (login: elibrary-login.html)  
- API: /api/elibrary/\*  
- Tables: elibrary\_documents, elibrary\_subjects, elibrary\_categories, elibrary\_users  
- Uploaded files live in uploads/elibrary/ — never delete these without asking

### Dead tables — checked Aug 2026, leave them alone

The `pmo` database contains tables that NO code reads or writes. They were
investigated on 4 Aug 2026 and deliberately left in place. If you find one of
these and think something is missing, it is not — stop and ask before acting.

- **quality\_survey** — 120 rows of branch survey data. An abandoned feature.
  There is no QualitySurvey model in app.py, and no /api/quality endpoint
  touches it; the Service Quality dashboard reads quality\_branches instead.
  Beware: an older copy of init\_db.py on the VPS still does
  `from app import (... QualitySurvey ...)`. That file CANNOT RUN — the model
  does not exist, so it fails with ImportError on import. Do not merge that
  version into the local init\_db.py; doing so breaks a working file.
  Reviving the feature means writing the model, endpoint and UI from scratch.
  The data is ready if that is ever wanted.
- **branchops\_user\_menus** — empty, 0 rows, referenced nowhere in the code.
  Left over from an earlier design where menu privileges attached to the
  individual USER. That was replaced by the per-ROLE design in
  branchops\_role\_menus (see "User privilege menu" below). Per-role is the
  intended behaviour; this table is not a half-finished per-user feature.

Also present and NOT documented per-module above: pd\_training, pd\_ikatan\_dinas,
pd\_evaluate\_event, pd\_evaluate\_facilitator. These belong to People Development
and are live — do not confuse them with the dead tables listed here.

### 5\. Branch Operations and Transactions Monitoring

- Frontend: frontend/branchops.html (login: branchops-login.html)  
- API: /api/branchops/\* (Flask Blueprint in backend/branchops/)  
- Tables: branchops\_users, plus the tables in backend/branchops/schema.sql — branchops\_branches, branchops\_batches, branchops\_stg, branchops\_issues, branchops\_it\_break, branchops\_pencairan, branchops\_tbo, branchops\_rekon, branchops\_ref\_values, branchops\_role\_menus, branchops\_settings, branchops\_audit  
- Daily data arrives as Excel (.xlsx) uploads parsed by ingest.py (openpyxl)  
- Dashboards: d1 Break Deposito, d2 Pencairan Deposito, d3 TBO, d4 Rekonsiliasi.
  Each filters on ONE date column — tgl\_break, tgl\_input, tgl\_input, tgl\_acuan
  respectively. That mapping is repeated in `\_KOLOM\_TGL` in analytics.py and
  must stay in step with what dash\_\*() passes to \_filter().

#### Branch Ops — required behaviour

1. Customer name masking — BUILT (Aug 2026). Do not undo this.

   Every customer name is replaced with "***" before the data leaves the API.
   Masking happens on the BACKEND, never in JavaScript — masking only in JS is
   not acceptable, because the raw name would still be visible in the network
   response and in the CSV export, which is built from that same response.

   - Code: backend/branchops/masking.py, wired into every JSON response through
     the \_out() helper in backend/branchops/\_\_init\_\_.py. When adding a new
     Branch Ops endpoint that returns rows, return \_out(payload) — not
     jsonify(payload) — or the new endpoint will leak names.
   - Masked fields: nama\_pemilik, nama\_pencairan, nasabah\_it, nasabah\_cabang,
     and the "nama" alias used by the top-nasabah chart. Also the raw Excel cell
     value in validation issues / issues.csv when the column is a name column.
   - NOT masked, on purpose: staff names (cs\_nama, teller\_nama, flm1\_nama,
     flm2\_nama) — those are employees, not customers. Also branch\_name and
     nama\_file, which are not people.
   - Applies to ALL roles including admin. There is deliberately NO un-masking
     endpoint. If a real name is genuinely needed, the source is the original
     Excel file, not this app.
   - If a role is ever allowed to see real names, that un-masking must be
     role-gated on the backend AND written to branchops\_audit. Change it in
     should\_mask() in masking.py — that is the single decision point.
   - Consequence to remember: since every name renders as "***", rows are told
     apart by account number / deposito number / CIF, not by name.

2. User privilege menu — BUILT (Aug 2026). Do not undo this.

   An admin screen (tab Pengguna → "Hak menu") where an admin ticks which
   menus each ROLE may see AND access.

   - Privileges attach to the ROLE (admin / editor / viewer), NOT to the
     individual user. Every viewer shares one setting. Two users with the
     same role cannot be given different menus — that is deliberate.
   - Code: backend/branchops/privileges.py. Stored in the database, table
     branchops\_role\_menus (role, menus TEXT[]) — deliberately NOT in the
     JWT and NOT in localStorage, so revoking a menu takes effect on the next
     request instead of the next login.
   - ELEVEN menu keys, listed in MENU\_KEYS in privileges.py. Ten match the
     data-tab values in branchops.html: home, d1, d2, d3, d4, upload,
     masterdata, users, settings, audit. The eleventh, "master", is not a
     tab — it is the "Langkah 0 — Master cabang" box inside the Unggah tab,
     split out so it can be granted separately. If you add a key, add it to
     MENU\_KEYS, MENU\_LABEL and (if role-limited) MENU\_MIN\_ROLE together;
     a key missing from MENU\_LABEL renders as a bare key in the admin
     screen.
   - "master" is the one key that is OFF by default (MENU\_DEFAULT\_OFF in
     privileges.py). Admin has it; editor may be granted it but does not get
     it automatically; viewer can never have it. The reason: the branch master
     defines which branches the whole module recognises, so a bad upload makes
     every transaction row get rejected.
   - Enforcement is on the BACKEND via @privileges.require\_menu("key"),
     placed AFTER @require(...) so the role check still runs first. The old
     gap is closed: /dash/&lt;no&gt; now checks d1–d4 inside the function.
   - Privileges can only NARROW, never widen. Giving "upload" to a viewer
     still fails, because @require("admin","editor") runs first. Never
     restructure this so the menu check replaces the role check.
   - Admin ALWAYS gets all eleven menus, even if a row says otherwise. Saving
     a row for "admin" is rejected outright, and allowed\_menus() ignores one
     if it somehow exists. Without this, an admin could strip "users" from
     the admin role and nobody could repair it through the app.
   - A role with no row is "not yet configured" and gets everything that role
     sensibly allows, so installing this locked nobody out.
   - Only these routes are intentionally open to every signed-in user:
     /summary, /cabang, and GET /settings — all three are needed to render
     any dashboard at all. Everything else is menu-gated. When adding a new
     route, gate it too, or it becomes the next hole.
   - The nav in branchops.html is built from the menus list returned by
     /api/branchops/me. That is presentation only — never rely on it.

3. Master Data tab — BUILT (Aug 2026). Admin only.

   Tab "Master Data" (menu key masterdata, admin only via MENU\_MIN\_ROLE).
   Two things live here, both editable without re-uploading Excel:

   - **Wilayah** — the list of Region Class values, stored in
     branchops\_ref\_values with kategori 'wilayah'. Add, rename, deactivate,
     delete. Renaming updates branchops\_branches AND branchops\_users in one
     transaction; they must move together or users silently point at a name
     that no longer exists and see nothing. Deleting is REFUSED while still
     in use rather than cascading. Deactivating removes it from the picker
     for new assignments but does NOT revoke anyone already on it.
   - **Cabang** — per-branch Tipe and Wilayah, saved instantly on change via
     PUT /api/branchops/masterdata/cabang/&lt;kode&gt;. That endpoint accepts
     region\_class and/or branch\_type; keys not sent are left alone.

   Tipe is constrained to KC / KCP / Pusat / Lainnya in THREE places that
   must stay in step: the CHECK on branchops\_branches, TIPE\_CABANG in
   scoping.py, and the TIPE array in branchops.html. Change one, change all
   three, or the picker offers a value PostgreSQL will reject.

   KNOWN AND ACCEPTED: re-uploading the branch master OVERWRITES a manually
   set Tipe. parse\_master() guesses it from the branch name ("(KC)", "(KCP)",
   code starting 000) and the upsert in storage.py does
   branch\_type=EXCLUDED.branch\_type. The UI warns about this. If that ever
   becomes annoying, the fix is in storage.py's upsert, not in the UI.

4. Jatah — which ROWS a user may see. BUILT (Aug 2026). Do not undo this.

   Separate from menu privileges. Menu privileges say which SCREENS a role
   may open; jatah says which BRANCHES' rows a user may see. Both run.
   Lives in backend/branchops/scoping.py. Read its module docstring first.

   - Two kinds, MUTUALLY EXCLUSIVE, on branchops\_users:
     region\_class VARCHAR(60) = every branch in one wilayah;
     branch\_codes TEXT[] = a specific list of branches (one branch is just
     a list of one). The special value 'SEMUA' in region\_class means all
     branches. Both NULL = sees nothing.
   - Mutual exclusivity is enforced by CHECK ck\_bo\_users\_satu\_jatah in
     schema.sql, not only in Python — one new endpoint that forgets to check
     would otherwise be enough to store a row with two meanings. The same
     CHECK also forbids an empty array: "not assigned" is always NULL.
   - Fails closed everywhere. No jatah = no rows, never all rows. Role
     'admin' always sees everything, so that an admin can always inspect and
     repair other users' jatah.
   - THE CHOKEPOINT: scope\_aktif() decides what a user may see, \_f() in
     \_\_init\_\_.py injects it as the filter key "\_scope", and klausa() turns
     it into SQL. analytics.py never opens the value. Adding a third kind of
     jatah later means editing those two functions, not every query.
     "\_scope" must NEVER be read from request.args — that would let anyone
     widen their own access by editing the URL.
   - A user tied directly to a branch sees it even if that branch has no
     region\_class. This deliberately overrides the "unclassified branches
     are admin-only" rule. See rule 5 in the scoping.py docstring.
   - History: the first version used a single branch\_code VARCHAR(5) column.
     The migration in schema.sql copies it into branch\_codes and DROPS it.
     If you find code referencing branchops\_users.branch\_code, it is stale.
   - The app has NO concept of a city. "Users covering several branches in
     one city" is expressed as a hand-picked list; the picker's search plus
     "Centang yang tampil" is how that is done in practice. If a real Kota
     grouping is ever wanted, it should be a column on branchops\_branches
     mirroring region\_class — ask before building it.

5. Scoping traps in analytics.py — fixed Aug 2026, do not reintroduce.

   Two places where jatah was NOT applied. Both are fixed; both are easy to
   undo by accident while tidying up.

   - dash\_rekon() (Dashboard 4) builds its own WHERE clause instead of
     using \_filter(), and so was the ONLY dashboard with no jatah at all.
     It now appends scoping.klausa() explicitly. Any new dashboard that
     does not go through \_filter() must do the same.
   - The "cabang tidak melapor" block in dash\_pencairan() must apply the
     jatah on the OUTER branch list, never inside the NOT EXISTS. Inside,
     the meaning inverts: an out-of-scope branch makes the subquery match
     nothing, NOT EXISTS becomes true, and the branch is listed as "did not
     report". Note also that the inner filter dict sets "\_scope" to None
     explicitly — DELETING the key is not the same thing, because \_filter()
     defaults a missing "\_scope" to "" (= see nothing), which would make
     every branch appear as non-reporting.

6. TBO tracking on BOTH fact tables — BUILT (Aug 2026). Do not undo this.

   TBO used to be tracked only on branchops\_tbo (account opening). It now
   also runs on branchops\_pencairan, because a disbursement row that
   carries a "Data TBO" value is a hanging document too. Same shape on
   both tables: `target\_pemenuhan\_tbo`, `status\_tbo`, `tgl\_tbo\_lengkap`,
   `tbo\_updated\_by`, `tbo\_updated\_at`.

   - **"Jumlah Hari Terlambat" is NEVER a stored column.** It changes every
     day and this app has no scheduler, so a stored value is wrong by the
     next morning. It is computed on read: `\_HARI\_TERLAMBAT` (TBO) and
     `\_HARI\_TERLAMBAT\_PC` (pencairan) in analytics.py. If you ever "fix"
     this by adding a column, you have introduced a bug, not removed one.
   - The rule, and both expressions must keep agreeing: no target → NULL
     (renders "—", NOT 0, because 0 reads as "on time"); status not
     Outstanding → NULL, a finished TBO must stop accruing; target still
     ahead → 0, never negative; target passed → positive day count.
   - **The "does this row have TBO" rule lives in FOUR places** and they
     must stay byte-identical: `\_TIDAK\_ADA` in ingest.py, `\_TIDAK\_ADA\_TBO`
     in \_\_init\_\_.py, `\_PUNYA\_TBO` in analytics.py, and the backfill block
     in schema.sql. A fifth copy previews it in branchops.html. They are
     duplicated on purpose — each lives in a different layer (parser, API,
     SQL) and unifying them means calling Python from inside a query.
     Change one, change all of them, or the edit screen and the reports
     will disagree about which rows have a TBO.
   - branchops\_pencairan.status\_tbo has a ONE-TIME backfill in schema.sql
     setting rows without Data TBO to 'Dikecualikan'. It is guarded by
     `pencairan\_status\_tbo\_migrasi` in branchops\_settings. Never delete
     that key — without the guard the block re-runs on every app start and
     silently overwrites whatever an editor decided.

7. Edit screens for TBO and Pencairan — BUILT (Aug 2026). Do not undo this.

   `PUT /api/branchops/tbo/<id>` and `PUT /api/branchops/pencairan/<id>`,
   both `@require("admin","editor")` then `@privileges.require\_menu(...)`.
   Dialogs live in branchops.html; the TBO one opens from Dashboard 3, the
   pencairan one from Dashboard 2, and both also open from Beranda.

   - Editable fields are a **WHITELIST** — `\_TBO\_EDITABLE` and
     `\_PENCAIRAN\_EDITABLE` in \_\_init\_\_.py. Never convert these to a
     blacklist. With a whitelist, a column added later is uneditable until
     somebody deliberately adds it; with a blacklist it becomes editable
     the moment it exists, and nobody decided that.
   - Six identity fields are locked on each screen and must stay locked:
     branch\_code, tgl\_input, no\_cif, no\_rekening, nama\_pemilik, and
     tgl\_penempatan (TBO) / tgl\_pencairan (pencairan). They are shown
     greyed out, not hidden — hiding them makes people think data is gone.
   - Pencairan editing is refused unless the row's STORED data\_tbo is
     filled. Check the stored value, never the request body, or anyone can
     unlock any row by including data\_tbo in their payload.
   - Editing no\_deposito recomputes no\_deposito\_norm in the same UPDATE.
     That column is the reconciliation key against IT data; letting the two
     drift makes rows match the wrong break, silently.
   - Editing arus\_dana sets arus\_manual=TRUE. That flag is how analytics
     tells a human decision from a parser guess.
   - **scoping.boleh\_cabang()** guards both endpoints, and the two
     single-row GETs. klausa() only protects rows fetched through a
     filtered list; an endpoint taking an id straight from the URL bypasses
     it entirely, so without this an editor could edit a branch they cannot
     even see by guessing an id. Any new by-id endpoint must call it too.

8. Excel column layout — the rule that prevents silent corruption.

   All three parsers read cells by POSITION (`r[0]`, `r[1]`, …), not by
   header text. Adding a field therefore means appending a column at the
   FAR RIGHT of the sheet and reading the next free index. As of Aug 2026:

   | parser | indices used | next free |
   |---|---|---|
   | parse\_it (Break Deposito) | r[0]–r[25] | **r[26]** |
   | parse\_pencairan | r[0]–r[19] — r[17] No. CIF, r[18] No. Rekening, r[19] Target Pemenuhan TBO | **r[20]** |
   | parse\_tbo | r[0]–r[18] — r[18] Target Pemenuhan TBO | **r[19]** |

   The three sheets have DIFFERENT layouts, so the same index means
   different things in each — r[18] is CS ID in parse\_it, No. Rekening in
   parse\_pencairan and Target Pemenuhan TBO in parse\_tbo. Always check the
   parser you are actually editing.

   Inserting a column in the MIDDLE shifts every index after it. Nothing
   errors — the rows just load into the wrong fields. New columns must also
   be optional (`len(r) > i` guard) so older files without them still
   parse, and must NOT join the `wajib` list, or old files lose completeness
   score for a column they could not have had.

9. Date range defaults are PER DASHBOARD — changed Aug 2026.

   `periode\_tersedia(scope)` in analytics.py returns a range per dashboard,
   read from the FACT TABLES using the same column each dashboard filters
   on (`\_KOLOM\_TGL`): tgl\_break for d1, tgl\_input for d2 and d3,
   tgl\_acuan for d4. It is jatah-scoped, like ringkasan().

   It used to be one global min/max over branchops\_batches.periode\_awal,
   shared by all four menus. One batch of Break Deposito rows dated 1984
   therefore made Pencairan and TBO open from 1984 as well. Do not merge it
   back into a single value.

   A dashboard with no data gets EMPTY date boxes, not a borrowed range —
   empty means no filter, which is the honest answer. The frontend keeps
   each dashboard's manually chosen dates in PERIODE\_PILIHAN so switching
   tabs does not throw away what the user typed.

10. Beranda shows open TBO from BOTH tables — changed Aug 2026.

    The "Unggahan terakhir" list was replaced by "TBO yang masih terbuka":
    a UNION of branchops\_tbo and branchops\_pencairan, ordered worst-first
    (`hari\_terlambat DESC NULLS LAST`). NULLS LAST matters — without it,
    rows with no target sort above genuinely late ones and bury them.

    The `sumber` column ('tbo' / 'pencairan') is not decoration. id 7
    exists in both tables, and the Ubah / Tandai lengkap buttons use it to
    pick the endpoint. Both buttons call the same endpoints the dashboards
    use, so role checks, jatah and audit apply identically — never add a
    Beranda-only write path.

    Upload history still exists, on the Unggah tab, from /batches.

11. Tab Unggah — Batal now works on COMMITTED batches. Aug 2026.

    The button used to render only for `status === "draft"`, so a committed
    batch with bad data could not be withdrawn through the app at all —
    direct SQL was the only route. The endpoint never had that limit;
    only the UI did. Now: draft → Komit + Batal, committed → Batal,
    dibatalkan → Komit lagi (commit\_batch accepts any status but
    'committed', so cancelling is reversible).

    Cancelling is almost always better than deleting. Every dashboard
    query joins `status='committed'` via \_AKTIF, and periode\_tersedia()
    filters the same, so a cancelled batch disappears from every view and
    from the date defaults without a single row being destroyed.
    branchops\_stg is the ONLY copy of the raw Excel cells — the app
    deletes the uploaded file after parsing (tempfile + os.unlink), so
    deleting a batch throws away the last record of what was uploaded.

