# CLAUDE.md — PMO Dashboard Project

## What this project is
A private, login-protected Project Management Office (PMO) dashboard for a bank.
It has a web app (live dashboard + data entry) and a PowerPoint generator, both
reading from one shared PostgreSQL database. Built as a personal showcase.

## Tech stack (do not change without asking)
- Backend: Python + Flask, served by gunicorn in production
- Database: PostgreSQL, accessed via SQLAlchemy
- Auth: JWT tokens; passwords hashed with bcrypt
- Frontend: a single self-contained index.html (vanilla JavaScript + CSS, no
  build step, no frameworks). Keep it as one file.
- PowerPoint: python-pptx, in the pptx/ folder, reads from the same database
- Deploy target: a single Ubuntu VPS (Hetzner), Nginx in front

## Folder structure
- backend/   Flask API (app.py), DB init (init_db.py, init_db_sample.py)
- frontend/  index.html (the whole web app)
- pptx/      PowerPoint generator + template
- deploy/    server setup scripts + deployment guide

## Roles (already built — preserve this behaviour)
- admin: full access incl. user management + change history
- editor: add/edit/delete projects
- viewer: read-only
Roles are enforced on the BACKEND, not just hidden in the UI. Never weaken this.

## Hard rules — do not break these
- NEVER use real bank data. Sample/anonymised data only.
- Do NOT add new dependencies (Python packages, JS libraries, frameworks)
  without asking me first and explaining why.
- Keep the frontend as ONE self-contained index.html — no build tools.
- Always preserve backend role enforcement and the audit-log on changes.
- Ask before any destructive command (dropping databases, deleting files,
  git operations that lose work).
- Before editing, briefly tell me your plan and wait for my OK on big changes.

## How to run locally (for testing)
- Backend: from backend/, `python app.py` then open http://localhost:8000
- DB is PostgreSQL; connection comes from the DATABASE_URL environment variable
- Sample data seed: `python init_db_sample.py admin@example.com <password>`

## My context
- I'm not a professional developer — explain changes in plain terms.
- Prefer small, clear, well-commented changes over clever or complex ones.
- When something could break my data, tell me to back up first.