@echo off
REM ======================================================================
REM  MENDORONG modul Branch Operations dari LOKAL  ->  VPS (produksi)
REM
REM  Ini adalah kebalikan dari sync-dari-vps.bat.
REM  Yang didorong: kode backend branchops, berkas frontend branchops,
REM  dan DATA tabel branchops_* (pencairan, TBO, dll).
REM
REM  PENTING soal keamanan:
REM   - Tabel milik 4 dashboard lain (PMO, People, Quality, E-Library)
REM     TIDAK disentuh. Hanya tabel branchops_* yang didorong.
REM   - VPS dicadangkan LEBIH DULU sebelum apa pun ditimpa.
REM   - Data ini berisi data nasabah asli. VPS bersifat publik.
REM     Anda sudah menyetujui ini secara sadar.
REM
REM  Urutan:
REM    0. Temukan folder aplikasi + nama service di VPS (sekali saja)
REM    1. Cadangkan database VPS yang sekarang  -> berkas bertanggal
REM    2. Dorong berkas kode + frontend (scp)
REM    3. Pasang openpyxl + restart aplikasi di VPS
REM    4. Dorong DATA tabel branchops_* (pg_dump lokal | psql VPS)
REM    5. Periksa jumlah baris di VPS
REM ======================================================================
REM  Jaring pengaman: kalau dibuka dengan KLIK DUA KALI, jalankan ulang di
REM  jendela cmd yang tidak menutup sendiri. Penting untuk dorongan ke
REM  produksi - kalau ada kesalahan, pesannya harus tetap terbaca.
if not "%~1"=="lanjut" (
    cmd /k ""%~f0" lanjut"
    exit /b
)

setlocal EnableDelayedExpansion
cd /d "%~dp0"

set VPS=root@159.65.139.45
set VPSDB=pmo
set LOKALDB=pmo

REM ====================================================================
REM  ISI DUA NILAI INI DULU (lihat LANGKAH 0 di bawah untuk menemukannya)
REM ====================================================================
REM  Folder aplikasi di VPS (yang berisi backend\ dan frontend\):
set APPDIR=/opt/pmo
REM  Perintah restart aplikasi di VPS (sesuaikan nama service):
set RESTART=systemctl restart pmo
REM  Perintah pip di VPS (venv aplikasi, dikonfirmasi dari pmo.service):
set PIP=/opt/pmo/backend/venv/bin/pip
REM ====================================================================

set STAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%-%TIME:~0,2%%TIME:~3,2%
set STAMP=%STAMP: =0%
set VPSBACKUP=vps-sebelum-push-%STAMP%.sql

echo.
echo ============================================================
echo   DORONG BRANCH OPS  LOKAL  -^>  VPS
echo ============================================================
echo   Tujuan : %VPS% , database %VPSDB%   (AKAN DITIMPA sebagian)
echo   Folder : %APPDIR%
echo   Restart: %RESTART%
echo.
echo   Hanya tabel branchops_* dan berkas branchops yang didorong.
echo   Dashboard lain tidak disentuh.
echo.

REM ---------- cari pg_dump lokal ----------
set PGBIN=
for %%V in (18 17 16 15) do (
    if exist "C:\Program Files\PostgreSQL\%%V\bin\pg_dump.exe" (
        if "!PGBIN!"=="" set "PGBIN=C:\Program Files\PostgreSQL\%%V\bin"
    )
)
if "%PGBIN%"=="" ( echo   GAGAL: PostgreSQL lokal tidak ditemukan. & pause & exit /b 1 )
set "PSQL=%PGBIN%\psql.exe"
set "PGDUMP=%PGBIN%\pg_dump.exe"
echo   PostgreSQL lokal: %PGBIN%

where ssh >nul 2>&1
if not %errorlevel%==0 ( echo   GAGAL: perintah ssh/scp tidak ada. Pasang OpenSSH Client. & pause & exit /b 1 )

