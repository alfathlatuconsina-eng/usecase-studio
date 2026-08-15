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
- Panduan-Pengguna-BranchOps.docx — user manual for Branch Ops EDITOR and
  VIEWER roles, in Indonesian. Admin tasks are deliberately out of scope.
  Built by `deploy/buat-panduan.js`; edit that and regenerate rather than
  editing the .docx by hand, or the two drift apart. It contains empty
  captioned boxes for screenshots — those are meant to be filled in Word.  
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

## STATUS 15 Aug 2026 — seven files changed, UNCOMMITTED. Not deployed.

Supersedes the 12 Aug block below. That block was also WRONG on two
counts, corrected here — see "what 12 Aug got wrong".

    HEAD           c1604cd "Branch Ops: kotak tanggal penyaring jadi
                   dd/mm/yyyy" — rule 19, committed and pushed.
    working tree   SEVEN files modified, none committed:
                     backend/app.py                     <- rule 22
                     backend/branchops/schema.sql       <- rules 22, 23
                     backend/branchops/analytics.py     <- rules 10, 20, 23, 24
                     backend/branchops/__init__.py      <- rules 20, 23
                     backend/branchops/ingest.py        <- rule 24
                     backend/branchops/storage.py       <- rule 24
                     deploy/buat-template-unggah.py     <- rule 24
                     contoh/Template-02, Template-03    <- rule 24 (dihasilkan)
                     frontend/branchops.html            <- rules 10, 20, 21, 22, 23
                     frontend/branchops-login.html      <- rule 22
                     CLAUDE.md
                   `_to_delete/` and a stale `.git/index.lock` were both
                   cleaned up on 15 Aug; nothing untracked is left holding
                   the `[1/6]` push guard.
    origin/main    level with c1604cd. Nothing unpushed.
    VPS code       NOT verified. Last confirmed deploy 53cef02, 9 Aug.
    Local DB       Branch Ops data REPLACED from the VPS on 15 Aug 00:20
                   WIB via `deploy/6-tarik-dari-vps.bat`. Rollback point:
                   `deploy/cadangan/bo-lokal-sebelum-impor-20260815-0020.sql`.
                   The eleven tables mirror the VPS; branchops_users and
                   branchops_audit were NOT touched, as designed.

**What changed in the code (all four rules are written up in full
below):**

1. "Status TBO" filter box on Dashboard 2 and Dashboard 3 — rule 20.
2. Search on the Beranda TBO table, by account and deposito number —
   rule 10. This one also added a column to the `/summary` UNION.
3. The always-"***" Nasabah column is hidden below 560px — rule 21.
4. Forced password change on first login, plus a self-service "Ganti
   sandi" for every role — rule 22. This is the one that touches
   `app.py`, shared by all five dashboards, and `schema.sql`. The other
   four dashboards are guarded out; read the rule before deploying.

**Owed before this is finished, in order:**

- **Browser pass on all of it.** Nothing here has been exercised against
  a running app or a real database. What HAS been checked, so you know
  what is already ruled out: every touched Python file parses, both
  inline `<script>` blocks in each of the two HTML files parse under
  Node, the psycopg placeholder count is unchanged in all three
  "Status TBO" branches, both `/summary` UNION arms carry identical
  column lists, the password rule was run against 7 inputs, and the
  Beranda search, the hidden Nasabah column and the whole forced
  password-change flow were rendered and DRIVEN in headless Chromium at
  360px and 1000px against a stubbed API. A stub is not the database:
  none of the SQL has run, and no bcrypt hash has been written.
- Hard-refresh after loading — `branchops.html` is cached, and a stale
  cache looks exactly like a change that failed.
- **Sign in with an EXISTING account first** (rule 22). It must let you
  straight in without asking for a new password — that is the only proof
  the one-time exemption ran. Only then create a test account and check
  that the new one IS forced.
- Commit. Nothing untracked is in the way any more.
- Delete the dumps holding real customer names — still outstanding from
  8 Aug and now joined by a fresh one:
  `deploy/masuk/vps-branchops.sql` (re-downloaded 15 Aug),
  `deploy/keluaran/lokal-branchops.sql`, and `/tmp/*.sql` on the VPS.

**One design decision left OPEN, deliberately not half-built:**

Adding a TBO record by hand from Dashboard 3, reusing the Ubah dialog in
an "add" mode, was designed but NOT written. It waits on one answer,
because it decides how the data is stored, not how it looks.

Every row in `branchops_tbo` needs a `batch_id`, and every dashboard
query hides rows whose batch is not `committed`. So a hand-typed row
needs a batch that no upload will ever cancel. The proposal was ONE
permanent `(entri manual)` batch, remembered by a key in
`branchops_settings`, with `periode_awal`/`periode_akhir` **NULL** and
`branch_code` NULL — because `commit_batch()` supersedes on identical
period, and a real upload always carries real dates, so it can never
match NULL. Give that batch real dates instead and the first upload
covering the same range silently sets it to `dibatalkan`, taking every
hand-typed row off every dashboard with no error at all. The cost of the
shared batch is the mirror image: cancelling it hides ALL manual rows at
once. The alternative is one batch per entry, which fills the Unggah tab
with things that are not files.

The rest of the design, if it is ever built: `POST /api/branchops/tbo`
with `@require("admin","editor")` then `require_menu("d3")` AND
`scoping.boleh_cabang()` — without the last one an editor can create
rows for branches they cannot see, which is a new hole in the jatah, not
a new feature. A separate whitelist `_TBO_BARU` = `_TBO_EDITABLE` plus
the six identity fields (never a blacklist, rule 7). `ada_tbo` and
`status_tbo` computed from `dokumen_tbo` with the same `_TIDAK_ADA` rule
as the parser (rule 6), never typed by the user, and `no_rekening_norm`
recomputed from the number.

**What the 12 Aug block got wrong**, recorded because both errors are
the kind that get believed:

- It said rule 19 was uncommitted and one commit was unpushed. Neither
  was true by 15 Aug: `git status` was clean at c1604cd, level with
  origin.
- It said the VPS→local pull "was NOT run". The files say otherwise —
  `deploy/masuk/vps-branchops.sql` and
  `deploy/cadangan/bo-lokal-sebelum-impor-20260812-2232.sql` both exist,
  dated 12 Aug 22:29 and 22:32. That backup is written at step 4/6,
  AFTER the `YA` prompt, so the import had already started. Lesson worth
  keeping: a status line about what was run is worth less than the
  timestamps on the files the script writes.

## STATUS 12 Aug 2026 — LOCAL IS AHEAD OF THE VPS. Not deployed.

Supersedes the 8 Aug block below, which stays because its push write-ups
are still the reference.

    HEAD           83ae484, working tree has ONE modified file:
                   frontend/branchops.html (rule 19, uncommitted)
    origin/main    83ae484 is AHEAD 1 — not pushed. That commit is
                   CLAUDE.md only, documentation, no code.
    VPS code       NOT verified this session. Last confirmed deploy was
                   53cef02 on 9 Aug (the code-only route). Inferred from
                   `git branch -vv` locally, not read off the VPS.
    Local DB       unchanged. The VPS→local Branch Ops pull discussed on
                   12 Aug was NOT run.

Rule 19 is a change to ONE HTML file — no schema.sql, no data, no
requirements.txt. When it is deployed, that is the **code-only** route
(`git push origin main`, then `git pull --ff-only` + `systemctl restart
pmo` over ssh). Do NOT use `2-push-ke-vps.bat` for it: that also replaces
the VPS Branch Ops database with the local one and writes ~30 MB of
backups onto an 8.7 GB disk, for a CSS-and-JS change. See "Deploying a
CODE-ONLY change" below.

After deploying it, hard-refresh the browser — `branchops.html` is
cached, and a stale cache looks exactly like a failed deploy.

Still outstanding from 8 Aug and unaffected by any of this: the browser
verification on the VPS, pruning `/root/*.sql`, and deleting the dumps
that hold real customer names (`/tmp/lokal-branchops.sql` on the VPS,
`deploy/keluaran/lokal-branchops.sql` and `deploy/masuk/vps-branchops.sql`
locally — all three were still present on 12 Aug).

## STATUS 8 Aug 2026, 23:38 — PUSHED. VPS was up to date at that point.

The push succeeded on the fifth attempt. `deploy/keluaran/push-log-20260808-2338.txt`
is the record: all seven steps, ending in `SELESAI. Cadangan:`.

    HEAD          36e64bf, pushed to origin/main, working tree clean
    VPS code      same commit, pulled at step 2/7
    VPS data      loaded from local, schema.sql re-applied at 5/7,
                  sequences reset at 6/7, 0 users left without a jatah
    VPS Postgres  16.14  (local is 18.4 — see push failure 3 below)
    VPS disk      was 100% full; cleaned to ~1.5 GB free

**Still to do, in rough priority order:**

1. **Verify in the browser on the VPS.** Nothing below has been confirmed
   against the live site: the Lingkup column on Unggah, the Alamat IP and
   Perangkat columns on Audit, the `masuk` login rows, and the idle
   logout. The IP column is expected to read 127.0.0.1 for everyone until
   nginx forwards X-Forwarded-For — see rule 17.
