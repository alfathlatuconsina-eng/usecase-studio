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

## STATUS 16 Aug 2026 — rule 26 written, NOT committed, NOT deployed.

Supersedes the 15 Aug block below for the git and VPS lines only; that
block stays because its push write-up is still the reference.

    HEAD           ca250e7 "Branch Ops: sandi 7-11 karakter, penyaring
                   Status TBO dan Cabang di Beranda, cari no deposito di
                   Break" — level with origin/main. That is where the
                   16 Aug work of rules 10 (amended) and 25 landed.
    origin/main    ca250e7. Level.
    VPS code       still 7ebb8eb, last VERIFIED 15 Aug. TWO commits
                   behind: 9eea0f6 (docs) and ca250e7 (code). Neither
                   touches data, so both go by the code-only route.
    working tree   rules 26 and 27 UNCOMMITTED, plus the VPS disk
                   tooling. Ten edited files —
                   frontend/branchops.html, backend/branchops/schema.sql,
                   backend/branchops/ingest.py,
                   backend/branchops/__init__.py,
                   backend/branchops/analytics.py,
                   deploy/buat-template-unggah.py, deploy/2-vps-muat.sh,
                   deploy/buat-panduan.js, CLAUDE.md — five new files in
                   deploy/ (0b and 0c pairs, LANGKAH-16-AGU-2026.md), and
                   the three regenerated files in contoh/.
                   `deploy/8-cadangkan-sebelum-restart.bat` reads as
                   modified from a Linux box — that is the CRLF artefact
                   noted in the 15 Aug block, not a real edit.
    Local DB       UNCHANGED. TWO guarded migrations fire together at
                   the next backend start, through `ensure_schema()`:
                   `status_tbo_baku_migrasi` (Dikecualikan -> Tidak ada
                   TBO, both tables, plus both CHECK constraints) and
                   `jenis_rekening_baku_migrasi` (84 rows). Neither has
                   run. **Back up first** —
                   `deploy\8-cadangkan-sebelum-restart.bat`.
    VPS DB         untouched, and this change needs no data push.

**Owed before this is finished:** run the backend once locally and check
BOTH migrations reported what they should, open one TBO row of each kind
in the browser (a clean one, one of the 34 shifted ones), then commit and
deploy by the code-only route. Step-by-step:
`deploy/LANGKAH-16-AGU-2026.md`. Everything else was verified without a
database — see the last bullet of rule 26 for exactly what that covered
and what it did not.

**Data findings from 16 Aug, recorded and NOT acted on.** Both are in
"Known data problems"; nothing was changed in any database.

1. The 9 `Pemindahbukuan` pencairan rows were traced to source. Not a
   spelling problem and not a shifted column: branches typed their own
   vocabulary into a pre-dropdown template. 5 are live, and **every live
   one duplicates a row a bank-wide file already recorded correctly —
   Rp 206 juta counted twice on 10 and 12 Aug**, plus a phantom Rp 200
   juta dated 8 Nov 2026 from a file named (110826). The repair is
   cancelling batches 50 and 51 on the Unggah tab, plus a decision on
   batch 43. No SQL, and none of it can be done through the Ubah dialog
   because those rows carry `data_tbo = 'Tidak Ada'`.
2. The 34 shifted TBO rows in batches 26 and 62 — not yet investigated
   to source, unlike the above.

**Disk VPS — MEASURED 16 Aug, and it is NOT the problem.** 8.7 GB
total, 6.6 GB used, **2.1 GB free (77%)**. No cleanup was needed or
run; nothing on the VPS was changed. `deploy/0b-cek-disk-vps.bat`
diagnoses, `deploy/0c-bersihkan-vps.bat` cleans (report first,
`BERSIHKAN` to commit), and `2-vps-muat.sh` now prunes its own backups
to the two newest per family — the structural fix push failure 1 had
listed as outstanding since 8 Aug. The full composition, and the three
corrections it forced on this file's long-standing assumptions, are in
that failure's write-up. Report: `deploy/keluaran/laporan-disk.txt`.

**Swap: FIXED 16 Aug.** This box has 458 MB of RAM and had NO active
swap since June — and `dmesg` proved the OOM killer had already killed
an `apt-get`. `/swapfile2` (1.5 GB) is now active AND in `/etc/fstab`;
the dormant `/swapfile` was deleted. Details in push failure 1. This
was done BEFORE the deploy on purpose: loading a database dump is the
most memory-hungry thing this machine is ever asked to do.

Still outstanding from 15 Aug and unaffected by any of this: the browser
pass on the live site.

## STATUS 15 Aug 2026 — committed, PUSHED, and deployed to the VPS.

Supersedes the 12 Aug block below. That block was also WRONG on two
counts, corrected here — see "what 12 Aug got wrong".

    HEAD           7ebb8eb "Branch Ops: penyaring Status TBO, cari di
                   Beranda, wajib ganti sandi, sumber dana dan tujuan
                   transfer, penyeragaman ejaan" — rules 20-24 in one
                   commit, 14 files.
    origin/main    9eea0f6. Level. (The doc commit needed a second
                   attempt - the first failed with `Could not resolve
                   host: github.com`, DNS rather than git.)
    VPS code       7ebb8eb, VERIFIED — first time since 9 Aug that this
                   line is read off the machine rather than inferred.
                   `Updating c1604cd..7ebb8eb`, Fast-forward.
    working tree   clean on Windows. NOTE for anyone reading this repo
                   from a Linux box or a mounted share: .bat files will
                   read as "modified" there, because Git for Windows has
                   core.autocrlf=true - it stores LF and checks out CRLF,
                   and a git without that setting compares raw bytes.
                   Nothing is actually wrong; do not "fix" it.
    Local DB       migrated and in use. Branch Ops data was pulled from
                   the VPS on 15 Aug 00:20 WIB, then all three schema
                   migrations ran at the first restart.
                   Rollback point before that restart:
                   `deploy/cadangan/bo-sebelum-restart-20260815-1135.sql`
                   — 4.57 MB, and unlike the import backups it INCLUDES
                   branchops_users and branchops_audit.
    VPS DB         REPLACED from local at 04:48 UTC. Its own rollback
                   points, on the VPS: `~/pmo-sebelum-push-20260815-0448.sql`
                   (whole database) and `~/bo-vps-sebelum-push-20260815-0448.sql`
                   (branchops tables only).

