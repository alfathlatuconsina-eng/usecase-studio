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

## How to run LOCALLY (this is the default for everything)

- Database: local PostgreSQL 18\. Its bin folder is C:\\Program Files\\PostgreSQL\\18\\bin (must be on PATH for psql).  
- The app connects via the DATABASE\_URL in the local .env file. It should point at the LOCAL database, e.g. postgresql+psycopg2://postgres:@localhost:5432/pmo  
- Start the backend: from backend/, run  py \-3 app.py  (or double-click backend/run\_local.bat, which also installs missing packages first). Then open [http://localhost:8000](http://localhost:8000)  
- Never point DATABASE\_URL at the VPS during local development.  
- Note: README.md still says "install Python 3.12". The version I actually run is 3.13 — trust this file, not the README, until the README is updated.

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

### 4\. E-Library — repository of internal and external documents

- Frontend: frontend/elibrary.html (login: elibrary-login.html)  
- API: /api/elibrary/\*  
- Tables: elibrary\_documents, elibrary\_subjects, elibrary\_categories, elibrary\_users  
- Uploaded files live in uploads/elibrary/ — never delete these without asking

### 5\. Branch Operations and Transactions Monitoring

- Frontend: frontend/branchops.html (login: branchops-login.html)  
- API: /api/branchops/\* (Flask Blueprint in backend/branchops/)  
- Tables: branchops\_users, plus the tables in backend/branchops/schema.sql — branchops\_branches, branchops\_batches, branchops\_stg, branchops\_issues, branchops\_it\_break, branchops\_pencairan, branchops\_tbo, branchops\_rekon, branchops\_ref\_values, branchops\_settings, branchops\_audit  
- Daily data arrives as Excel (.xlsx) uploads parsed by ingest.py (openpyxl)

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
   - Ten menu keys. Nine match the data-tab values in branchops.html:
     home, d1, d2, d3, d4, upload, users, settings, audit. The tenth,
     "master", is not a tab — it is the "Langkah 0 — Master cabang" box
     inside the Unggah tab, split out so it can be granted separately.
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
   - Admin ALWAYS gets all nine menus, even if a row says otherwise. Saving
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

