@echo off
REM ======================================================================
REM  Menyalin database PMO dari VPS ke komputer lokal
REM
REM  Urutan sengaja dibuat begini: tidak ada yang dihapus di lokal
REM  sebelum tarikan dari VPS terbukti lengkap dan masuk akal.
REM
REM    1. Cadangkan database lokal yang sekarang  -> berkas bertanggal
REM    2. Tarik salinan segar dari VPS (pg_dump, hanya MEMBACA)
REM    3. Periksa hasil tarikan: ukuran, penanda, jumlah tabel
REM    4. Baru timpa database lokal
REM    5. Bandingkan jumlah baris sesudahnya
REM
REM  VPS tidak diubah sama sekali. pg_dump hanya membaca.
REM ======================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set VPS=root@159.65.139.45
set VPSDB=pmo
set LOKALDB=pmo
set STAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%-%TIME:~0,2%%TIME:~3,2%
set STAMP=%STAMP: =0%
set BACKUP=backup-lokal-%STAMP%.sql
set FRESH=vps-%STAMP%.sql

echo.
echo ============================================================
echo   SALIN DATABASE VPS  -^>  LOKAL
echo ============================================================
echo   Sumber  : %VPS% , database %VPSDB%   (hanya dibaca)
echo   Tujuan  : localhost , database %LOKALDB%   (AKAN DITIMPA)
echo.
echo   Cadangan lokal akan disimpan sebagai:
echo     %BACKUP%
echo.

REM ---------- cari psql ----------
set PSQL=
for %%V in (18 17 16 15) do (
    if exist "C:\Program Files\PostgreSQL\%%V\bin\psql.exe" (
        if "!PSQL!"=="" set "PGBIN=C:\Program Files\PostgreSQL\%%V\bin"
    )
)
if "%PGBIN%"=="" ( echo   GAGAL: PostgreSQL tidak ditemukan. & pause & exit /b 1 )
set "PSQL=%PGBIN%\psql.exe"
set "PGDUMP=%PGBIN%\pg_dump.exe"
echo   PostgreSQL lokal: %PGBIN%

where ssh >nul 2>&1
if not %errorlevel%==0 (
    echo.
    echo   GAGAL: perintah ssh tidak ada.
    echo   Pasang lewat: Settings ^> Apps ^> Optional features ^> OpenSSH Client
    echo.
    pause & exit /b 1
)

REM ---------- password postgres lokal ----------
echo.
set /p PGPASSWORD=  Kata sandi 'postgres' lokal:
"%PSQL%" -U postgres -h localhost -c "SELECT 1;" >nul 2>&1
if not %errorlevel%==0 ( echo   GAGAL: sandi salah atau layanan PostgreSQL mati. & pause & exit /b 1 )

echo.
echo   Ketik  SALIN  untuk melanjutkan, atau apa saja untuk batal.
set /p KONFIRM=  ^>
if /I not "%KONFIRM%"=="SALIN" ( echo   Dibatalkan. Tidak ada yang berubah. & pause & exit /b 0 )

REM ---------------------------------------------------------------- 1
echo.
echo [1/5] Mencadangkan database lokal yang sekarang...
"%PGDUMP%" -U postgres -h localhost --clean --if-exists %LOKALDB% > "%BACKUP%" 2>nul
if not %errorlevel%==0 (
    echo   Database lokal '%LOKALDB%' belum ada atau gagal dibaca.
    echo   Lanjut tanpa cadangan? Ketik LANJUT bila ya.
    set /p K2=  ^>
    if /I not "!K2!"=="LANJUT" ( echo   Dibatalkan. & pause & exit /b 1 )
) else (
    for %%A in ("%BACKUP%") do set SZ=%%~zA
    echo   Tersimpan: %BACKUP%  ^(!SZ! byte^)
    if !SZ! LSS 1000 (
        echo   PERINGATAN: cadangan mencurigakan kecil. Dibatalkan demi keamanan.
        pause & exit /b 1
    )
)

REM ---------------------------------------------------------------- 2
echo.
echo [2/5] Menarik salinan dari VPS ^(hanya membaca, VPS tidak diubah^)...
ssh %VPS% "sudo -u postgres pg_dump --clean --if-exists %VPSDB%" > "%FRESH%"
if not %errorlevel%==0 (
    echo   GAGAL menarik dari VPS. Periksa koneksi SSH.
    echo   Database lokal TIDAK disentuh. Cadangan tetap ada: %BACKUP%
    del "%FRESH%" 2>nul
    pause & exit /b 1
)

REM ---------------------------------------------------------------- 3
echo.
echo [3/5] Memeriksa hasil tarikan sebelum apa pun ditimpa...
for %%A in ("%FRESH%") do set FSZ=%%~zA
echo   Ukuran berkas: %FSZ% byte
if %FSZ% LSS 5000 (
    echo   GAGAL: berkas terlalu kecil, hampir pasti tidak lengkap.
    echo   Database lokal TIDAK disentuh.
    pause & exit /b 1
)
findstr /C:"PostgreSQL database dump complete" "%FRESH%" >nul
if not %errorlevel%==0 (
    echo   GAGAL: penanda akhir dump tidak ditemukan - tarikan terpotong.
    echo   Database lokal TIDAK disentuh.
    pause & exit /b 1
)
for /f %%C in ('findstr /R /C:"^CREATE TABLE" "%FRESH%" ^| find /c /v ""') do set NTAB=%%C
echo   Tabel di dalam dump: %NTAB%
if %NTAB% LSS 5 (
    echo   GAGAL: jumlah tabel tidak wajar. Database lokal TIDAK disentuh.
    pause & exit /b 1
)
echo   Tarikan terlihat lengkap.

REM ---------------------------------------------------------------- 4
echo.
echo [4/5] Menerapkan ke database lokal...
"%PSQL%" -U postgres -h localhost -tAc "SELECT 1 FROM pg_database WHERE datname='%LOKALDB%'" | findstr "1" >nul
if not %errorlevel%==0 "%PSQL%" -U postgres -h localhost -c "CREATE DATABASE %LOKALDB%;" >nul
"%PSQL%" -U postgres -h localhost -d %LOKALDB% -v ON_ERROR_STOP=0 -q -f "%FRESH%" 2>nul
if not %errorlevel%==0 (
    echo   Ada pesan saat menerapkan. Lanjut ke pemeriksaan hasil.
)

REM ---------------------------------------------------------------- 5
echo.
echo [5/5] Hasil di database lokal sekarang:
"%PSQL%" -U postgres -h localhost -d %LOKALDB% -c "SELECT (SELECT count(*) FROM projects) AS proyek, (SELECT count(*) FROM users) AS pengguna_pmo, (SELECT count(*) FROM people_training) AS pelatihan, (SELECT count(*) FROM quality_branches) AS survei, (SELECT count(*) FROM elibrary_documents) AS dokumen;"

echo.
echo ============================================================
echo   SELESAI
echo.
echo   Cadangan sebelum tindakan : %BACKUP%
echo   Salinan mentah dari VPS   : %FRESH%
echo.
echo   Keduanya berisi data internal. Simpan aman, hapus bila
echo   sudah tidak diperlukan.
echo.
echo   Untuk kembali ke kondisi sebelum skrip ini:
echo     "%PSQL%" -U postgres -h localhost -d %LOKALDB% -f "%BACKUP%"
echo.
echo   Langkah berikutnya: jalankan run_local.bat.
echo   Tabel branchops_* akan dibuat otomatis saat aplikasi start.
echo ============================================================
echo.
pause