**The push itself, from `deploy/keluaran/push-log-20260815-1148.txt`
(86 KB, read end to end):** no ERROR, no FATAL, no "does not exist"
anywhere. Fast-forward at 2/7; `3 baris khusus versi baru dibuang` at 4a
(PG18 dump into PG16, rule 3 of the push failures); schema.sql at 5/7
produced CREATE/ALTER plus "already exists, skipping" and nothing else;
service `active` at 7/7. Row counts on the VPS afterwards: pencairan
1042, it_break 1561, rekon 474, tbo 176, branches 44, batches 50, and
users 12 — untouched, because `2-push-ke-vps.bat` exports ELEVEN tables
and deliberately not branchops_users or branchops_audit. Zero users left
without a jatah.

Two checks that ran read-only before the push, both worth repeating next
time because both were cheap and one settled an old rumour:
`0-cek-vps.bat` for disk, and `1-lihat-suntingan-vps.bat` which produced
a **ZERO-BYTE diff** — no file has been edited directly on the VPS. That
is the SECOND time this has been proven (see failure 5). The warning in
`deploy/0-sebelum-push.md` about "six files edited on the VPS" is stale
and should be rewritten or deleted.

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

**Done locally:** the three migrations ran at the first restart, an
existing account still signed straight in (proving the rule 22
exemption), and the two spelling counters went to zero — checked by
running `8-cadangkan-sebelum-restart.bat` a second time, which prints
them. Before the restart it read 316 and 9.

**Confirmed ON THE VPS after the push, by query, 15 Aug:**

    six new columns present   sumber_produk, sumber_no_rek, tujuan_bank,
                              tujuan_no_rek, tujuan_nama on
                              branchops_pencairan; harus_ganti_sandi on
                              branchops_users
    UPDATE 12                 the rule 22 exemption applied by hand -
                              see the trap in that rule, it does NOT
                              happen by itself on a data push
    0 / 0 / 316               old jenis_pencairan spelling, old
                              jenis_penarikan spelling, new spelling.
                              Rule 24 landed intact on both sides.

The dumps holding real customer names are gone: `lokal-branchops.sql`
deleted locally, `/tmp/lokal-branchops.sql` shredded on the VPS,
`deploy/masuk/vps-branchops.sql` deleted. That item had been outstanding
since 8 Aug.

**Still owed:**

- Browser pass on the live site, hard-refreshed. The single most telling
  screen is **Dashboard 4**: `storage.py` filters the branch side on the
  NEW spelling, so if reconciliation is populated, code and data agree.
  Empty, or everything reading "Tidak dilaporkan cabang", means they do
  not. Also worth one test Excel upload, then Batalkan — that is what
  proves the sequences on the VPS.
- Prune `/root/*.sql` on the VPS — this push added another ~30 MB pair
  to an 8.7 GB disk, and nothing ever deletes them (failure 1).

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

Keep the newest of each pair, delete the rest.

**FIXED 16 Aug 2026 — the script now prunes itself.** `2-vps-muat.sh`
ends with a retention block keeping the **two** newest of each family
(`SIMPAN_CADANGAN=2`). Two, not one: with one, a failed push immediately
overwrites the only rollback point you have, which is exactly when you
need the previous one. It sits at the very END, after the service is
proven alive at 7/7 — pruning at the start would delete old backups to
make room for a push that may then fail. Every command carries `|| true`,
because failing to tidy is not a reason to report a successful push as
failed. Verified against six synthetic backups: two kept per family, the
families never mixed.

**MEASURED 16 Aug 2026, 13:28 UTC — and the received wisdom in this
section turns out to be wrong at today's scale.** First real reading,
from `0b-cek-disk-vps.bat`; report kept as
`deploy/keluaran/laporan-disk.txt`.

    8.7 GB total, 6.6 GB used, 2.1 GB free — 77%. NOT tight.