REM ---------- sandi postgres lokal ----------
echo.
set /p PGPASSWORD=  Kata sandi 'postgres' lokal:
"%PSQL%" -U postgres -h localhost -c "SELECT 1;" >nul 2>&1
if not %errorlevel%==0 ( echo   GAGAL: sandi salah atau PostgreSQL lokal mati. & pause & exit /b 1 )

echo.
echo   ============================================================
echo   LANGKAH 0 (opsional, jalankan SEKALI untuk menemukan nilai
echo   APPDIR dan nama service, lalu isi di atas berkas ini):
echo.
echo     ssh %VPS% "find / -name app.py -path '*backend*' 2^>/dev/null"
echo     ssh %VPS% "systemctl list-units --type=service ^| grep -iE 'pmo^|gunicorn^|flask'"
echo   ============================================================
echo.
echo   Ketik  DORONG  untuk melanjutkan, atau apa saja untuk batal.
set /p KONFIRM=  ^>
if /I not "%KONFIRM%"=="DORONG" ( echo   Dibatalkan. Tidak ada yang berubah. & pause & exit /b 0 )

REM ---------------------------------------------------------------- 1
echo.
echo [1/5] Mencadangkan SELURUH database VPS lebih dulu (hanya membaca)...
ssh %VPS% "sudo -u postgres pg_dump --clean --if-exists %VPSDB%" > "%VPSBACKUP%"
if not %errorlevel%==0 ( echo   GAGAL menarik cadangan VPS. Batal, VPS tidak disentuh. & del "%VPSBACKUP%" 2^>nul & pause & exit /b 1 )
set VSZ=0
for %%A in ("%VPSBACKUP%") do set VSZ=%%~zA
if "!VSZ!"=="" set VSZ=0
echo   Cadangan VPS tersimpan: %VPSBACKUP%  ^(!VSZ! byte^)
findstr /C:"PostgreSQL database dump complete" "%VPSBACKUP%" >nul
if not %errorlevel%==0 ( echo   GAGAL: cadangan VPS terpotong. Batal demi keamanan. & pause & exit /b 1 )
if !VSZ! LSS 5000 ( echo   GAGAL: cadangan VPS terlalu kecil. Batal. & pause & exit /b 1 )
echo   Cadangan terlihat lengkap. Untuk mengembalikan VPS bila perlu:
echo     ssh %VPS% "sudo -u postgres psql -d %VPSDB%" ^< "%VPSBACKUP%"

REM ---------------------------------------------------------------- 2
echo.
echo [2/5] Mendorong berkas kode + frontend ke VPS...
scp -r "backend\branchops" %VPS%:%APPDIR%/backend/
scp "backend\app.py"          %VPS%:%APPDIR%/backend/app.py
scp "backend\requirements.txt" %VPS%:%APPDIR%/backend/requirements.txt
scp "frontend\branchops.html"       %VPS%:%APPDIR%/frontend/branchops.html
scp "frontend\branchops-login.html" %VPS%:%APPDIR%/frontend/branchops-login.html
scp "frontend\landing.html"         %VPS%:%APPDIR%/frontend/landing.html
scp "frontend\img-branchops.png"    %VPS%:%APPDIR%/frontend/img-branchops.png
if not %errorlevel%==0 ( echo   PERINGATAN: sebagian scp gagal. Periksa APPDIR. Data BELUM didorong. & pause & exit /b 1 )
echo   Berkas terkirim.

REM ---------------------------------------------------------------- 3
echo.
echo [3/5] Membersihkan cache Python basi, memasang openpyxl, restart...
REM  scp ikut membawa folder __pycache__ dari Windows. Dihapus supaya VPS
REM  pasti menjalankan kode .py yang baru saja dikirim, bukan sisa lama.
ssh %VPS% "rm -rf %APPDIR%/backend/__pycache__ %APPDIR%/backend/branchops/__pycache__"
ssh %VPS% "cd %APPDIR% && %PIP% install -r backend/requirements.txt && %RESTART%"
if not %errorlevel%==0 ( echo   PERINGATAN: pemasangan/restart bermasalah. Lanjut, tapi periksa manual. )