2. **Prune `/root/*.sql` on the VPS.** Five attempts left roughly 150 MB
   of backups on an 8.7 GB disk. See push failure 1.
3. **Delete the transferred dump**, it holds real customer names:
   `ssh root@159.65.139.45 "shred -u /tmp/lokal-branchops.sql"` and the
   local `deploy/keluaran/lokal-branchops.sql`.
4. Rules 16, 17 and 18 have run against a live database now, but have not
   been EXERCISED — nobody has yet been logged out by the idle timer on
   the VPS, or had an upload refused for being out of jatah.
5. The data problems below (batch 16, batch 21) are unchanged.

The five failed attempts are all written up under "Pushing to the VPS —
every failure that has actually happened". Read that before the next push
rather than rediscovering them.

Note the file name: git tracks this file as lowercase `claude.md`. Windows
treats that as the same file as CLAUDE.md; Linux does not. On the VPS a
checkout produces `claude.md`. Harmless — it is documentation only — but
do not "fix" it by adding a second file.

Still outstanding in the data, separate from the push: the batch 16
June rows that look synthetic, and the batch 21 `tgl_input` typo. See
"Known data problems" below. Batch 27 has been cancelled.

## Pushing to the VPS — every failure that has actually happened

Written 8 Aug 2026, the night the push finally went through, after five
failed attempts in two days. Every entry below is something that HAS
occurred, not something that might. Read this before running
`deploy/2-push-ke-vps.bat`; `deploy/0-sebelum-push.md` is the short
checklist version.

**The shape of the problem, once:** `2-vps-muat.sh` stops the `pmo`
service at step 3/7 and starts it again at 7/7. Anything that kills the
script in between leaves PRODUCTION DOWN with no message saying so. That
is what makes these failures expensive rather than annoying. After ANY
failed push, the first command is always:

    ssh root@159.65.139.45 "systemctl start pmo && systemctl is-active pmo"

### 1. The VPS disk is 8.7 GB and it HAS hit 100%

Symptom: `sed: couldn't flush <unknown>: No space left on device`, and the
script gives up at step 2/6 without touching anything.

