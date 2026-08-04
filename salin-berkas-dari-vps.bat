@echo off
REM ======================================================================
REM  Menyalin BERKAS KODE dari VPS ke komputer lokal
REM  (Copy CODE FILES from the VPS down to this PC)
REM
REM  Pasangan dari sync-dari-vps.bat:
REM     sync-dari-vps.bat       -> menyalin DATABASE
REM     salin-berkas-dari-vps.bat (berkas ini) -> menyalin BERKAS KODE
REM
REM  Pengaman utama: git.
REM  Skrip ini menolak jalan bila masih ada perubahan lokal yang belum
REM  di-commit. Jadi sebelum apa pun ditimpa, selalu ada titik pulih.
REM  Sesudah selesai:  git status      -> lihat apa yang berubah
REM                    git checkout .  -> batalkan semuanya
REM
REM  VPS TIDAK diubah sama sekali. Hanya dibaca.
REM
REM  TIDAK ikut disalin, disengaja:
REM     .env            -> sandi VPS berbeda dari lokal. Jangan tertimpa.
REM     venv/           -> lingkungan Python Linux, tidak jalan di Windows.
REM     __pycache__/    -> berkas sementara.
REM ======================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set VPS=root@159.65.139.45
set APPDIR=/opt/pmo
set STAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%-%TIME:~0,2%%TIME:~3,2%
set STAMP=%STAMP: =0%
set ARSIP=vps-berkas-%STAMP%.tar.gz

echo.
echo ============================================================
echo   SALIN BERKAS KODE   VPS  -^>  LOKAL
echo ============================================================
echo   Sumber : %VPS%:%APPDIR%   (hanya dibaca)
echo   Tujuan : folder ini             (AKAN DITIMPA)
echo.

REM ---------------------------------------------------------------- 0
REM  Perkakas yang dibutuhkan
where ssh >nul 2>&1
if not %errorlevel%==0 (
    echo   GAGAL: perintah 'ssh' tidak ada.
    echo   Pasang lewat: Settings ^> Apps ^> Optional features ^> OpenSSH Client
    pause & exit /b 1
)
where tar >nul 2>&1
if not %errorlevel%==0 (
    echo   GAGAL: perintah 'tar' tidak ada. Perlu Windows 10 versi 1803 ke atas.
    pause & exit /b 1
)
where git >nul 2>&1
if not %errorlevel%==0 (
    echo   GAGAL: perintah 'git' tidak ada. Git dipakai sebagai pengaman.
    pause & exit /b 1
)

REM ---------------------------------------------------------------- 1
REM  PENGAMAN: tolak jalan bila ada perubahan lokal yang belum tersimpan
echo [1/5] Memeriksa pengaman git...
git rev-parse --is-inside-work-tree >nul 2>&1
if not %errorlevel%==0 (
    echo   GAGAL: folder ini bukan repositori git. Tidak ada jaring pengaman.
    pause & exit /b 1
)
for /f %%C in ('git status --porcelain ^| find /c /v ""') do set NDIRTY=%%C
if not "%NDIRTY%"=="0" (
    echo.
    echo   BERHENTI: ada %NDIRTY% berkas lokal yang belum di-commit.
    echo   Kalau diteruskan, perubahan itu bisa hilang tertimpa berkas VPS.
    echo.
    echo   Simpan dulu:
    echo       git add -A
    echo       git commit -m "simpan sebelum tarik berkas dari VPS"
    echo.
    pause & exit /b 1
)
for /f %%H in ('git rev-parse --short HEAD') do set TITIKPULIH=%%H
echo   Bersih. Titik pulih: %TITIKPULIH%

REM ---------------------------------------------------------------- 2
echo.
echo   Ketik  SALIN  untuk melanjutkan, atau apa saja untuk batal.
set /p KONFIRM=  ^>
if /I not "%KONFIRM%"=="SALIN" ( echo   Dibatalkan. Tidak ada yang berubah. & pause & exit /b 0 )

echo.
echo [2/5] Menarik berkas dari VPS ^(hanya membaca^)...
ssh %VPS% "cd %APPDIR% && tar czf - --exclude='.env' --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' --exclude='*.sql' backend frontend pptx 2>/dev/null" > "%ARSIP%"
if not %errorlevel%==0 (
    echo   GAGAL menarik dari VPS. Periksa koneksi SSH atau APPDIR.
    echo   Berkas lokal TIDAK disentuh.
    del "%ARSIP%" 2>nul
    pause & exit /b 1
)

REM ---------------------------------------------------------------- 3
echo.
echo [3/5] Memeriksa arsip sebelum apa pun ditimpa...
for %%A in ("%ARSIP%") do set ASZ=%%~zA
echo   Ukuran arsip: %ASZ% byte
if %ASZ% LSS 20000 (
    echo   GAGAL: arsip terlalu kecil, hampir pasti tidak lengkap.
    echo   Berkas lokal TIDAK disentuh.
    pause & exit /b 1
)
tar -tzf "%ARSIP%" >nul 2>&1
if not %errorlevel%==0 (
    echo   GAGAL: arsip rusak / terpotong. Berkas lokal TIDAK disentuh.
    pause & exit /b 1
)
for /f %%C in ('tar -tzf "%ARSIP%" ^| find /c /v ""') do set NBERKAS=%%C
echo   Berkas di dalam arsip: %NBERKAS%
if %NBERKAS% LSS 10 (
    echo   GAGAL: jumlah berkas tidak wajar. Berkas lokal TIDAK disentuh.
    pause & exit /b 1
)
tar -tzf "%ARSIP%" | findstr /I "app.py" >nul
if not %errorlevel%==0 (
    echo   GAGAL: backend/app.py tidak ada di arsip. Isinya tidak seperti dugaan.
    echo   Berkas lokal TIDAK disentuh.
    pause & exit /b 1
)
echo   Arsip terlihat lengkap.

REM ---------------------------------------------------------------- 4
echo.
echo [4/5] Menimpa berkas lokal...
tar -xzf "%ARSIP%"
if not %errorlevel%==0 (
    echo   Ada masalah saat membuka arsip.
    echo   PULIHKAN dengan:  git checkout .
    pause & exit /b 1
)
echo   Selesai dibuka.

REM ---------------------------------------------------------------- 5
echo.
echo [5/5] Apa yang berubah dibanding sebelum skrip ini:
echo.
git status --short
echo.
for /f %%C in ('git status --porcelain ^| find /c /v ""') do set NUBAH=%%C
echo   Jumlah berkas berubah: %NUBAH%
if "%NUBAH%"=="0" echo   ^(Tidak ada perbedaan - berkas VPS sama persis dengan lokal.^)

echo.
echo ============================================================
echo   SELESAI
echo.
echo   Arsip mentah dari VPS : %ARSIP%
echo   Titik pulih git       : %TITIKPULIH%
echo.
echo   Lihat isi perubahan sebuah berkas:
echo       git diff frontend/branchops.html
echo.
echo   BATALKAN SEMUA perubahan dari VPS:
echo       git checkout .
echo.
echo   Bila hasilnya sudah benar, simpan:
echo       git add -A
echo       git commit -m "salin berkas dari VPS"
echo.
echo   CATATAN: berkas .env TIDAK ikut disalin, disengaja.
echo   Sandi dan kunci JWT di VPS memang berbeda dari lokal.
echo.
echo   Untuk databasenya, jalankan: sync-dari-vps.bat
echo ============================================================
echo.
pause