REM  Pastikan berkas penyamaran benar-benar sampai DAN tersambung.
REM  Ini inti dorongan kali ini - kalau gagal, nama nasabah asli akan
REM  tampil di server publik.
echo.
echo   Memeriksa penyamaran nama di VPS:
ssh %VPS% "test -f %APPDIR%/backend/branchops/masking.py && echo '    masking.py   : ADA' || echo '    masking.py   : TIDAK ADA - GAGAL'"
ssh %VPS% "grep -c '_out(' %APPDIR%/backend/branchops/__init__.py | xargs -I{} echo '    _out() dipakai: {} kali (harus >= 7)'"
ssh %VPS% "grep -q 'return True' %APPDIR%/backend/branchops/masking.py && echo '    berlaku untuk semua peran: ya' || echo '    PERIKSA: should_mask() mungkin versi lama'"

REM  Pastikan hak menu ikut terpasang. Kalau privileges.py tidak sampai,
REM  seluruh pembatasan menu hilang dan /dash kembali terbuka untuk siapa pun.
echo.
echo   Memeriksa hak menu di VPS:
ssh %VPS% "test -f %APPDIR%/backend/branchops/privileges.py && echo '    privileges.py    : ADA' || echo '    privileges.py    : TIDAK ADA - GAGAL'"
ssh %VPS% "grep -c 'require_menu' %APPDIR%/backend/branchops/__init__.py | xargs -I{} echo '    require_menu     : {} pemakaian (harus >= 12)'"
ssh %VPS% "grep -q 'privileges.boleh' %APPDIR%/backend/branchops/__init__.py && echo '    penjaga /dash    : terpasang' || echo '    penjaga /dash    : TIDAK ADA - celah masih terbuka'"
ssh %VPS% "grep -q 'branchops_role_menus' %APPDIR%/backend/branchops/schema.sql && echo '    tabel hak menu   : ada di schema.sql' || echo '    tabel hak menu   : TIDAK ADA - GAGAL'"
ssh %VPS% "sudo -u postgres psql -d %VPSDB% -tAc \"SELECT count(*) FROM pg_tables WHERE tablename='branchops_role_menus'\" | xargs -I{} echo '    tabel di database: {} (1 = sudah dibuat saat restart)'"

REM ---------------------------------------------------------------- 4
echo.
echo [4/5] Mendorong DATA tabel branchops_* (hanya branchops)...
"%PGDUMP%" -U postgres -h localhost -t "branchops_*" --clean --if-exists %LOKALDB% | ssh %VPS% "sudo -u postgres psql -d %VPSDB%"
if not %errorlevel%==0 ( echo   PERINGATAN: dorong data bermasalah. Cadangan VPS masih ada: %VPSBACKUP% & pause & exit /b 1 )
echo   Data branchops_* terkirim.

REM ---------------------------------------------------------------- 5
echo.
echo [5/5] Jumlah baris di VPS sekarang:
ssh %VPS% "sudo -u postgres psql -d %VPSDB% -c \"SELECT (SELECT count(*) FROM branchops_pencairan) AS pencairan, (SELECT count(*) FROM branchops_tbo) AS tbo, (SELECT count(*) FROM branchops_branches) AS cabang;\""

echo.
echo ============================================================
echo   SELESAI
echo.
echo   Cadangan VPS sebelum push : %VPSBACKUP%   (simpan aman)
echo   Untuk MENGEMBALIKAN VPS ke kondisi sebelum push:
echo     ssh %VPS% "sudo -u postgres psql -d %VPSDB%" ^< "%VPSBACKUP%"
echo.
echo   Buka https://usecase-studio.xyz/branchops untuk memeriksa.
echo ============================================================
echo.
pause
