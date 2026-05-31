# PMO Dashboard — Option B (Your Own Backend + PostgreSQL)

A full self-hosted stack: a Python/Flask REST API, PostgreSQL database, token
login, the same polished web dashboard, **and** a PowerPoint generator that
reads from the same database. One source of truth feeds both the web app and
your deck.

```
        ┌─────────────┐     HTTP/JSON      ┌──────────────┐
        │  Browser     │  ◄──────────────►  │ Flask API     │
        │ (index.html) │   login + CRUD     │ (app.py)      │
        └─────────────┘                     └──────┬───────┘
                                                   │ SQLAlchemy
                                            ┌──────▼───────┐
                                            │ PostgreSQL    │
                                            │  (pmo db)     │
                                            └──────┬───────┘
                                                   │  reads
                                            ┌──────▼────────────┐
                                            │ PowerPoint gen     │
                                            │ generate_from_db.py│
                                            └────────────────────┘
```

## Folders
- `backend/`  — Flask API, DB init, requirements
- `frontend/` — the dashboard (`index.html`), served by the backend
- `pptx/`      — PowerPoint generator wired to the same database

---

# PART 1 — Run it locally (Windows)

### 1. Install Python 3.12
https://www.python.org/downloads/release/python-3120/ — tick **Add to PATH**.

### 2. Install PostgreSQL
https://www.postgresql.org/download/windows/ (EDB installer).
- During setup, set a password for the `postgres` user — **remember it**.
- Keep the default port **5432**.
- After install, open **pgAdmin** (bundled) or the **SQL Shell (psql)** and
  create the database:
  ```sql
  CREATE DATABASE pmo;
  ```

### 3. Configure the backend
- In `backend/`, copy `.env.example` to `.env`.
- Edit `.env`: put your postgres password into `DATABASE_URL`, and set a long
  random `JWT_SECRET`.

### 4. Initialise the database (creates tables, admin user, seeds projects)
Open a terminal in `backend/`:
```
py -3 -m pip install -r requirements.txt
py -3 init_db.py admin@mncbank.co.id YourLoginPassword
```

### 5. Start the server
```
py -3 app.py
```
(or just double-click `run_local.bat`). Then open **http://localhost:8000**
and log in with the email/password from step 4.

You now have the full web dashboard running locally, backed by PostgreSQL.
Add/edit/delete projects — they persist in the database.

---

# PART 2 — Generate the PowerPoint from the same database

In `pptx/` (with `Dashboard_Template.pptx` present):
```
py -3 generate_from_db.py
```
It reads the live projects from PostgreSQL and writes
`01a. PMO Dashboard - <date>.pptx`. Any change made in the web dashboard shows
up in the next deck — one source of truth.

> Set the same `DATABASE_URL` in this terminal (or add a `.env` here too) so the
> generator points at your database.

---

# PART 3 — Deploy to a VPS (when you're ready)

Summary of the path (full commands below). On a fresh Ubuntu VPS (e.g. Hetzner
CX22, ~$5/mo):

1. **Create a non-root user & update**
   ```
   adduser pmo && usermod -aG sudo pmo
   apt update && apt upgrade -y
   ```
2. **Install PostgreSQL, Python, Nginx**
   ```
   sudo apt install -y postgresql python3-venv python3-pip nginx
   ```
3. **Create the database & user**
   ```
   sudo -u postgres psql
   CREATE DATABASE pmo;
   CREATE USER pmo WITH PASSWORD 'strong-password';
   GRANT ALL PRIVILEGES ON DATABASE pmo TO pmo;
   \q
   ```
4. **Copy the app up** (scp or git), then in `backend/`:
   ```
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt gunicorn
   # set DATABASE_URL + JWT_SECRET in .env
   python init_db.py admin@mncbank.co.id YourLoginPassword
   ```
5. **Run with gunicorn behind systemd** — create `/etc/systemd/system/pmo.service`:
   ```
   [Unit]
   Description=PMO Dashboard
   After=network.target postgresql.service

   [Service]
   User=pmo
   WorkingDirectory=/home/pmo/optionb/backend
   Environment="DATABASE_URL=postgresql+psycopg2://pmo:strong-password@localhost:5432/pmo"
   Environment="JWT_SECRET=your-long-random-secret"
   ExecStart=/home/pmo/optionb/backend/venv/bin/gunicorn -w 3 -b 127.0.0.1:8000 app:app
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   ```
   sudo systemctl enable --now pmo
   ```
6. **Nginx reverse proxy** — `/etc/nginx/sites-available/pmo`:
   ```
   server {
       listen 80;
       server_name your-domain.com;
       location / { proxy_pass http://127.0.0.1:8000; proxy_set_header Host $host; }
   }
   ```
   ```
   sudo ln -s /etc/nginx/sites-available/pmo /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   ```
7. **Free HTTPS** (Let's Encrypt):
   ```
   sudo apt install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.com
   ```

Your dashboard is now live at `https://your-domain.com`, login-protected,
auto-restarting, with HTTPS. Generate decks on the server (or locally pointed
at the server's DB) any time.

---

## API reference (for your showcase / future apps)
| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| POST | `/api/login` | no | `{email,password}` → `{token}` |
| GET | `/api/projects` | yes | list all |
| POST | `/api/projects` | yes | create |
| PUT | `/api/projects/:id` | yes | update |
| DELETE | `/api/projects/:id` | yes | delete |
| GET | `/api/health` | no | DB health check |

Auth = send header `Authorization: Bearer <token>`.

## Security notes
- Change `JWT_SECRET` and the admin password before any real deployment.
- The API enforces auth on every data route (not just the UI).
- For bank-grade production: add rate-limiting, HTTPS-only cookies, audit
  logging, and a managed/replicated database. Happy to advise when you scale.