Cause, in order of size when it happened:

    /root/.npm       710 MB   npm cache
    /root/.cache     699 MB   pip and friends
    /root/*.sql      145 MB   accumulated push/pull backups
    6 deleted-but-open file handles held more, freed by restarting services

Both caches are pure cache — deleting them is safe and they rebuild.

**The cause is structural, not accidental: every single run of
`2-push-ke-vps.bat` writes a fresh ~26 MB `pmo-sebelum-push-*.sql` plus a
~3.5 MB `bo-vps-sebelum-push-*.sql` into `/root`, and NOTHING ever deletes
them.** Five attempts in one evening is ~150 MB. This WILL refill the
disk. Prune after every successful push:

    ssh root@159.65.139.45 "ls -lht /root/*.sql"

Keep the newest of each pair, delete the rest. The proper fix — having the
script keep only the two most recent — is still not done.

Check before pushing, not after it fails:

    ssh root@159.65.139.45 "df -h /"

Anything under ~1 GB free, clean up first. And these dumps contain REAL
customer names (masking is at the API layer, not at rest), so leaving them
lying around is a data problem as well as a disk problem.

### 2. Windows PowerShell 5.1 has no `Tee-Object -Encoding`

Symptom: `Tee-Object : A parameter cannot be found that matches parameter
name 'Encoding'`, then `FINDSTR: Cannot open ...push-log-*.txt`, then
`GAGAL DI SISI VPS` — **while the VPS is perfectly fine.**

`-Encoding` was added to `Tee-Object` in PowerShell 6. On the PowerShell
that ships with Windows 10/11 it does not exist, so the command died at
parameter binding, the pipe closed, and `ssh` was killed mid-run. The
remote script got as far as writing its backup and stopped before
`git pull`. The log was never created, so `findstr` failed, so the script
blamed the VPS.

Fixed in `2-push-ke-vps.bat`: the ssh output is redirected straight to the
log file and printed with `type`. No PowerShell in that path at all.
**Do not reintroduce a pipe there.** The cost is that the screen sits
still for ~30 seconds during step 5/6 and prints everything at the end —
that is normal, not a hang.

General lesson worth keeping: a deploy script that decides success by
reading a file it may have failed to create will report the wrong side as
broken. Prefer checking the exit code of the thing that actually ran.

### 3. Local PostgreSQL 18 dumps do not load into the VPS's PostgreSQL 16

**The two sides are different major versions and always have been:**

    local: PostgreSQL 18.4
    VPS  : PostgreSQL 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)

`pg_dump` 18 writes three lines that PostgreSQL 16 rejects:

    \restrict <token>          psql meta-command, new in PG18
    \unrestrict <token>        the closing half, at end of file
    SET transaction_timeout    server parameter, new in PG17

Symptom: `psql:/tmp/lokal-branchops.sql:13: ERROR: unrecognized
configuration parameter "transaction_timeout"` — at step 4/7, service
already stopped.

Fixed in `2-vps-muat.sh` step 4a: those three lines are stripped before
`psql` runs, and the script now prints both PostgreSQL versions so the
next mismatch is visible immediately. Safe to strip —
`transaction_timeout = 0` is the default, and `\restrict` only guards psql
against untrusted dump content, which this file is not.

Stripping happens on the VPS SIDE deliberately: that is the side that
knows its own version. If the VPS is ever upgraded to 18, the block stops
matching and does nothing.

**Expect this to recur whenever local PostgreSQL is upgraded.** A newer
`pg_dump` will invent new header lines. The check that catches it is the
version pair printed at step 4a — if the load fails right after those two
lines, this is why.

### 4. The `[1/6]` guard counts UNTRACKED files

`2-push-ke-vps.bat` reads `git status --porcelain` with no
`--untracked-files=no`, so a single new file anywhere in the project stops
the push and demands you type `TETAP`. Do not type it reflexively — the
same guard is what correctly catches genuinely uncommitted code, and the
VPS pulls from git, so anything uncommitted simply will not arrive.

### 5. "Six files modified on the VPS" was a false alarm

For two days this file recorded that `backend/app.py`, `init_db.py`,
`requirements.txt`, `landing.html`, `people.html` and `quality.html` were
edited directly in production and would be destroyed by `git pull`. On
8 Aug `1-lihat-suntingan-vps.bat` produced a ZERO-BYTE diff, and all six
files were confirmed byte-identical to commit `1b3842a`. Nothing had been
edited in production at all.

The likely source is the old guard that counted untracked files (see 4).
Lesson: `1-lihat-suntingan-vps.bat` is cheap and read-only — run it and
look, rather than trusting a remembered warning. A blocker that nobody
re-verifies stays in the notes forever.

### 6. Smaller things that cost time

- **A stale `.git/index.lock`** sat in the repo for 27 hours and blocked
  every commit with "Another git process seems to be running". It was
  0 bytes with no MERGE/REBASE state — leftover from a crashed git. Check
  its age and size before assuming something is genuinely running.
- **The `[0/6]` connection test is `ssh ... >nul 2>&1`.** It hides any
  prompt, so a password or passphrase request looks like a plain failure.
  If it reports it cannot reach the VPS, run the same command by hand
  without the redirect: `ssh -o ConnectTimeout=15 root@159.65.139.45 "echo ok"`.
  One failure was simply transient and worked on retry.
- **`*** System restart required ***`** in the login banner: reboot before
  pushing, not after. Finding out the server does not come back is better
  done before a database load than during one.

### 7. A bare `git pull` does not work on the VPS

Symptom, 9 Aug 2026:

    There is no tracking information for the current branch.
    Please specify which branch you want to merge with.

The VPS's `main` had no upstream configured, so `git pull` with no
arguments fetched and then refused to merge. `git log` still showed the
old commit. Nothing broke — the command was chained with `&&`, so the
`systemctl restart` never ran and the service kept serving the old code.

`deploy/2-vps-muat.sh` never hits this because it uses the explicit form
at step 2/7: `git pull --ff-only origin main`.

Fixed permanently on 9 Aug with

    git branch --set-upstream-to=origin/main main

but keep using the explicit form in scripts anyway — `--ff-only` is the
part that matters. It refuses rather than inventing a merge commit if the
VPS ever has commits of its own, which is exactly the situation
`1b-samakan-git-vps.bat` exists to clean up.

### Deploying a CODE-ONLY change — do not use 2-push-ke-vps.bat

`2-push-ke-vps.bat` also REPLACES the VPS Branch Ops database with the
local one. For a change that touches no schema.sql, no data and no
requirements.txt, that is 30 seconds of downtime, a full data overwrite,
and another ~30 MB of backups on an 8.7 GB disk — all for nothing.

Two commands are enough, and this route is proven (9 Aug 2026, commit
`53cef02`):

    git push origin main
    ssh root@159.65.139.45 "cd /opt/pmo && git pull --ff-only origin main \
      && systemctl restart pmo && systemctl is-active pmo"

Then confirm with `git log --oneline -1` on the VPS. Look for
"Fast-forward" in the output — a merge commit there means the VPS had
its own commits and needs investigating before anything else.

The restart is still required: `ensure_schema()` only runs at start-up.
It is a no-op when schema.sql has not changed, so it is safe either way.

### What a successful run looks like

8 Aug 2026, log `deploy/keluaran/push-log-20260808-2338.txt`: all seven
steps, `3 baris khusus versi baru dibuang` at 4a, every schema.sql NOTICE
reading "already exists, skipping" (that is the idempotency working, not
an error), zero users left with an empty jatah, and the final marker
`SELESAI. Cadangan:`. That marker is what the script greps for — if it is
absent, the run did not finish, whatever else was printed.

Then, and this is separate from the script:

    ssh root@159.65.139.45 "systemctl restart pmo && systemctl is-active pmo"

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
- **11 Aug 2026, Pencairan — one orphan draft and one template-named
  upload.** Found 15 Aug while checking what to clean on that date; NO
  action was taken, nothing was cancelled or deleted. Three batches touch
  `tgl_input` 2026-08-11:

      43  committed  scope 02001 DAGO   "Template-02-Pencairan-Deposito (1).xlsx"
                     2 rows total (1 on 11 Aug), by sumirat@mncbank.co.id
      45  DRAFT      bank-wide          "07a. Pencairan Deposito 10 dan 11 Aug 2026.xlsx"
                     41 rows, uploaded 17:33:45
      46  committed  bank-wide          same file, uploaded 17:35:54

  45 and 46 are the same file two minutes apart — the orphan-draft
  pattern in rule 14: the dialog was closed without choosing, the file
  was uploaded again, and the second one was committed. 45 is invisible
  on every dashboard, but its 41 rows still sit in branchops_pencairan.
  Cancelling or deleting it costs nothing unique, because 46 holds the
  same file's staging copy.

  43 is the one needing a human decision: the filename is the blank
  template with a browser's "(1)" suffix, which reads like a test, but it
  resolved to a real branch. It contributes exactly Rp 200.000.000,00 to
  11 Aug — committed total 61.258.296.986,30 against 61.058.296.986,30
  from batch 46 alone.

  No duplicates were found on that date, and no rekon rows point at those
  pencairan rows, so Dashboard 4 is unaffected either way. Both 45 and 46
  also carry one row rejected as `tanggal_terbalik`, which never entered
  the fact table.

  The read-only query that produced all of this is
  `deploy/keluaran/periksa-pencairan-11agu.sql`. It deliberately selects
  no customer names.

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
- Daily data arrives as Excel (.xlsx) uploads parsed by ingest.py (openpyxl).
  Templates for all three file types live in `contoh/` and are verified to
  parse with 0 rejected rows; upload the branch master first or every row
  is rejected as `cabang_tak_dikenal`.
- Dashboards: d1 Break Deposito, d2 Pencairan Deposito, d3 TBO, d4 Rekonsiliasi.
  Each filters on ONE date column — tgl\_break, tgl\_input, tgl\_input, tgl\_acuan
  respectively. That mapping is repeated in `\_KOLOM\_TGL` in analytics.py and
  must stay in step with what dash\_\*() passes to \_filter().
- Uploading is possible from the Unggah tab (all three file types) AND from
  a button inside d1, d2 and d3. Both post to the same POST /upload — see
  rules 14, 15 and 18. d4 has no upload and never will; its rows are
  computed, not uploaded.

Columns added to existing tables in Aug 2026 — if a query or an INSERT
looks like it is missing one, check here before assuming it was dropped:

- `branchops\_batches.branch\_code` — batch scope. NULL = bank-wide, set
  when the batch covers exactly one branch. Decides which older batch a
  commit supersedes (rule 18).
- `branchops\_audit.ip`, `branchops\_audit.perangkat` — request origin,
  filled for EVERY audited action by db.audit(), not just logins (rule 17).
- `branchops\_settings.idle\_timeout\_menit` — idle auto-logout, in minutes,
  0 = off (rule 16).
- `branchops\_pencairan` — TBO tracking columns mirroring branchops\_tbo
  (rule 6).

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
   - "master" is ADMIN ONLY — changed Aug 2026, it used to be grantable to
     editor. `MENU\_MIN\_ROLE["master"] = ("admin",)` and `POST /master` is
     `@require("admin")`. Two reasons: the branch master defines which
     branches the whole module recognises, so a bad upload makes every
     later transaction row get rejected as `cabang\_tak\_dikenal` — for
     everyone, not just the uploader; and the file overwrites each branch's
     Tipe and Wilayah, and wilayah decides who may see which branch, so
     uploading it can change other people's row access. That is the Pengguna
     screen's level of power, so it now carries the same restriction.
     Old rows in branchops\_role\_menus that granted "master" to editor need
     no cleanup — `allowed\_menus()` intersects with `menus\_for\_role()`, so
     the grant simply stops applying. `set\_menus()` now applies the same
     intersection when SAVING, so such a row cannot be created again either.
     MENU\_DEFAULT\_OFF still lists "master" but no longer affects anyone; it
     is kept so the safety net is already in place if the key is ever
     re-opened to editor.
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
     /cabang and GET /settings — both are needed to render any dashboard
     at all. Everything else is menu-gated. When adding a new route, gate
     it too, or it becomes the next hole.
   - /summary (Beranda) is the one route that is neither open nor gated by
     a decorator, and the reason is in "Beranda" below: it cannot be shut
     off, so it narrows its own contents instead. Do not "fix" this by
     adding @require_menu("home") — that would lock people out of the only
     page they can land on. See rule 12.
   - Of those eleven keys, "home" is NOT revocable — see MENU\_ALWAYS in
     privileges.py and rule 12 below. The admin screen shows it ticked and
     disabled. Adding another key to MENU\_ALWAYS means the same care:
     something must still narrow what that screen shows.
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
     unlock any row by including data\_tbo in their payload. Since Aug 2026
     Dashboard 2 only LISTS rows that have Data TBO (rule 13), so every
     Ubah button there is enabled — that is the list narrowing, not this
     rule loosening. Do not remove the check because "every row can be
     edited anyway".
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
   tabs does not throw away what the user typed. Those stored values are
   yyyy-mm-dd; what the boxes SHOW is dd/mm/yyyy — see rule 19.

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

    **Search on the Beranda table — added 15 Aug 2026.**

    - Matches NUMBERS ONLY: `no_rekening` and `no_deposito`. Never the
      customer name, for the same reason spelled out in rule 14 for
      Dashboard 3 — the name is already "***" on screen, and matching the
      real one on the backend turns the app into a way to confirm whether
      a given customer exists in the data.
    - `no_deposito` had to be ADDED to the union to make this possible.
      `branchops_tbo` has no such column at all (it records account
      openings, not deposit transactions), so its arm selects
      `NULL::varchar AS no_deposito`. Both arms alias it in full, per
      rule 12 — either arm can stand alone when a menu is revoked.
    - The column is also DISPLAYED, as a second line under No rekening.
      A value you can search but cannot see makes a successful search look
      like a coincidence.
    - Filtering happens in the browser, over the rows already loaded, and
      `/summary` caps that list at 2000. So the search cannot reach a row
      past the cap. When the list IS truncated the info line says so and
      gives both numbers — a search that silently misses rows is exactly
      the "precise but partial" failure this file keeps warning about.
    - The row renderer was extracted into `barisTbo(r)` and is used by
      both the first paint and every re-search. Do not copy it into a
      second block: the copy nobody edits is how the search result starts
      differing from the table it filtered.

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

12. Beranda obeys Hak Menu — BUILT (Aug 2026). Do not undo this.

    Before this, `/summary` was `@require()` only. That was defensible when
    it returned counts, but rule 10 above made it return up to 2000 real
    rows out of branchops_tbo and branchops_pencairan. Any signed-in user
    therefore received d2 and d3 row data — account numbers, deposito
    numbers, nominals, targets — even with those menus revoked, and could
    read it straight out of the network response without opening a tab.
    Masking and jatah still applied; the menu check was the one missing.

    - **"home" can never be revoked** — `MENU_ALWAYS` in privileges.py.
      Beranda is where everyone lands: view-home carries `class="view on"`
      and init() calls renderHome() unconditionally. Revoking it did not
      show people less, it dropped them on a screen that refused itself.
      `allowed_menus()` and `set_menus()` both add it back, so old rows
      saved before this rule still behave. Do not gate /summary on it.
    - **What narrows Beranda is d1–d4, not "home".** `ringkasan(scope,
      menus)` takes the caller's allowed menus and builds the TBO union
      from only the arms it may see: branchops_tbo needs d3,
      branchops_pencairan needs d2, neither means no query at all. The
      four menu-card counts are nulled for dashboards the role lacks.
      Route passes `privileges.allowed_menus()`; `menus=None` means "no
      menu limit" and must never be used from an HTTP route.
    - **The counts in `hitung` are computed then discarded**, not built
      conditionally. That block is one query whose `sp * 5` multiplier is
      tied to five `{swh}` inside it; making it conditional means
      recomputing the multiplier every time, which is exactly how
      parameters shift silently. The numbers never leave the process.
      `cabang` is deliberately never nulled — Beranda needs it for the
      "Master cabang belum diisi" banner.
    - **Every UNION arm now writes its own column aliases in full.**
      PostgreSQL names the result columns after the FIRST arm only, so the
      pencairan arm used to be allowed to go without. Now that either arm
      can be dropped, either can be first: an unaliased pencairan arm
      standing alone yields `?column?` and `g.sumber`, `g.mata_uang`,
      `g.dokumen` and `g.hari_terlambat` vanish with no error at all.
      If you add a third arm, alias every column in it.
    - The frontend reads the menu list from `/summary`'s own reply, not
      from window.MENUS, so the cards and the numbers cannot disagree.
      Row buttons check d3/d2 per row's `sumber`, matching what
      PUT /tbo/<id> and PUT /pencairan/<id> actually enforce. All of this
      is presentation — the backend is what stops it.
    - Tests: `py -3 backend/uji_hak_menu_beranda.py`. No database and no
      Flask app needed; db and scoping are stubbed. It checks the two
      things that fail silently rather than loudly — placeholder count
      versus parameter count in all four privilege shapes, and that every
      union column carries an alias. Run it after touching ringkasan().

13. Dashboard 2 (Pencairan) — rebuilt Aug 2026. Do not undo this.

    Section order on the page, top to bottom. Anything not listed was
    deleted on purpose, not lost:

    1. KPI cards
    2. "Arus dana dan volume" — komposisi arus dana + tren harian
    3. "Pencairan: dipercepat vs sesuai jatuh tempo" — ringkasan + two
       stacked daily charts
    4. "Detail transaksi" — see below
    5. "Rincian per cabang menurut jenis pencairan" — collapsed `<details
       class="sect">`, break rows ONLY

    DELETED: "Fokus pengendalian: pencairan dipercepat (break)" (both
    per-branch bar charts), and the whole "Kinerja dan kepatuhan cabang"
    block — cabang nilai vs volume, kelengkapan pelaporan per cabang,
    ringkasan kepatuhan, and "Cabang tidak mengirim laporan". The backend
    still sends `tak_lapor`; it is simply unused by this dashboard now.
    `aggByBranch()` in branchops.html lost its only caller at the same
    time and is marked as such in the file — it is not a missing feature.

    - **Detail transaksi is filtered in SQL, never in JavaScript.**
      `dash_pencairan` returns a second list, `rows_detail`, whose WHERE
      clause is applied BEFORE its own `LIMIT 2000`.

      AMENDED Aug 2026 — see rule 20. This list used to be called
      `rows_tbo` and was always "TBO rows only"; it now follows the
      "Status TBO" filter box (all / without TBO / with TBO), and
      "with TBO" is the default so the opening screen is unchanged.
      What did NOT change is where the filtering happens.

      This is the whole point and it is easy to undo by accident: `rows` is
      capped at 2000 ordered by `tgl_input, id`. Filtering that in the
      browser means the screen only ever sees TBO rows that happen to fall
      inside the 2000 earliest disbursements — any TBO row past the cap
      disappears with no error, no warning, and a count that looks exact.
      Never go back to `rows.filter(r => r.punya_tbo)`.

      `rows` itself must stay UNFILTERED: the KPIs, both daily charts and
      the Rincian table are computed from it and have to count every
      disbursement. `rows` and `rows_detail` return an identical 33-column
      shape, so the edit dialog and the CSV work off either.
    - **`kpi.n_tbo`** is the true, uncapped count of TBO rows. The screen
      compares it against `rows_detail.length` and shows a warning banner
      when the list is short. Keep that banner. A precise number that is
      quietly partial is the failure that goes unnoticed longest.
      Since rule 20 the comparison follows the filter: with TBO -> `n_tbo`,
      without TBO -> `n - n_tbo`, all -> `n`. All three are server-side
      counts with no LIMIT, so no extra query was needed.
    - Columns, in order: No deposito, No rekening, Cabang, Tanggal
      Pencairan, Nasabah, Nominal, Tenor, Target TBO, Terlambat, Aksi.
      Ten columns — header, `<td>` count and `emptyRow(10)` must agree.
    - Aksi checks TWO things since rule 20: role, AND `r.punya_tbo`.
      It used to check role alone, because every listed row had Data TBO
      by construction — that assumption died with the "Status TBO" filter.
      The rule in item 7 is UNCHANGED: the backend still refuses to edit a
      pencairan row whose stored data_tbo is empty, so a button left
      showing on a "Tanpa TBO" row 403s and reads as a broken app.
    - **The whole list renders at once — no inner scroll box.** The table
      overrides `.tbl-wrap`'s 520px default to `max-height:none`. A capped
      box was tried and removed: the sticky `<thead>` hides the fact that
      the table is clipped, macOS draws no scrollbar until you scroll, and
      the row count sits at the top-right of the page far from the table,
      so hidden rows read as missing data. The inline style is safe because
      `$("root").innerHTML` is rebuilt on every dashboard switch.
    - Search by No. Deposito filters the already-loaded rows; it does not
      call the server. Both sides are compared with punctuation stripped,
      so `0012-3456` matches `00123456`. It fires on the button, on Enter,
      and on the browser's native ✕ (the `search` event — without that, the
      box clears but the table stays filtered).
    - **CSV follows what is on screen**, including the search result. A
      download that differs from the visible table is only discovered after
      the file is in someone else's hands.
    - The inline "Arus dana" dropdown went with its column. Arus dana is
      still editable through the Ubah dialog, which means only on TBO rows.
      `PATCH /api/branchops/pencairan/<id>/arus` is now unreachable from
      the UI; the endpoint was left in place deliberately.
    - Rincian per cabang is break-only, and the ROWS are filtered before
      `aggGroups`, not just the sort order. Narrowing the `order` argument
      alone still lets aggGroups build the "Sesuai Jatuh Tempo" group, and
      its numbers still land in grpTableHTML's Grand total — the table
      would read break-only while its total was not.

    NEVER write the characters percent-s in a SQL comment in analytics.py.
    psycopg counts parameter markers across the entire statement text,
    comments included, so one in a comment makes the marker count disagree
    with the parameter list and the query fails at runtime. This was
    written and caught during the Aug 2026 work on `dash_pencairan`'s kpi
    query; the note is repeated in the file at the point it happened.

14. Dashboard 3 (TBO) — search + inline upload. Aug 2026. Do not undo this.

    **Search is by No. Rekening ONLY, and that is not an oversight.**
    Nama Nasabah is replaced with "***" by masking.py before the data
    leaves the API (rule 1), so `r.nama_pemilik` in the browser is the
    literal string "***" for every row — a name search on screen would
    match all rows or none. Making it work means the BACKEND matching the
    real name, which turns the app into a way to confirm whether a given
    customer exists in the data. That is the thing rule 1 exists to
    prevent. If it is ever genuinely wanted it must be role-gated AND
    written to branchops_audit, decided deliberately — not slipped in
    because "search should search everything". The reason is repeated as a
    comment in branchops.html at the search box.

    - Both sides are compared with punctuation stripped, so `300-010-002`
      matches `300010002`. Fires on the button, on Enter, and on the
      browser's native ✕ (the `search` event — without wiring that, the box
      clears but the table stays filtered).
    - `TBO_ROWS` is filled from ALL rows, never from the search result, or
      the edit dialog cannot open a row that is currently filtered out.
    - CSV follows what is on screen, including the search result.
    - Search filters rows already loaded, so it is bounded by the
      date/branch filters and by `LIMIT 2000`.

      SUPERSEDED Aug 2026 — this used to add "unlike Dashboard 2 there is
      no server-side pre-filter here". There is one now: the "Status TBO"
      box feeds `rows_detail`, filtered in SQL. See rule 20. The search
      box still filters in the browser, on top of that list.

    **The in-dashboard upload button** sits in the dashboard header beside
    "Unduh tabel (CSV)". Since Aug 2026 it serves BOTH Dashboard 3 (TBO)
    and Dashboard 2 (Pencairan) — see rule 15 — so the element is
    `bUpData` / `fUpData`, not the old `bUpTbo` / `fUpTbo`, and the handler
    is `unggahData(file, jenis, judul)`, not `unggahTbo(file)`.

    THREE conditions must all hold before it renders: `window.DASH` is a
    key in `UNGGAH_DASH`, role is not viewer, and MENUS includes "upload".
    That mirrors `@require("admin","editor")` then
    `@privileges.require_menu("upload")` on the endpoint. Hiding it is only
    presentation — but drop the last two checks and the button appears and
    then 403s, which reads as a broken app rather than a permission.

    - It posts to the SAME `POST /upload` as the Unggah tab, with the
      `jenis` taken from `UNGGAH_DASH`. Never add a dashboard-only upload
      path — the same rule as "never add a Beranda-only write path" in
      rule 10. Two paths means one of them eventually stops validating.
    - **It NEVER auto-commits.** The upload stops as a draft and the dialog
      shows rows read / admitted / rejected / warned with the rejection
      reasons grouped by code, then Komit, Batalkan and Unduh catatan. A
      batch that lands committed with nobody reading the rejection list is
      the quietest way to get broken data onto a dashboard.
    - `boCommit(id, sesudah)` and `boBatal(id, sesudah)` take an optional
      callback so an upload started from a dashboard refreshes THAT
      dashboard instead of throwing the user into the Unggah tab. Same
      pattern as `pcEdit(id, sesudah)`. The four existing call sites in the
      Unggah tab pass one argument and still fall through to
      `renderUpload`; keep that fallback.
    - The file input is cleared after each pick. Without it, choosing the
      SAME file twice in a row fires no `change` event at all and the
      button feels dead.

    **Upload lifecycle — what actually happens, and when.** Not new, but
    now reachable from a dashboard, so it needs writing down.

    - `POST /upload` → `storage.simpan_batch()` writes FOUR things in one
      transaction, immediately: a `branchops_batches` row with
      `status='draft'`; every raw Excel row into `branchops_stg`; every
      validation finding into `branchops_issues`; and the data rows
      themselves into the fact table (`branchops_tbo` for jenis=tbo).
      Rows that failed hard validation are NOT put in the fact table —
      they exist only in stg and issues.
    - So the data is in the table the moment it is uploaded. What makes it
      APPEAR is `_AKTIF` in analytics.py, which joins
      `branchops_batches ... AND b.status='committed'`. A draft batch is
      invisible on every dashboard while its rows sit in the fact table.
    - `commit_batch()` inserts nothing. It runs two UPDATEs: any OTHER
      committed batch with the same `jenis` AND exactly the same
      `periode_awal`/`periode_akhir` becomes `dibatalkan`, then this batch
      becomes `committed`.
    - **TRAP: the supersede matches on identical period, not just jenis.**
      periode comes from the date range inside the file
      (`TGL_PERIODE[jenis]`). Re-upload a corrected file whose range
      differs by even one day — a fixed date typo, a row dropped at the
      edge — and the old batch is NOT superseded. Both stay committed and
      the same account appears twice on the dashboard. Nothing errors.
      When REPLACING an earlier upload rather than adding a new period,
      cancel the old batch on the Unggah tab first.
    - Closing the upload dialog without choosing leaves an orphan DRAFT:
      invisible, but its rows are already in the fact table, and
      re-uploading the same file makes a second one. The Unggah tab is
      where drafts are seen and cleared.

15. ONE upload button shared by d1, d2 and d3. Aug 2026.

    Dashboard 2 got the same in-dashboard upload button Dashboard 3 has,
    and Dashboard 1 was added shortly after.
    It was NOT built as a second button with a second dialog. There is one
    button (`bUpData`), one hidden file input (`fUpData`) and one dialog
    function (`unggahData(file, jenis, judul)`); which menu shows it, what
    it is labelled and what `jenis` it posts all come from ONE table:

    ```js
    const UNGGAH_DASH = {
      1: { jenis: "it_break",  label: "Unggah Data Break Deposito" },
      2: { jenis: "pencairan", label: "Unggah Data Pencairan" },
      3: { jenis: "tbo",       label: "Unggah Data TBO" },
    };
    ```

    - The `jenis` values must stay identical to the keys of
      `ingest.PARSERS` ("it_break", "pencairan", "tbo"). They are posted
      verbatim; an unknown one is a 400 from `/upload`.
    - Dashboard 1 was added on request, later in Aug 2026, and adding it
      was the one line above — nothing else changed. Worth remembering
      why it was initially left out, because it still applies: the Break
      Deposito file is an IT Group export, not a branch submission, so
      whoever clicks the button usually did not produce the file and
      cannot correct it. A rejected row there means asking IT for a new
      export, not editing a cell. Batch 27 (all `tgl_break` = 1984) is
      what that failure looks like in practice.
    - Dashboard 4 can never have one — rekon rows are computed from the
      other two tables, not uploaded. Do not add it.
    - **Copying the dialog per menu is the thing to avoid.** Everything
      worth keeping about this screen — never auto-committing, showing
      rejections grouped by code, offering Unduh catatan — has to be
      remembered in every copy. The copy nobody edits still looks correct.
      Same reasoning as "never add a Beranda-only write path" (rule 10).
    - The handler re-reads `window.DASH` at the moment a file is picked,
      not when the button was drawn. Switching menus with the OS file
      picker still open would otherwise post a Pencairan file as
      `jenis=tbo`. The parser would reject it row by row, which is far
      more confusing than never mis-sending it.
    - `switchTab` rewrites the button's label on every dashboard switch.
      A stale label is not a typo here — one button serves two file types
      that must not be swapped, so a label naming the previous menu
      invites exactly the wrong upload.
    - The supersede TRAP in rule 14 applies to Pencairan too, and matters
      more there: `TGL_PERIODE["pencairan"]` is `tgl_input`, so a
      corrected re-upload whose date range shifts by a day does NOT
      cancel the old batch. Both stay committed and the same disbursement
      is counted twice in the KPIs and both daily charts. Cancel the old
      batch on the Unggah tab first when REPLACING rather than adding.

16. Idle auto-logout — BUILT (Aug 2026). Branch Ops only.

    Leaving the screen untouched for `idle_timeout_menit` clears the token
    and sends the browser to `/branchops/login?idle=1`. Silent, by
    decision — no countdown, no "still there?" prompt. The login page
    explains why it happened, in a neutral colour rather than the red
    error style, because a login screen appearing mid-task otherwise
    reads as a crash and gets reported as one.

    - **This is NOT session security, and must not be described as such.**
      It removes the token from the browser, which is what stops a
      passer-by using an unattended screen. It does not invalidate
      anything server-side: the JWT stays valid until its own `exp`, and
      `JWT_HOURS = 12` in app.py. A token already copied out still works
      for 12 hours. Closing that means shortening `JWT_HOURS` — which is
      shared by ALL FIVE dashboards — or keeping a server-side revocation
      list. Neither was done here. The same warning is repeated in
      branchops.html and in the setting's own description.
    - Configured in `branchops_settings.idle_timeout_menit`, in MINUTES,
      `0` = off. Seeded at **1** by schema.sql. Admins change it on the
      Pengaturan tab; the field is a number input capped at 480 so nobody
      types `0.1` and locks the module out of usability.
    - **The value is read ONCE, in `init()`.** Changing the setting takes
      effect on the next page load, not the next request — unlike menu
      privileges and jatah, which are deliberately read per request. Said
      plainly under the Pengaturan heading so it is not mistaken for a bug.
    - If `GET /settings` fails, the timer does NOT start. Deliberate: a
      guessed limit throws people out on a number nobody chose. Better
      silent than wrong.
    - **Wall clock, not `setTimeout`.** A `setInterval` tick compares
      `Date.now()` against the last activity stamp. A single long
      `setTimeout` stops running when the laptop sleeps or the browser
      freezes the tab — so a session left overnight would never expire,
      which is the exact opposite of the point. The comparison catches it
      on the first tick after wake.
    - Last-activity is kept in `localStorage` (`branchops_aktivitas_terakhir`),
      so working in one tab keeps the others alive instead of each tab
      running its own countdown.
    - **Two pauses, and both exist for real failures:**
      `window._sibuk` counts in-flight `authFetch` calls, and the file
      picker sets `_pilihBerkasSampai`. The OS file dialog belongs to the
      operating system, not the page — while it is open the page receives
      no mouse or keyboard events at all, so without this, someone
      hunting for their Excel file gets thrown out precisely when they
      were about to upload. The picker grace is capped at 10 minutes and
      also cleared on window `focus`, so an abandoned dialog cannot hold
      a session open indefinitely.
    - `window._sibuk--` sits in a `finally`. If it were skipped when a
      fetch throws (network down, server stopped), the counter never
      returns to zero and the session never expires — a silent failure,
      in the permissive direction.
    - File inputs are watched by ONE delegated listener on `document`,
      not wired per element. The Unggah tab builds `fMaster` and the drop
      zone's `file` input after load, and any input added later must be
      covered automatically rather than remembered.
    - Tests: `node /tmp/t.js` style harness was used during development
      (stubbed clock + localStorage) covering the busy counter, the
      picker cap, cross-tab activity and the sleeping-laptop case. It was
      not kept in the repo — if this logic is changed, rebuild it. The
      cases that matter are the ones that fail permissively: busy counter
      stuck above zero, and a `setTimeout` rewrite that survives sleep.
    - Only Branch Ops has this. PMO, People, Quality and E-Library are
      untouched.

17. Login trail + request origin on audit — BUILT (Aug 2026).

    `branchops_audit` gained two columns, `ip` and `perangkat`, and
    `_do_login()` in app.py now writes a `masuk` row for a successful
    Branch Ops sign-in. The Audit tab shows Waktu / Pengguna / Aksi /
    Alamat IP / Perangkat / Objek / Detail.

    - **Filled in `db.audit()`, not at each call site.** That function is
      the only thing that writes to branchops_audit, so every action
      already recorded — uploads, edits, privilege changes — gained an
      origin at the same time, and any action added later gets one
      without the author remembering to.
    - **`perangkat` stores the RAW User-Agent.** The friendly
      "Chrome di Windows" is produced by `ringkasPerangkat()` in
      branchops.html at render time. This follows principle 1 at the top
      of schema.sql: raw data is never altered. Summarising before
      storage would throw away the evidence to save a string — and UA
      guessing is exactly the kind of thing that turns out wrong later.
      The raw text is in the cell's `title` tooltip.
    - The check order in `ringkasPerangkat()` is load-bearing, do not
      alphabetise it: Edge claims to be Chrome *and* Safari, Chrome
      claims to be Safari, Android claims to be Linux, and iPhone says
      "like Mac OS X". Most specific first, or everything reads as
      Safari on macOS. An unrecognised UA shows a truncated raw string
      rather than "unknown" — unreadable beats empty.
    - **Successful sign-ins ONLY.** A wrong password writes nothing, so
      this trail cannot show password guessing. That was a decision, not
      an oversight. Changing it means writing the audit row on the 401
      branch of `_do_login()` — and deciding what to record when the
      email doesn't exist at all.
    - **Branch Ops only.** PMO's `audit_log` is project-shaped
      (`project_id`, `project_name`) and People, Quality and E-Library
      have no audit table. `_do_login()` is shared by all five, hence the
      `if module == "branchops"` guard. Covering the others needs a
      shared table designed first.
    - Signing in must never fail because of bookkeeping, so the write is
      guarded three times: `_branchops` may not be in globals (the import
      at the bottom of app.py is deliberately guarded), the attribute
      lookup may miss, and `db.audit()` swallows its own DB errors.
    - **IP and User-Agent are self-reported and forgeable.** They answer
      "roughly where from", never "who". Never gate access on them. The
      Audit tab says so on screen, deliberately.

    **VPS CAVEAT — the IP column will read 127.0.0.1 in production.**
    The nginx block in the install notes forwards only Host:

        location / { proxy_pass http://127.0.0.1:8000; proxy_set_header Host $host; }

    With no `X-Forwarded-For` and no `ProxyFix` in app.py, `remote_addr`
    is the proxy itself for every user. `asal_permintaan()` prefers
    X-Forwarded-For, then X-Real-IP, then remote_addr, so the fix is
    nginx-side:

        proxy_set_header X-Real-IP        $remote_addr;
        proxy_set_header X-Forwarded-For  $proxy_add_x_forwarded_for;

    Locally, with no proxy, the address is already correct. Note the
    trade: trusting XFF is only safe *because* a proxy overwrites it. If
    the app is ever exposed directly, that header is attacker-controlled.

18. Uploads obey jatah — BUILT (Aug 2026). Do not undo this.

    An editor may only upload data for the branches in their jatah
    ("Jatah (Cabang yang dilihat)"). Admin is unrestricted. Applies to
    all three file types and to BOTH entry points — the Unggah tab and
    the in-dashboard button — because both post to the same
    `POST /upload`. That is the payoff of rule 15's single write path.

    - **The WHOLE FILE is refused (403) if it contains one out-of-scope
      branch.** Rows are not silently filtered. Two reasons, and the
      second is the one that bites: filtering makes people believe the
      whole submission landed when only part did; and a filtered batch
      still takes its PERIOD from every row in the file, because
      `ParseResult.periode()` reads `self.rows` including rejected ones.
      A half-empty batch carrying a full-width period is exactly what
      cancels another branch's batch.
    - Checked BEFORE `simpan_batch()`. A refused file must leave nothing
      behind in batches/stg/issues, or the Unggah tab fills with drafts
      that can never be committed.
    - `scoping.kode_di_luar_jatah(codes)` resolves the whole file in ONE
      query. Do not replace it with `boleh_cabang()` per row — that is a
      database round trip per row for wilayah jatah. Its rules must stay
      identical to `boleh_cabang()` and `klausa()`: see, edit and upload
      must never disagree about what a branch means. A third jatah kind
      later means changing all three.
    - Fails closed: no jatah, unknown scope kind, or a branch missing
      from the master all count as out of scope.
    - The response carries `cabang_luar` (capped at 20) and
      `cabang_luar_total`. Both screens list them. A refusal that does
      not say WHICH branch is unactionable on a 200-row file.

    **`branchops_batches.branch_code` — why supersede changed too.**

    `commit_batch()` used to cancel any committed batch with the same
    `jenis` and the exact same period. That was right while one file
    meant the whole bank. Per-branch uploads break the assumption
    outright: branch A and branch B both report Mon–Fri, same jenis,
    same period — and committing B cancelled A, with A's rows vanishing
    from every dashboard and no error anywhere. That is the normal case
    for branch reporting, not an edge case.

    - `branch_code` on the batch is NULL for a bank-wide file and set
      when the batch covers EXACTLY ONE branch (`storage.lingkup_cabang()`).
      Computed from all rows including rejected ones, so it describes the
      file rather than the surviving remainder.
    - Supersede matches with `IS NOT DISTINCT FROM`, never `=`. NULL = NULL
      is NULL in SQL, not TRUE — with plain `=`, bank-wide batches would
      stop replacing bank-wide batches, which is the one behaviour that
      had to stay unchanged.
    - Resulting matrix: bank-wide replaces bank-wide (as before); same
      branch replaces same branch; branch A never touches branch B; and
      bank-wide and single-branch batches never cancel each other.
    - That last pair is a real consequence, not an oversight: an admin's
      bank-wide upload no longer retires the branch uploads for the same
      period, so the same rows can be present twice. Cancel the old
      batches on the Unggah tab when switching between the two styles.
      The Unggah tab shows a "Lingkup" column for exactly this reason.
    - The period trap from rules 14 and 15 is UNCHANGED and still applies
      within a scope.

    Not covered by jatah, deliberately: `POST /master` (the branch master)
    is bank-wide. It defines which branches exist, so it is not a
    per-branch document and scoping it makes no sense. Since Aug 2026 the
    control is simply that it is ADMIN ONLY — see rule 2. An editor cannot
    reach it at all, so there is no per-branch case left to answer.

19. Filter date boxes are TEXT inputs showing dd/mm/yyyy — 12 Aug 2026.
    Do not convert them back to `<input type="date">`.

    "Dari tanggal" and "Sampai tanggal" in the shared filter bar are
    `<input type="text">` with a dd/mm/yyyy placeholder, plus a small
    calendar button that opens a hidden `<input type="date">` used purely
    as a picker. Frontend only — no backend, no schema, no data change.

    - **A native date input cannot be told what format to display.**
      Chrome renders it from the BROWSER UI LANGUAGE, not from the page.
      Tested 12 Aug 2026 in an English Chrome with `lang="id"` on the
      input, `lang="id-ID"`, `lang="id"` on a parent element, and an
      `id-ID` browser locale — all four still printed `03/25/2026` for
      2026-03-25. There is no HTML attribute, CSS property or JS call
      that changes it. Setting Chrome's display language DOES work, but
      that configures one machine, not the app. If a future session
      "simplifies" this back to `type="date"`, the dd/mm/yyyy requirement
      silently reverts for every user whose browser is not Indonesian.
    - **The wire format is UNCHANGED and must stay unchanged.** `tgl_awal`
      and `tgl_akhir` are still yyyy-mm-dd, and PERIODE\_PILIHAN still
      stores yyyy-mm-dd. Only the on-screen text is dd/mm/yyyy.
    - **Always go through `tglGet(id)` and `tglSet(id, iso)`.** Never read
      `$("fA").value` directly — that is display text now, and treating it
      as ISO yields a wrong date without erroring. The one deliberate raw
      read is the validity check inside the change handler.
    - **Bad input is REFUSED, never coerced.** A half-typed `25/03` or an
      impossible `31/02/2026` turns the box red and does NOT reload the
      dashboard. Without that, `tglGet()` returns "" and the filter
      silently becomes "all dates" — the numbers widen with nothing
      explaining why, which reads as broken data rather than a typo.
      `03/25/2026` is refused as well, not read the other way round.
    - **Validity is computed by hand, not by `new Date()`.**
      `new Date(2026, 1, 31)` silently becomes 3 March, and a filter that
      moves the date the user typed is worse than one that says it is
      wrong. `tglNilai()` checks month length with `Date.UTC(y, m, 0)`, so
      leap years are right: 29/02/2024 passes, 29/02/2026 does not.
    - **The hidden date input must stay RENDERED.** `.tglsem` is 1×1 at
      `opacity:0` — NOT `display:none` and not `visibility:hidden`.
      Chrome throws on `showPicker()` for an element that is not rendered,
      so the calendar button would die with no message at all.
      `showPicker()` is Chrome 99+; the fallback is `.click()`, and if
      that does nothing the box is still typable, so there is no dead end.
    - The picker writes into the text box and then dispatches a `change`
      event, so a date chosen from the calendar takes exactly the same
      path as a typed one. Do not give the picker its own save path — the
      same reasoning as "never add a Beranda-only write path" (rule 10).
    - **One filter bar serves d1, d2, d3 AND d4.** There is a single
      `fA`/`fB` pair, so Rekonsiliasi changed too. Excluding it would mean
      splitting the filter bar per dashboard, which nothing else needs.
    - **Deliberately NOT covered.** The seven date inputs inside the Ubah
      TBO and Ubah Pencairan dialogs are still `type="date"` and still
      follow the browser's language, so they can disagree with the filter
      boxes on the same screen. Dates inside TABLES and in the CSV are
      still yyyy-mm-dd. The table case is not a one-line fix: `tgl()` is
      used BOTH to render table cells and to fill filter values, so
      changing it breaks the filter — it needs a separate display-only
      function.
    - Tested with 24 conversion cases (separators `/ - .`, pasted ISO,
      leap years, round-trip ISO→display→ISO) and rendered in headless
      Chromium at 360px and 1000px. No test file was kept in the repo. If
      this logic changes, the cases that matter are the ones that fail
      QUIETLY: an unparseable box that still loads the dashboard, and a
      coerced 31 February.

20. "Status TBO" filter box on Dashboard 2 (Pencairan) — 15 Aug 2026.
    Do not undo this, and do not move the filtering into JavaScript.

    A fourth control in the shared filter bar, next to Tipe: Semua /
    Tanpa TBO / Memiliki TBO. It narrows the "Detail transaksi" table
    and the CSV built from it. Nothing else on the page moves — KPIs,
    both daily charts and Rincian per cabang still count every
    disbursement, because they are computed from `rows`, which is
    untouched.

    - **The parameter is `tbo_status`, NOT `status`.** `_f()` in
      `__init__.py` builds ONE filter dict shared by all four dashboards,
      and `status` is already dash_rekon's reconciliation status. Reusing
      the name would make a choice on Pencairan silently filter
      Dashboard 4 as well. `_f()` also whitelists the value to
      "punya"/"tanpa" and turns anything else into None (= all) — this is
      a display filter, not an access filter; row access is still
      `_scope`, which is never read from request.args.
    - **Filtered in SQL, before LIMIT.** `syarat_tbo` in `dash_pencairan`
      appends `AND {_PUNYA_TBO}` or `AND NOT {_PUNYA_TBO}` to
      `rows_detail`. Filtering `rows` in the browser instead would repeat
      exactly the bug rule 13 exists to prevent: `rows` is capped at 2000
      ordered by `tgl_input, id`, so any matching row past the cap
      disappears with no error and a count that looks exact.
    - `NOT {_PUNYA_TBO}` is NULL-safe on purpose: the first conjunct
      inside is `data_tbo IS NOT NULL`, so a row with no Data TBO
      evaluates FALSE (not NULL) and its negation is genuinely TRUE.
      If that expression is ever rewritten to lead with something else,
      re-check this.
    - `_PUNYA_TBO` contains no parameter markers, so none of the three
      branches shifts the placeholder count against `p`. Keep it that way
      — and keep the percent-s ban in rule 13 in mind if you add a
      comment near it.
    - **`rows_tbo` was renamed `rows_detail`.** A key called `rows_tbo`
      that can hold rows without TBO is a name that lies, and the next
      person reads the name, not the query.
    - **Default is "Memiliki TBO"**, so the screen opens exactly as it did
      before this box existed. Reset returns it to that default rather
      than to empty — empty means "Semua" here, so clearing it would
      change the view to something nobody chose.
    - The box is shown for Dashboard 2 only (`wrapTbo` in `switchTab`,
      same pattern as `wrapStatus` for d4 and `wrapDup` for d2), and
      `params()` only sends it when `window.DASH === 2`.
    - **Dashboard 3 (TBO) has the same box**, added the same day in a
      second pass. Same control, same parameter, one difference that
      matters: d3 filters on the STORED column `f.ada_tbo`, not on
      `_PUNYA_TBO`. `branchops_tbo` has that column, the parser fills it
      with the same rule (`_TIDAK_ADA` in ingest.py), and the rest of
      `dash_tbo` — `kpi.dengan_tbo`, the aging query — already reads it.
      Using a different marker from its own neighbours is the fastest way
      to make two numbers on one screen disagree. `ada_tbo` is
      `BOOLEAN NOT NULL DEFAULT TRUE`, so `NOT f.ada_tbo` needs no
      COALESCE.
    - d3 needed its own `rows_detail` rather than a filter on `rows`,
      because `rows` also feeds `tboDoc`, `tboJenis` and the "Perlu
      ditindaklanjuti" notes — those must keep describing every row on
      the current date/branch filter, not the slice being viewed.
    - d3's truncation banner (`#tboPotong`) is new. The menu never had one;
      with a filter in front of a `LIMIT 2000` list ordered by
      `status_tbo, tgl_input` — an order that groups like with like — one
      choice can lose almost all of its rows at the cap. Its uncapped
      comparison is `kpi.n` and `kpi.dengan_tbo`.
    - **The default differs per menu, and that is deliberate.**
      `TBO_BAWAAN = {2: "punya", 3: ""}`: Pencairan opens on "Memiliki
      TBO", TBO opens on "Semua" — each matching how that screen looked
      before the box existed. The choice is then remembered per menu in
      `TBO_PILIHAN`, like `PERIODE_PILIHAN`, and `switchTab` writes it
      into the box BEFORE `load()`. One shared value cannot satisfy both
      defaults, and a menu that suddenly opens with fewer rows than
      yesterday reads as missing data, not as a filter.
    - Not tested against a live database by the author of this change —
      no route to local PostgreSQL from where it was written. What WAS
      checked: both inline `<script>` blocks parse under Node, both
      Python files parse, and the placeholder count is unchanged in all
      three branches. The browser pass is still owed.

21. The Nasabah column is hidden below 560px — 15 Aug 2026.

    Every customer-name cell in this module renders the literal string
    "***" (rule 1, masked in the backend for every role). On a phone that
    column is pure width: it pushed the account / deposito number — the
    thing that actually tells rows apart, and the thing the Beranda and
    Dashboard 3 search boxes match on — off the right edge of the screen.

    - `.col-nasabah{display:none}` inside the existing
      `@media(max-width:560px)` block. Applied to FIVE tables: Break
      Deposito, Pencairan, TBO, Rekonsiliasi and the Beranda TBO list.
    - **The class is chosen from the column TITLE** in `tabel(cols)`,
      exactly the way the `num` class has always been chosen on that same
      line. A new table that calls its column "Nasabah" therefore behaves
      correctly without anyone remembering this rule. The two tables
      whose `<th>`s are hand-written — Rekonsiliasi and Beranda — carry
      the class literally, so if you add a third hand-written table,
      write it in.
    - **Display only. The data is still sent, still shown on a wide
      screen, and still in the CSV.** Do not "optimise" this by dropping
      the field from the API or from the export: a download whose
      contents depend on the width of the screen it was triggered from is
      only discovered after the file is in someone else's hands.
    - Accepted side effect: the truncated-name marker "…" on Break
      Deposito and the "gabungan" marker for joint CIF on TBO both ride
      inside that cell, so they vanish on a phone too. Both are about the
      source file rather than the row, and both remain on a wide screen.
    - Measured, not assumed: at 360px the computed style is `none` and
      the Beranda table's content width falls 1130px -> 1054px, putting
      No rekening third among the visible columns instead of fourth; at
      1000px it is `table-cell` and nothing moves.

22. Forced password change on first login + self-service change —
    15 Aug 2026. Branch Ops ONLY.

    `branchops_users.harus_ganti_sandi BOOLEAN NOT NULL DEFAULT TRUE`.
    New accounts, and any account whose password an admin sets, must
    change it before the module will return any data.

    - **Enforced in `require()` in app.py, not on screen.** Login puts a
      `ganti: true` claim in the JWT; `require()` then refuses EVERY
      `/api/branchops/*` route except two — `/me` and `/ganti-sandi`.
      Fails closed: a route added later is refused automatically, with
      nobody having to remember this rule. Hiding buttons would leave the
      token perfectly usable from curl.
    - **The other four dashboards are untouched.** `make_token()`,
      `require()` and `_do_login()` are shared by all five, so each hook
      is guarded — `module == "branchops"`, and `getattr(user,
      "harus_ganti_sandi", False)`, which is False for user models that
      have no such column. Extending this to PMO / People / Quality /
      E-Library means adding the column to each of their tables; it will
      not happen by itself.
    - **`/ganti-sandi` returns a NEW token, and both screens store it.**
      The old one still carries `ganti: true` until it expires 12 hours
      later (`JWT_HOURS`), so without this a successful password change
      still lands the user in a dashboard that 403s everything — which
      reads as a broken app, not as a rule.
    - **The old password is verified even when the account is already
      required to change it.** A token left behind on a shared machine
      must not be enough to take the account over.
    - **Existing accounts were exempted, once.** `ADD COLUMN ... DEFAULT
      TRUE` would otherwise have forced every current user — including
      the only admin — to change at next login, which is not what was
      asked for. The one-time `UPDATE ... SET harus_ganti_sandi = FALSE`
      is guarded by `wajib_ganti_sandi_migrasi` in `branchops_settings`,
      the same pattern as `region_class_migrasi` and
      `pencairan_status_tbo_migrasi`. Never delete that key: without it
      the block re-runs on every app start and quietly exempts new
      accounts that have not logged in yet — which cancels the feature.
    - **The rule lives in ONE function, `sandi_salah()`, used by all
      three write paths**: admin creates a user, admin sets someone's
      password, user changes their own. A path that skips it makes the
      rule vacuous, since one loose entry point is enough.
    - The rule as specified by the owner: more than 4 characters, at most
      10, must contain a special character. Whitespace does NOT count as
      that special character — otherwise "abc d" passes, which is plainly
      not what was meant. Constants: `_SANDI_MIN`, `_SANDI_MAKS`,
      `_SANDI_KHUSUS`, `_SANDI_ATURAN`.

      **Recorded objection, deliberately not silently dropped: the
      10-character CEILING weakens passwords.** bcrypt accepts 72 bytes;
      there is no technical reason to cut at 10, and the only effect is
      that long memorable passphrases become impossible. If the limit
      comes from another system holding the same credentials, write that
      system down here. Otherwise it is worth raising.
    - **"Ganti sandi" is NOT a menu key and must not become one.** It
      sits next to Keluar in the nav bar. Menu keys can be revoked per
      role by an admin (rule 2), and the ability to change your own
      password must not be revocable — the same reasoning as "home" in
      rule 12. Keeping it outside `MENU_KEYS` closes that off entirely.
      It is `@require()` with no role list, so viewers have it too.
    - The forced form lives on `branchops-login.html`, not inside the
      dashboard, so no screen is ever visible before the password is
      changed. The login page's existing "already signed in" check now
      reads `harus_ganti_sandi` from `/me` and shows the form instead of
      redirecting — `/me` is one of the two allowed routes, so without
      that check a reload would drop the user into a dashboard where
      every request 403s.
    - Every change writes `ganti_sandi` to `branchops_audit` through
      `_catat_audit_branchops()`, which carries the same three guards as
      the login trail (rule 17): signing in, or changing a password, must
      never fail because of bookkeeping.
    - Tested: the rule function against 7 inputs, and the login-page flow
      driven in headless Chromium — forced panel appears after login,
      mismatched repeat is caught in the browser, a server rejection is
      shown verbatim, and a successful change stores the NEW token and
      redirects. All against a stubbed API. **Not yet exercised against
      the real database**, and the first thing worth checking there is
      that existing accounts can still sign in without being asked to
      change anything.
    - Deploying this is NOT a data push — schema.sql changed, but
      `ensure_schema()` applies it at start-up, so the code-only route
      (`git push` + `git pull --ff-only` + `systemctl restart pmo`) is
      still the right one. Do not reach for `2-push-ke-vps.bat`.

23. Ubah data pencairan — two fields became pickers, and five new columns
    for where the money came from and where it went. 15 Aug 2026.

    Requested as four items; two of them would have quietly broken the
    numbers if written literally, so read the first two bullets before
    changing anything here.

    - ~~"Dipercepat (Break)" is a label over the old stored value.~~
      **SUPERSEDED the same day — see rule 24.** The owner chose to make
      the stored value match the label, so every filter, the parser and
      299 existing rows were moved together. `optJaga()` still supports
      label ≠ value, and that ability is the point; it is simply not in
      use for this column any more.
    - **A value outside the list is KEPT, as an extra option.** The data
      holds `Pemindahbukuan` on jenis_penarikan, which is not one of the
      two choices asked for. Without this, opening the dialog on such a
      row shows the first option and pressing Simpan overwrites the real
      value — a destructive edit nobody made deliberately. Empty values
      get a leading "— belum diisi —" option for the same reason: saving
      must not invent a value nobody chose. All of this lives in
      `optJaga()` inside `pcEdit`; it takes [value, label] pairs.
    - Five new columns on branchops_pencairan: `sumber_produk`,
      `sumber_no_rek`, `tujuan_bank`, `tujuan_no_rek`, `tujuan_nama`.
      Added to `_PENCAIRAN_EDITABLE` (still a whitelist, rule 7) and to
      BOTH `rows` and `rows_detail` in `dash_pencairan`, so the two keep
      the identical shape rule 13 depends on. The single-row GET uses
      `SELECT *`, so it needed nothing.
    - `sumber_produk` has NO CHECK in the database on purpose. The list
      is enforced once, in the whitelist. A CHECK would mean the same
      list in two places, and — if these columns are ever fed from Excel
      — one unexpected value would reject the whole ROW rather than
      leave one cell empty. Contrast rule 3, where the CHECK on
      branch_type already costs three places kept in step.
    - **`tujuan_nama` is WRITE-ONCE on screen** (owner's choice, 15 Aug
      2026). The input always opens EMPTY, showing only a `***`
      placeholder; the only way to read the value is the CSV.

      **This is a display choice, NOT a protection, and must never be
      written down as one.** The real value is still sent to the browser
      so the CSV can carry it, so anyone allowed to press Unduh can read
      it in the Network tab regardless of what the screen shows. It is
      therefore NOT in `masking.py` — putting it there would blank it in
      the CSV too, which is the opposite of what was asked. Real
      protection means a server-side CSV endpoint, role-gated and written
      to `branchops_audit` per download, exactly as rule 1 prescribes.

      **The save path is the part that bites.** Because the box always
      starts empty, `tujuan_nama` is deliberately NOT part of the body
      object; it is attached afterwards, and only when something was
      actually decided — text typed, or the "Kosongkan kolom ini" box
      ticked. Put it back in the literal and one ordinary Simpan (to fix
      a date, say) wipes a stored name nobody meant to touch, because the
      backend loop only skips keys that are ABSENT from the body.
    - **Excel is untouched.** These five are edit-only, so uploaded rows
      start empty. If they should ever come from the file, rule 8
      applies: append at the FAR RIGHT (next free for pencairan is
      column 21 / `r[20]`), keep them optional, and keep them out of the
      `wajib` list.
    - The Dashboard 2 CSV grew to 24 columns and now also carries Jenis
      penarikan, which it had been dropping. Header and row are built in
      the same function, so they cannot drift.
    - Verified in headless Chromium against a stubbed API: the pencairan
      picker offers label "Dipercepat (Break)" over value "Dipercepat
      dari Jatuh Tempo"; a row holding "Pemindahbukuan" keeps it as a
      third option, selected; an empty sumber_produk shows "— belum
      diisi —" first; and all five inputs render. **No SQL has run** —
      the five ALTER statements have not touched a real database yet.

24. One canonical spelling per value, enforced in four layers —
    15 Aug 2026. Excel dropdowns do NOT replace parser normalisation.

    `jenis_pencairan` "Dipercepat dari Jatuh Tempo" became
    **"Dipercepat (Break)"**, and `jenis_penarikan` "Pemindahbukuan"
    became **"Pemindah-bukuan"**. Owner's decision: the stored value
    follows the label, so there is only ever one spelling in the column.

    - **Renaming a stored value touches five code sites, and one of them
      is not where you would look.** All had to move together:

          analytics.py    kpi.dipercepat filter
          storage.py      the branch-side filter in jalankan_rekonsiliasi
          branchops.html  the JDIP constant (2 daily charts + Rincian)
          schema.sql      the branchops_ref_values seed
          buat-template-unggah.py   the sample rows

      `storage.py` is the dangerous one: miss it and reconciliation stops
      matching every break on the branch side, so Dashboard 4 reports the
      whole file as "Tidak dilaporkan cabang" — plausible-looking output,
      no error anywhere.
    - **Existing rows were migrated once**, guarded by
      `ejaan_baku_migrasi` in `branchops_settings` (same pattern as
      `region_class_migrasi`). 299 rows on jenis_pencairan, 9 on
      jenis_penarikan, counted from the dump before the change. The old
      `branchops_ref_values` row is deleted in the same block.
    - **`_SERAGAM` in ingest.py maps the old spellings on every parse,
      forever. Do not delete it because "the template has dropdowns
      now".** Dropdowns only exist in files created FROM the new
      template; branches keep copies, and next month's file may be a
      Save As of a July one. One old file is enough to put the old
      spelling back and silently drop those rows out of the KPI, both
      charts, Rincian AND reconciliation. Unknown values pass through
      UNCHANGED — never guessed into one of the known options, so a
      genuinely new value stays visible instead of being disguised.
    - **The Excel templates now carry real dropdowns** (openpyxl
      DataValidation), written by `deploy/buat-template-unggah.py`:
      Pencairan K4:K500 and L4:L500, TBO L4:L500 and M4:M500. Lists are
      inline in the formula (under the 255-char limit), `allow_blank` so
      an empty cell is still legal — only wrong values are refused. The
      column NUMBERS are positional, like everything else here: reorder
      the headers and those numbers must move too (rule 8).
    - **`jenis_setoran` on branchops_tbo keeps "Pemindahbukuan", no
      hyphen** — owner's decision, matching the data as it stands. So the
      two columns spell the same concept differently. That is safe
      because they live in different TABLES and no code ever compares
      them, and it is written down here precisely so nobody "tidies" it
      later without migrating the data first. For the record, TBO had
      zero rows with that value at the time; all 9 were on the pencairan
      side.
    - The four places that must agree on these lists are listed in the
      comment above `PILIHAN` in the generator: the ref_values seed, the
      API whitelists in `__init__.py`, `optJaga(...)` in branchops.html,
      and the generator itself. Nothing enforces the agreement.
    - Verified: `seragam()` exercised on 9 inputs including mixed case
      and unknown values; templates regenerated and re-parsed by the real
      parsers ("SEMUA TEMPLATE LOLOS", 0 rows rejected); and in headless
      Chromium the pickers offer exactly the new lists, an unmigrated row
      still shows its old value as a preserved extra option, saving an
      untouched dialog does NOT send `tujuan_nama`, typing sends it, and
      ticking Kosongkan sends null. **The migration SQL has not run** —
      no database has been touched.