What actually occupies it, largest first:

    2560 MB  /swapfile2 (1.5G) + /swapfile (1.0G)   38% of everything
     702 MB  Claude Code, THREE binaries — including claude.exe, a
             WINDOWS executable, and a musl build unusable on Ubuntu
     193 MB  /var/lib/apt/lists
    ~250 MB  kernel 6.8.0-71 (estimate)
     117 MB  playwright driver inside /opt/pmo/backend/venv
      92 MB  journald
      43 MB  database pmo — pd_training is 29 MB of it
      30 MB  /root/*.sql   <- what this section has chased since 8 Aug
      26 MB  /var/log/btmp + btmp.1

**Three corrections worth more than the cleanup itself:**

- **`/root/*.sql` is 30 MB, three files.** It is the SMALLEST item on
  that list, and the new retention rule deletes none of them (one of
  each family plus a 52 KB stray). Everything this section says about it
  remains true — it does accumulate, nothing deleted it — but it was
  never what filled the disk. Two swap files nobody ever wrote down are
  85× larger.
- **The 8 Aug composition no longer holds.** `/root/.npm` 710 MB and
  `/root/.cache` 699 MB are now 0 and 4 KB. Somebody cleaned them and
  they did NOT grow back in eight days. Do not quote those figures as
  current.
- **The whole `pmo` database is 43 MB**, and every `branchops_*` table
  together is under 4 MB. The data this project worries about is not a
  disk concern and on this trajectory never will be.

Read off the same report: **a reboot is pending** — running `6.8.0-136`
while `6.8.0-137` is installed — and `/var/log/btmp` holds 26 MB of
FAILED login attempts, i.e. someone steadily trying the SSH port. Normal
for an exposed droplet, worth knowing about.

**THE SWAP FILES ARE BOTH DEAD, AND THAT IS THE REAL PROBLEM — not the
2.5 GB.** Checked the same day:

    swapon --show      printed NOTHING
    free -h            Mem 458Mi total, 397Mi used, 60Mi available
                       Swap  0B total, 0B used
    ls -lh /swapfile*  /swapfile  1.0G  4 Jun 17:37
                       /swapfile2 1.5G  9 Jun 02:58

So this box runs PostgreSQL 16 + gunicorn + nginx on **458 MB of RAM
with 60 MB available and no swap whatsoever**. Two swap files were
created in June, four days apart, and neither is active — almost
certainly because they were never added to `/etc/fstab` and did not
survive a reboot. Nothing reports that; swap simply stops existing.

**The fix is therefore the opposite of "reclaim 2.5 GB".** Turn ONE on
and delete the other: the machine gains the memory safety net it has
been missing since June, and the disk still gets 1 GB back. Order
matters — activate the one you are keeping BEFORE deleting the other:

    ssh root@159.65.139.45 "swapon /swapfile2 && swapon --show && free -h"
    # if that fails with 'invalid argument', it was never formatted:
    #   mkswap /swapfile2 && swapon /swapfile2
    ssh root@159.65.139.45 "grep -q '/swapfile2' /etc/fstab || \
      echo '/swapfile2 none swap sw 0 0' >> /etc/fstab"
    ssh root@159.65.139.45 "rm -f /swapfile"

**This is worth more than every disk item on the list above, and it is
no longer hypothetical. `dmesg` on 16 Aug showed the OOM killer had
ALREADY fired:**

    oom-kill: constraint=CONSTRAINT_NONE, task=apt-get, pid=134876
    Out of memory: Killed process 134876 (apt-get)

That one cost nothing — apt-get is restartable. The same event during a
`2-push-ke-vps.bat` run would hit `postgres` at step 4/7, with the
service already stopped at 3/7, leaving production down and the database
half-loaded. If `pmo.service` is ever found dead with nothing useful in
its own log, read `dmesg` for oom-kill BEFORE looking anywhere else.

**RESOLVED the same day.** `swapon /swapfile2` succeeded (the
`Device or resource busy` seen afterwards was a SECOND attempt against
an already-active file — correct behaviour, not a failure; `/proc/swaps`
is the thing to trust, not the error text). It took 65 MB within
minutes of coming up, which says plainly how much the box wanted it.
`/swapfile2 none swap sw 0 0` is in `/etc/fstab`, so it survives reboot
this time — the missing fstab line is almost certainly why both files
went dormant back in June. `systemd-detect-virt` reports `kvm`, so swap
is fully supported here; a container would have refused it outright.
`/swapfile` (1.0 GB, never active) was then deleted, taking free space
from 2.1 GB to roughly 3.1 GB.

`0b` section 1b was rewritten after this: when NO swap is active it now
says "activate one, delete the rest" and prints the RAM figure, instead
of the original advice to delete inactive swap files — which, on this
machine, would have been exactly the wrong move.

**Both scripts were patched on the strength of this report** (16 Aug):
`0b` now reports swap in its own section instead of letting 2.5 GB show
up incidentally under "files over 20 MB", and `0c` now also empties
`/var/lib/apt/lists` (193 MB, which `apt-get clean` does NOT touch —
after it, `apt-get update` is needed once before installing anything),
deletes the rotated `btmp.1`, and vacuums journald to **50M** instead of
100M. The old 100M threshold would have freed nothing at all against a
92 MB journal — a threshold never reached is the same as no threshold.

**Three notes on the number 8.7 GB itself**, because it is easy to
misread and was misread once:

- It is the disk's **SIZE**, not what is used. Nothing ballooned to
  8.7 GB; the whole machine is that small and has hit 100% before. So
  the question to ask is always "what is GROWING", never "what is big".
- The known composition when it filled on 8 Aug was `/root/.npm` 710 MB
  and `/root/.cache` 699 MB — **1.4 GB of pure cache**, far more than
  the SQL dumps. Both rebuild themselves; deleting them is free.
- Deleted-but-still-open file handles held more. That space does not
  come back by deleting anything — only by restarting the process
  holding it.

**Two scripts added 16 Aug 2026, both following the `0-cek-vps.bat`
pattern (scp the .sh, `sed` the CRLF, run over ssh):**

    0b-cek-disk-vps.bat + 0b-vps-disk.sh    READ-ONLY. Ten sections:
      df and inodes, biggest directories, files over 20 MB, the /root
      backups with what would be kept vs deleted, caches, journald,
      deleted-but-open handles, database and pg_wal size with the ten
      biggest tables, old kernels, and — labelled DO NOT DELETE — the
      size of uploads/elibrary and any /tmp dump still holding real
      customer names.

    0c-bersihkan-vps.bat + 0c-vps-bersih.sh  Cleans. Defaults to a
      REPORT that names every file and its size and deletes nothing;
      only the word BERSIHKAN typed at the prompt runs the real pass.
      Never touches the database (there is not one SQL statement in
      it), `/opt/pmo`, `/opt/pmo/uploads/**`, or the two newest backups
      per family. Old kernels and deleted-but-open handles are reported
      only — the second would mean restarting production, which is not
      a side effect a disk cleaner is entitled to have.

Both were exercised end to end on a throwaway Linux box, including the
destructive path: backups pruned to two per family, caches emptied,
journal vacuumed, `/tmp/lokal-branchops.sql` shredded, and both the
estimate and the actually-freed figure printed. They have NOT been run
against the VPS.

Check before pushing, not after it fails:

    ssh root@159.65.139.45 "df -h /"

Anything under ~1 GB free, clean up first. And these dumps contain REAL
customer names (masking is at the API layer, not at rest), so leaving them
lying around is a data problem as well as a disk problem — which is why
`0c` shreds them rather than `rm`-ing them.

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

  **Second cause, found 16 Aug 2026, and it will recur: running `git`
  through the Cowork bridge leaves that lock behind.** The bridge cannot
  DELETE files — `rm` on a mounted path fails with "Operation not
  permitted" — so even a read-only `git status` creates
  `.git/index.lock`, fails to remove it, and warns
  `unable to unlink ... Operation not permitted`. The lock is 0 bytes
  and nothing is running; it simply cannot be cleaned up from that side.

  The workaround the bridge CAN do is rename, so the lock gets moved to
  `.git/index.lock.stale-hapus-saja-<time>` and deleted from Windows
  afterwards. Two consequences worth remembering: **a lock file blocking
  your commits may have been left by a session that only READ the repo**,
  and the "Could Not Find" that `del` answers with later usually means
  it is already gone, not that you typed it wrong. If commits are ever
  blocked with no git running, check the working directory first — a
  Command Prompt opens in `C:\Users\...`, not on drive D, and `cd /d` is
  required to change drive at all.
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

### 8. A guarded migration NEVER runs on the VPS after a data push

15 Aug 2026, found before it did damage — but only because someone
traced what the push actually copies.

`2-push-ke-vps.bat` copies `branchops_settings`, and that is where every
one-time migration keeps its guard key. The far side therefore receives
the key ALREADY SET, and its own `schema.sql` run skips the block. Any
`ADD COLUMN ... DEFAULT`, however, has already applied.

So a push can leave the VPS with the column but WITHOUT the backfill
that was supposed to soften it. On 15 Aug that meant every production
account would have been forced to change password — from a push whose
whole point was that VPS logins were not being touched. See rule 22 for
the one-line repair.

Before any push that carries data: list the guarded blocks in
schema.sql, and for each one ask what its effect should be on the VPS.
Apply those by hand afterwards. Nothing in the tooling does it for you,
and nothing warns you.

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

- **The nine "Pemindahbukuan" rows — traced to source 16 Aug 2026, and
  the answer is NOT a spelling problem.** Read this before writing any
  SQL against them; the repair is three clicks on the Unggah tab.

  The raw Excel cells are in `branchops_stg` and were read out of
  `deploy/cadangan/bo-sebelum-restart-20260815-1138.sql`. **Nothing is
  shifted**: `r[2]` branch, `r[3]` date, `r[4]` deposit no, `r[9]`
  nominal, `r[12]` Data TBO, `r[13..15]` NIPs, `r[16]` catatan, `r[17]`
  CIF, `r[18]` rekening all line up perfectly. The branches genuinely
  TYPED `Pemindahbukuan` into the Jenis Pencairan column and `Seluruhnya`
  into Jenis Penarikan. That is their own vocabulary — *how* the money
  moved, and *how much* — entered into the two columns that ask *when*
  it was liquidated and *how* it was withdrawn. The files are all named
  `Template-02-Pencairan-Deposito*.xlsx`: copies of the blank template
  from before it had dropdowns (rule 24).

  **Only 5 of the 9 are live.** Batches 48 and 49 are `dibatalkan`, so
  their 4 rows are already invisible everywhere. The live ones are
  batch 43 (ids 825, 826), batch 50 (913, 914) and batch 51 (915).

  **Every live one duplicates a row that a BANK-WIDE file already
  recorded correctly**, and that is the real finding:

      id 825  batch 43  02001  10 Agu  Rp  66 jt  = id 890  batch 46 (bank-wide)
      id 913  batch 50  04271  12 Agu  Rp  70 jt  = id 973  batch 57 (bank-wide)
      id 914  batch 50  04271  12 Agu  Rp  70 jt  = id 974  batch 57 (bank-wide)
      id 826  batch 43  02001  11 Agu  Rp 200 jt  = id 915  batch 51 (branch, 8 Nov)

  The bank-wide twins hold `Sesuai Jatuh Tempo` / `Transfer` — the right
  values for the same transactions. So **Rp 206 juta is currently counted
  twice** on 10 and 12 Aug, and `is_duplikat` is FALSE on all of them
  because duplicate detection runs WITHIN a batch, never across batches.
  This is rule 18's documented consequence — bank-wide and single-branch
  batches never supersede each other — happening for real and unnoticed.

  **Batch 51 is the same Rp 200 juta as batch 43 under a wrong date.**
  Its file is `Template-02-Pencairan-Deposito (110826).xlsx` — 11/08/26 —
  and every date inside it reads 2026-11-08. Eight November, not eleven
  August. Because the period differs, `commit_batch()` did not supersede
  batch 43 (rule 14's trap), so both stayed committed and there is a
  phantom Rp 200 juta sitting four months in the future, invisible under
  any sane date filter.

  **These rows CANNOT be repaired through the app.** All five carry
  `data_tbo = 'Tidak Ada'`, which `_TIDAK_ADA_TBO` matches, so
  `PUT /pencairan/<id>` refuses them by design (rule 7). The Ubah button
  is not merely hidden — the endpoint says no.

  **Recommended repair, no SQL, reversible (rule 11):**

      batch 50  cancel.  Both rows exist correctly in batch 57. No loss.
      batch 51  cancel.  Same Rp 200 jt as batch 43 under a wrong date.
      batch 43  needs a decision. Its id 825 duplicates batch 46 and
                should go, but id 826 (Rp 200 jt, 11 Aug) exists in NO
                bank-wide file — cancelling 43 removes a real
                transaction from the books. Either cancel it and have
                branch 02001 re-upload that single row on the current
                template, or keep it and accept the Rp 66 jt double
                count until they do.

  **Do NOT add `pemindahbukuan` to `_SERAGAM` under `jenis_pencairan`.**
  It is not a spelling variant of anything; it is a value from the wrong
  concept. Rule 24 passes unknown values through unchanged precisely so
  they stay visible, and mapping this one would disguise a data problem
  as a tidy value.

  Worth building, if this recurs: `parse_pencairan` currently accepts any
  string in `jenis_pencairan` without a murmur. A warning-level Issue
  when the value is neither `Sesuai Jatuh Tempo` nor `Dipercepat (Break)`
  — the same shape as the existing "Jenis setoran kosong" flag — would
  have surfaced all nine at upload time, on the screen of the person who
  could still fix the file. Not built as of 16 Aug.

- **34 TBO rows are shifted ONE COLUMN — batches 26 and 62.** Found
  16 Aug 2026 while adding the pickers of rule 26, by counting values in
  `deploy/cadangan/bo-sebelum-restart-20260815-1138.sql`. Nothing was
  changed. This is rule 8's silent corruption in the wild: no error was
  ever raised, the rows loaded fine, and every value landed one field to
  the left of where it belonged.

      jenis_rekening   31 rows 'Transfer', 3 rows 'Deposito'
                       (should be Perorangan / Non Perorangan)
      jenis_setoran    19 'surat pernyataan dan kuasa gabungan format
                       legal', 3 'Tidak Ada', 2 'Form Penempatan',
                       2 'Tidak ada', 1 'Riplay', 1 'Form penempatan'
                       (these are Dokumen TBO values)
      dokumen_tbo      NIPs on several of the same rows

  Per batch: **26 → 26 rows, 62 → 5, and one each in 52, 53, 54.** So it
  is mostly two uploads, not a spreading problem. The shape says the
  source file was missing one column to the left of Jenis Rekening, or
  had one extra before it — `parse_tbo` reads by POSITION (`r[11]`,
  `r[12]`, `r[13]`), so everything after that point moved together.

  **The repair is a re-upload of the corrected file, not SQL and not
  hand-editing 34 rows.** The correct value cannot be recovered from the
  row itself: what belongs in jenis_rekening was never stored anywhere,
  it fell off the left edge. `branchops_stg` holds the raw cells for
  these batches, so what the file actually contained IS recoverable —
  read it there before deciding. Cancel the old batch on the Unggah tab
  first when replacing (rule 14's supersede trap).

  Until then the rows stay visible with their wrong values, which is why
  `_TBO_EDITABLE` was left as free text — see rule 26. They are also the
  reason `optJaga()` has to preserve out-of-list values: without that,
  opening one of these rows and pressing Simpan would overwrite the
  evidence.

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

    **AMENDED 16 Aug 2026 — the table is no longer only open TBO.**
    A "Status TBO" picker sits beside the search box: Masih terbuka
    (default) / Lengkap / Dikecualikan / Semua.

    - **It narrows the TABLE only. The orange banner above stays about
      Outstanding**, always. `ringkasan()` therefore builds the union
      TWICE from one pattern — `gabung_kpi`, pinned to Outstanding, and
      `gabung_baris`, which follows the picker. The banner is the number
      people quote in meetings; it must not change meaning because
      somebody was browsing another status. Same shape as rules 13 and 20:
      KPI whole, detail list filtered.
    - **Filtered in SQL, and the picker re-fetches.** Do not filter the
      loaded rows in the browser: the list is capped at 2000, so a row
      that matches but falls outside the cap would vanish silently. The
      search box still filters client-side — that is deliberate and its
      note says so.
    - `_STATUS_BERANDA` in analytics.py is a WHITELIST; the request value
      never reaches SQL. Anything unknown falls back to **Outstanding**,
      not to "all" — a hand-edited URL must never WIDEN what is shown.
      The reply echoes `status`, and the screen titles itself from that
      echo rather than from what it asked for.
    - **`total_pilihan`** is the uncapped count FOR THE CHOSEN STATUS, and
      it is what the "list is truncated" banner compares against. Using
      `kpi.total` there would invent a truncation warning that is wrong,
      or hide a real one. It is skipped (reusing `kpi.total`) when the
      choice is Outstanding, since then they are the same number.
    - **The card is now drawn even when nothing is Outstanding.** It used
      to live inside `if (!nTerbuka) ... else`, so the moment every TBO
      was completed the picker disappeared — exactly when someone would
      want it, to look at the completed ones.
    - **The "Terlambat" column was removed** (owner, 16 Aug). The ORDER BY
      still uses `hari_terlambat DESC NULLS LAST` — dropping the column
      does not drop the ordering, and NULLS LAST still matters.
    - **A "Kantor cabang" picker sits beside it** (16 Aug 2026), for a
      Region Head whose jatah covers several branches and who wants one
      at a time. It NARROWS INSIDE the jatah and can never widen it: the
      jatah clause `{swh}` stays in every UNION arm and comes FIRST, so a
      branch code outside the jatah yields zero rows rather than a leak.
      That is why `branch_code` may come from `request.args` while
      `_scope` may never (rule 4).
    - **The picker is filled from `window.CABANG`, stashed at init from
      `/cabang`** — the same list the dashboard filter bar uses, and
      already jatah-filtered by `daftar_cabang(scope_aktif())` on the
      server. Do not build a second branch list for this screen; two
      lists drift, and the one nobody looks at is the one that goes
      stale.
    - **TRAP: the banner query and the table query now carry DIFFERENT
      parameter counts.** The branch filter applies to `gabung_baris`
      only, so there are two parameter lists — `sp_gab` for the banner
      and `sp_baris` (= `(scope params + [kode]) * number of arms`) for
      the table. Reuse one for both and psycopg counts placeholders that
      do not match the parameters, and the query dies at runtime. The
      order inside each arm is load-bearing too: `{swh}` first, then the
      branch clause, matching how the list is built.
    - `total_pilihan`'s shortcut (reuse `kpi.total` when the status is
      Outstanding) is only valid when NO branch is selected. With one
      selected, the KPI still counts the whole jatah while the table
      shows one branch.
    - **"Tandai lengkap" stays**, but the first button now follows the
      ROW's status, not the picker: Outstanding gets "Tandai lengkap",
      anything else gets "Buka lagi", mirroring Dashboard 3 so nobody has
      to remember two behaviours. `homeLengkap(sumber, id, status)` takes
      the target status; omitted means "Lengkap", the old behaviour.
      Both still go through the same endpoints as the dashboards — role
      checks, jatah and audit apply identically. Marking complete from
      the Ubah dialog also works and always did; it is simply a second
      route to the same field.

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
    - The rule as specified by the owner, TIGHTENED on the afternoon of
      15 Aug 2026: **more than 6 characters and fewer than 12** — so 7 to
      11 — and it must contain a special character. It was 5 to 10 for
      the first few hours of that day. Whitespace does NOT count as the
      special character; otherwise "abc d" passes, which is plainly not
      what was meant. Constants, and the only place to change any of
      this: `_SANDI_MIN`, `_SANDI_MAKS`, `_SANDI_KHUSUS`,
      `_SANDI_ATURAN` in app.py — the message string is derived from the
      two numbers, so it can never disagree with them. The two sentences
      shown on screen (`branchops-login.html` and the dialog in
      `branchops.html`) are hand-written and DO NOT derive from them:
      change the numbers, change those two too.

      **Existing passwords are unaffected.** The rule runs only when a
      password is SET, so an account still on a 5- or 6-character
      password keeps working until someone changes it.

      **Recorded objection, still standing after the tightening: a
      CEILING weakens passwords.** It moved 10 → 11, which changes
      nothing about the argument. bcrypt accepts 72 bytes; there is no
      technical reason to cut here, and the only effect is that long
      memorable passphrases stay impossible. If the limit comes from
      another system holding the same credentials, write that system
      down here. Otherwise it is still worth removing.
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
    - Deploying this alone is NOT a data push — schema.sql changed, but
      `ensure_schema()` applies it at start-up, so the code-only route
      (`git push` + `git pull --ff-only` + `systemctl restart pmo`) is
      enough on its own.
    - **TRAP, and it will recur on EVERY future one-time migration:
      a guarded backfill never runs on the VPS after a data push.**
      `2-push-ke-vps.bat` copies `branchops_settings` — the very table
      the guard keys live in. So the VPS receives
      `wajib_ganti_sandi_migrasi` already set, schema.sql sees it, and
      SKIPS the exemption UPDATE. Meanwhile `ADD COLUMN ... DEFAULT
      TRUE` has already fired on every account there. Net effect: a push
      that was supposed to change nothing about VPS logins forces EVERY
      production user to change their password at next sign-in.
      Fix, run by hand after the push (owner's choice, 15 Aug 2026):

          ssh root@159.65.139.45 "sudo -u postgres psql -d pmo \
            -c \"UPDATE branchops_users SET harus_ganti_sandi = FALSE;\""

      New accounts are unaffected — they still get TRUE from the column
      default and from the API. The general lesson: after any push that
      carries branchops_settings, ask which guarded blocks were skipped
      on the far side, and apply their effect there by hand.

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
    - ~~**`jenis_setoran` on branchops_tbo keeps "Pemindahbukuan", no
      hyphen** — owner's decision, matching the data as it stands.~~
      **SUPERSEDED 16 Aug 2026 — see rule 26.** The owner reversed it and
      TBO now uses "Pemindah-bukuan" as well, so both columns finally
      spell the concept the same way. Reversing was free: zero rows held
      either spelling on that column, so nothing needed migrating.

      **This paragraph also placed 9 rows in the wrong column, and the
      correction is worth reading in full — see "The nine
      'Pemindahbukuan' rows" under "Known data problems".** Short
      version: it said "all 9 were on the pencairan side", meaning 9 rows
      of `jenis_penarikan = 'Pemindahbukuan'` that the guarded migration
      would fix. Counted from the 15 Aug backups on 16 Aug, that is not
      where they are. `jenis_penarikan` holds `Transfer` 892, NULL 135,
      **`Seluruhnya` 9**, `Tunai` 6 — no `Pemindahbukuan` at all. The 9
      sit in **`jenis_pencairan`**. So the migration's second UPDATE
      matched **zero rows**, and the "0 old spelling" check on 15 Aug
      passed for the wrong reason: it was looking at a column the value
      was never in.

      The comparison of the two backups did confirm the rest of the
      migration ran exactly as claimed: 316 rows moved from `Dipercepat
      dari Jatuh Tempo` to `Dipercepat (Break)` between 11:35 and 11:38.
      General lesson, and it is the same one as failure 5: a migration
      that reports "0 rows on the old spelling" has proved nothing until
      someone checks the value is not hiding in a neighbouring column.
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

25. Dashboard 1 (Break Deposito) — "Konsentrasi nasabah" was DELETED,
    16 Aug 2026. It is not missing; do not put it back without deciding
    the thing that made it useless.

    The block listed the top ten customers by nominal, with a bar each.
    Every label in it read `***`, because masking.py replaces customer
    names before the data leaves the API (rule 1). The GROUPING was
    correct — the SQL grouped on the REAL name — but the result was ten
    bars nobody could attribute to anyone.

    - The query `top_nasabah` in `dash_it()` was removed too, not just
      the screen block. It was that block's only consumer, so keeping it
      meant a GROUP BY over every break row on every Dashboard 1 load,
      for output nobody rendered. This differs from the rule 13
      deletions, where `tak_lapor` was left in place; the difference is
      that this one is the sole consumer relationship, and it is
      documented here so the asymmetry is deliberate rather than sloppy.
    - **The `"nama"` entry in `NAMA_NASABAH` (masking.py) STAYS.** It
      costs nothing and it protects immediately if some future query
      reuses that alias. Removing it is the kind of tidy-up that silently
      re-opens rule 1.
    - If this is ever wanted back, the question to answer FIRST is how to
      identify a customer without showing their name — account number,
      CIF, a stable hash — not how to restore the block. Restoring it
      as-is just recreates ten anonymous bars.

    **Two more columns went the same day: "Rekonsiliasi" and "Catatan"
    in Detail transaksi.** Also the owner's call, also not a loss of
    function:

    - Reconciliation status still lives on Dashboard 4, the screen built
      to act on it — and it is STILL in this table's CSV, together with
      the Selisih column. The download was deliberately left richer than
      the screen: the CSV is where follow-up actually gets done, and
      dropping it there would cost something real. Rule 21 already set
      that precedent for the Nasabah column.
    - "Catatan" rendered `flags`, the validation findings. Those are
      still stored in branchops_stg and branchops_issues and readable on
      the Unggah tab under the batch.
    - The table is now EIGHT columns. Header, `<td>` count and
      `emptyRow(8)` must agree — the same invariant rule 13 states for
      Dashboard 2. Verified in headless Chromium: 8 headers, 8 cells in
      the first row.
    - `r.rekon` and `r.rekon_selisih` are still SELECTed and still used
      by the CSV; only the `REK` colour map was deleted. Do not remove
      them from the query on the assumption they are now unused.

    **Search by deposit number was added the same day — and the column it
    searches is NOT called that.**

    - `branchops_it_break` has **no `no_deposito` and no `no_cif`**. The
      IT export carries `rek_pendebetan` (normalised into `rek_norm`) and
      `rek_pencairan`, nothing else account-like. What the branch files
      call "No. Deposito" is what the IT file calls "Rekening
      Pendebetan": `storage.py` reconciles on
      `it.rek_norm = pc.no_deposito_norm`. Same number, two names — so
      the search box is labelled No. deposito and matches
      `rek_pendebetan` / `rek_norm`.
    - **Searching by CIF is impossible here and no amount of frontend
      work fixes it.** `parse_it` reads r[0]–r[25] and none of them is a
      CIF. It would take a new column from IT Group, appended at the FAR
      RIGHT of their export (rule 8, next free index r[26]).
    - A "No deposito" COLUMN was added at the same time, second from the
      left. Searching by a value the table does not show is the failure
      already hit on Beranda: the match looks like a coincidence. That
      takes the table back to NINE columns — header, `<td>` and
      `emptyRow(9)` must agree.
    - Name search is deliberately absent, same reason as rule 14: names
      are already `***` when they reach the browser.
    - Matching strips punctuation on both sides, and the CSV follows what
      is on screen including the search result — both the same rules the
      other three screens use. Verified in headless Chromium: full number
      matches, `3000-1000-2826-025` matches `300010002826025`, Bersihkan
      restores all rows, and a miss says so in words.

26. Three fields in "Ubah data TBO" became pickers — 16 Aug 2026.
    Owner's request: uniform values in the database. Read the last three
    bullets before changing any of the three lists.

        Jenis rekening   Perorangan / Non Perorangan (Perusahaan)
        Jenis setoran    Tunai / Transfer / Pemindah-bukuan
        Jenis produk     Tabungan / Giro / Deposito

    - **`optJaga()` moved to module scope.** It used to live inside
      `pcEdit`, so `tboEdit` could not reach it. It was moved rather than
      copied, for the reason this file keeps repeating: the copy nobody
      edits is the one that starts behaving differently. Both dialogs now
      call the same function; `pcEdit` was otherwise untouched.
    - **A picker on its own does NOT make the data uniform, and assuming
      it does is the trap here.** Three other things had to move with it:
      `_SERAGAM` in ingest.py gained both TBO columns, `parse_tbo` was
      made to actually CALL `seragam()` on them — before 16 Aug it never
      did, so any mapping added there would have done nothing at all —
      and the Excel template's dropdowns were regenerated. Without the
      parser side, one branch re-using a July file puts the old spelling
      straight back. That is rule 24's lesson, hit a second time.
    - **`jenis_rekening` was migrated: `Perusahaan (Non Perorangan)` →
      `Non Perorangan (Perusahaan)`**, 84 rows, guarded by
      `jenis_rekening_baku_migrasi` in `branchops_settings`. Never delete
      that key. Unlike the 15 Aug migration this string is not filtered on
      anywhere — jenis_rekening is only displayed and grouped — so a row
      left on the old spelling would show up as a separate group rather
      than vanish silently. Migrated anyway, so the report is not split.
    - **`jenis_setoran` REVERSES the 15 Aug decision** recorded in rule 24
      (TBO keeps "Pemindahbukuan", no hyphen). Reversing cost nothing:
      counted from the 15 Aug backup, ZERO rows held either spelling. No
      UPDATE was needed — only the picker, the ref_values seed, the Excel
      dropdown and `_SERAGAM`. Rule 24's paragraph has been marked.
    - **`_TBO_EDITABLE` deliberately stays free text, NOT
      `_pilihan_opsional`.** 34 of 176 rows hold values outside every list
      (see "Known data problems"). `optJaga()` preserves such a value and
      sends it back unchanged, on purpose — so a whitelist here would
      reject any edit to those rows, including someone merely fixing a
      date, with an error that reads as a broken app rather than a rule.
      Same precedent as `jenis_pencairan` / `jenis_penarikan`, which got
      pickers on 15 Aug and stayed free text at the API. Uniformity is
      enforced by the parser (which sees every incoming row) and by the
      picker — not by refusing saves. If those 34 rows are ever repaired,
      tightening this is reasonable, but check the column is clean first.
    - **The Jenis Produk list is deliberately NARROWER than what can
      actually arrive, and that asymmetry is the thing to remember.**
      Nobody types jenis_produk: there is no such column in the Excel file
      at all. `parse_tbo` DERIVES it from the free-text Keterangan column
      via `_PRODUK` in ingest.py, which can still produce `Deposito On
      Call` (16 rows) and `Bundling` (5 rows). The owner chose three on
      16 Aug knowing this. So the picker narrows what a person can newly
      choose; it does not narrow what an upload creates, and the column
      will keep holding five values. The ref_values seed still lists all
      five on purpose — it describes what can arrive, not what the screen
      offers. Making the column genuinely three-valued means changing
      `_PRODUK`, which changes the MEANING of 21 rows and needs its own
      guarded migration. That is a data decision, not a display one.
    - Verified: both inline `<script>` blocks parse under Node; the three
      Python files compile; `seragam()` exercised on 13 inputs including
      unknown values and the shifted-column junk, all passing through as
      intended; templates regenerated and re-parsed by the real parsers
      ("SEMUA TEMPLATE LOLOS", 0 rejected), with the sample rows updated
      so the template no longer violates its own dropdowns. In headless
      Chromium against a stubbed API, 25 assertions: all three render as
      `<select>` with the right options and order; a clean row round-trips
      untouched; a row holding `Transfer` / a document string / `Deposito
      On Call` keeps all three as preserved extra options AND still sends
      them unchanged on a Simpan nobody edited; an all-empty row shows
      "— belum diisi —" first and still saves as null; and `pcEdit` still
      works after the move.
    - **The migration was rehearsed on a real PostgreSQL 16** — a
      throwaway cluster, NOT this machine's `pmo` and not the VPS. Worth
      doing because 16 is the VPS's major version (16.14) while local is
      18.4, so this also proves schema.sql still loads there (push
      failure 3). `schema.sql` ran clean on an empty database, then
      against 176 synthetic rows matching the real distribution: 84 rows
      moved to the new spelling, 57 `Perorangan` untouched, and the
      31 `Transfer` + 3 `Deposito` + 1 NULL — the shifted-column rows —
      were left ALONE, which is the point: the migration does not guess.
      Run a third time with the guard in place, five deliberately
      re-introduced old-spelling rows survived, proving the block is
      skipped rather than re-applied. **Nothing has touched the real
      database**; the 84-row UPDATE fires at your next backend start,
      through `ensure_schema()`.
    - Deploying this is the **code-only** route: schema.sql changed, but
      `ensure_schema()` applies it at start-up and no data moves between
      machines. Note the mirror image of push failure 8 — because the VPS
      runs schema.sql against ITS OWN `branchops_settings`, the guard key
      is absent there and the migration WILL run. That is the wanted
      behaviour here. Only a DATA push would carry the key across and
      skip it.

27. `Dikecualikan` became **`Tidak ada TBO`** — 16 Aug 2026, owner's
    decision. Renaming a value that TWO tables share; read the first
    three bullets before touching any of it.

    "Dikecualikan" never said what was excluded. "Tidak ada TBO" states
    the condition directly. Twenty sites across seven files.

    - **It had to hit `branchops_pencairan` too, and that was not a
      preference.** Both tables carry `status_tbo` with the same three
      values, and `_STATUS_BERANDA` in analytics.py is ONE filter applied
      to BOTH arms of the Beranda UNION. Renaming only `branchops_tbo`
      leaves the Beranda "Status TBO" picker matching TBO rows and not
      pencairan rows — no error, just rows missing from a list. So the
      Ubah Pencairan dialog changed as well, on a screen nobody asked to
      change. Contrast rule 24's `jenis_setoran`, where two tables could
      safely disagree because no code ever compared them.
    - **Safer than the 15 Aug rename, and worth knowing why.** NOTHING
      filters on `'Dikecualikan'` — every KPI, chart, aging query and
      reconciliation filter compares against `'Outstanding'`, which did
      not move. The only functional comparison was `_STATUS_BERANDA`.
      So this rename could not silently drop rows out of the numbers,
      which is the failure that made the `jenis_pencairan` rename
      dangerous.
    - **What made it delicate instead: TWO CHECK constraints.** The
      UPDATE is REFUSED while either still lists the old value, so the
      order is load-bearing — drop, update, re-add. Getting it wrong
      does not corrupt data; it aborts schema.sql, and since
      `ensure_schema()` runs the whole file in one statement, the app
      simply fails to start. Loud, not silent.
    - **The constraint names are LOOKED UP, not hardcoded**, by scanning
      `pg_constraint` for definitions containing the old value. Read off
      a live PostgreSQL 16 rather than guessed: `branchops_tbo` carries
      the auto-generated `branchops_tbo_status_tbo_check` (its CHECK is
      inline in CREATE TABLE) while `branchops_pencairan` carries the
      hand-named `ck_bo_pencairan_status_tbo`. The re-add uses those same
      two names, so a migrated database and a freshly created one end up
      identical.
    - **A REAL BUG the rehearsal caught, and the general rule it gives.**
      The migration block was first written AFTER the `pc_backfill` block
      — and `pc_backfill` now writes the NEW value while the OLD CHECK is
      still installed. schema.sql died at that line. It only reproduces
      when `pencairan_status_tbo_migrasi` is absent, which is not this
      machine's state, so it would have shipped and then failed on some
      future rebuilt database. The block now sits BEFORE `pc_backfill`.
      **The rule: a block that widens a constraint must come before every
      block that writes the widened value.** Ordering inside schema.sql
      is behaviour, not tidiness.
    - `status_tbo` is `VARCHAR(16)`; `'Tidak ada TBO'` is 13 characters.
      A future term longer than 16 needs the column widened FIRST.
    - **The `<option value=...>` in branchops.html must equal the
      `_STATUS_BERANDA` key**, because that value is what goes out as
      `?status_tbo=`. Both moved together. A bookmarked URL still
      carrying `Dikecualikan` now matches no key and falls back to
      Outstanding — narrowing, never widening, which is the direction
      rule 10 requires.
    - **These pickers use `opt()`, NOT `optJaga()`, and that is
      deliberate.** Unlike `jenis_rekening` (free text, rule 26), this
      column has a CHECK, so a value outside the list cannot exist once
      the migration has run — there is nothing to preserve. Consistent
      with the other CHECK-backed pickers, `tipe_pembukaan` and
      `arus_dana`. The consequence to respect: during the window between
      new HTML and an un-migrated database, a row still holding
      `Dikecualikan` would display as `Outstanding` and a Simpan would
      write that. The code-only route closes the window by chaining
      `git pull && systemctl restart` in one command, and
      `ensure_schema()` migrates at start-up. **Never ship this HTML to a
      machine whose backend is not restarted in the same breath.** The
      reverse order is harmless: old HTML sending `Dikecualikan` to the
      new backend is rejected by `_pilihan` with a visible 400.
    - `deploy/buat-panduan.js` was updated; the **`.docx` was NOT
      regenerated** (owner's choice). So `Panduan-Pengguna-BranchOps.docx`
      on disk still says "Dikecualikan" until someone runs the generator.
      Noted here rather than left to be discovered by a reader of the
      manual.
    - Verified on a throwaway PostgreSQL **16** — the VPS's major version
      — in three scenarios. Old constraints plus old data: both CHECKs
      found and dropped by name, 52 TBO rows and 137 pencairan rows moved,
      `Lengkap` and `Outstanding` untouched, both CHECKs re-added with the
      new list, and the old value afterwards genuinely REFUSED by the
      constraint. With `pencairan_status_tbo_migrasi` already set — this
      machine's actual state — only the rename ran and the backfill stayed
      skipped. Run a third time: zero errors and identical counts, so the
      guard holds. Also: three Python files compile, both inline
      `<script>` blocks and `buat-panduan.js` parse under Node, the
      `_STATUS_BERANDA` keys and the Beranda `<option>` values were
      compared programmatically and agree, and in headless Chromium the
      dialog shows the three new options with `Tidak ada TBO` selected,
      Simpan sends it verbatim, and the string "Dikecualikan" appears
      nowhere on the screen. **The real database has not been touched.**

