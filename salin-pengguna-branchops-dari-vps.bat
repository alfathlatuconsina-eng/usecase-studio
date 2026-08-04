@echo off
REM ======================================================================
REM  Menyalin TABEL AKUN Branch Ops (branchops_users) dari VPS ke LOKAL
REM
REM  Hanya SATU tabel yang disentuh: branchops_users.
REM  Tabel data Branch Ops (it_break, pencairan, tbo, dll) TIDAK disentuh.
REM  Dashboard lain (PMO, People, Quality, E-Library) juga TIDAK disentuh.
REM
REM  ==================  BACA INI DULU  ==================
REM  Tabel ini berisi akun login Branch Ops beserta hash sandinya.
REM  Menyalinnya berarti akun LOKAL Anda DIGANTI oleh akun VPS.
REM
REM  Akibatnya: sandi Branch Ops lokal Anda berubah menjadi sandi VPS.
REM  Kalau Anda tidak tahu sandi akun di VPS, Anda TIDAK BISA MASUK
REM  ke Branch Ops lokal setelah skrip ini dijalankan.
REM
REM  Kalau itu terjadi, pulihkan dengan salah satu cara:
REM    a) kembalikan cadangan tabel yang dibuat skrip ini (perintah
REM       lengkapnya dicetak di akhir), atau
REM    b) buat ulang akun admin:
REM         cd backend
REM         py -3 init_db.py email-anda@contoh.com SandiBaru
REM       (init_db.py memperbarui sandi admin Branch Ops bila akun sudah ada)
REM  =====================================================
REM
REM  VPS tidak diubah sama sekali - hanya dibaca.
REM ======================================================================

REM  Jaring pengaman: kalau dibuka dengan KLIK DUA KALI, jalankan ulang di
REM  jendela cmd yang tidak menutup sendiri, supaya pesan tetap terbaca.
if not "%~1"=="lanjut" (
    cmd /k ""%~f0" lanjut"
    exit /b
)

setlocal EnableDelayedExpansion
cd /d "%~dp0"

set VPS=root@159.65.139.45
set VPSDB=pmo
set LOKALDB=pmo
set TABEL=branchops_users
set STAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%-%TIME:~0,2%%TIME:~3,2%
set STAMP=%STAMP: =0%
set BACKUP=backup-branchops_users-%STAMP%.sql
set FRESH=vps-branchops_users-%STAMP%.sql

echo.
echo ============================================================
echo   SALIN AKUN BRANCH OPS   VPS  -^>  LOKAL
echo ============================================================
echo   Tabel   : %TABEL%  ^(hanya ini^)
echo   Sumber  : %VPS% , database %VPSDB%   ^(hanya dibaca^)
echo   Tujuan  : localhost , database %LOKALDB%
echo.
echo   PERINGATAN: sandi login Branch Ops lokal Anda akan BERUBAH
echo   menjadi sandi yang berlaku di VPS.
echo.

REM ---------- cari PostgreSQL lokal ----------
set PGBIN=
for %%V in (18 17 16 15) do (
    if exist "C:\Program Files\PostgreSQL\%%V\bin\psql.exe" (
        if "!PGBIN!"=="" set "PGBIN=C:\Program Files\PostgreSQL\%%V\bin"
    )
)
if "%PGBIN%"=="" ( echo   GAGAL: PostgreSQL tidak ditemukan. & pause & exit /b 1 )
set "PSQL=%PGBIN%\psql.exe"
set "PGDUMP=%PGBIN%\pg_dump.exe"
echo   PostgreSQL lokal: %PGBIN%

where ssh >nul 2>&1
if not %errorlevel%==0 (
    echo   GAGAL: perintah ssh tidak ada.
    echo   Pasang lewat: Settings ^> Apps ^> Optional features ^> OpenSSH Client
    pause & exit /b 1
)

REM ---------- sandi postgres lokal ----------
echo.
set /p PGPASSWORD=  Kata sandi 'postgres' lokal:
"%PSQL%" -U postgres -h localhost -c "SELECT 1;" >nul 2>&1
if not %errorlevel%==0 ( echo   GAGAL: sandi salah atau layanan PostgreSQL mati. & pause & exit /b 1 )

REM ---------------------------------------------------------------- 0
echo.
echo [0/6] Memeriksa apakah tabel %TABEL% ada di VPS...

ssh -o ConnectTimeout=15 %VPS% "echo ok" >nul 2>&1
if not %errorlevel%==0 (
    echo   GAGAL: tidak bisa masuk ke %VPS%. Periksa koneksi dan kunci SSH.
    echo   Database lokal TIDAK disentuh.
    pause & exit /b 1
)

ssh %VPS% "sudo -u postgres psql -d %VPSDB% -tAc \"SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename='%TABEL%'\"" > _cek_ada.txt 2>nul
set ADA=0
if exist _cek_ada.txt set /p ADA=<_cek_ada.txt
del _cek_ada.txt 2>nul
set ADA=%ADA: =%
echo %ADA%| findstr /R "^[0-9][0-9]*$" >nul || set ADA=0

if %ADA% LEQ 0 (
    echo.
    echo   ============================================================
    echo   BERHENTI - tabel %TABEL% TIDAK ADA di VPS.
    echo.
    echo   Artinya modul Branch Ops belum pernah dipasang di VPS,
    echo   jadi tidak ada akun yang bisa disalin.
    echo.
    echo   Database lokal TIDAK disentuh. Tidak ada yang berubah.
    echo   ============================================================
    pause & exit /b 1
)

ssh %VPS% "sudo -u postgres psql -d %VPSDB% -tAc \"SELECT count(*) FROM %TABEL%\"" > _cek_n.txt 2>nul
set NAKUN=0
if exist _cek_n.txt set /p NAKUN=<_cek_n.txt
del _cek_n.txt 2>nul
set NAKUN=%NAKUN: =%
echo %NAKUN%| findstr /R "^[0-9][0-9]*$" >nul || set NAKUN=0
echo   Jumlah akun di VPS : %NAKUN%

if %NAKUN% LEQ 0 (
    echo.
    echo   BERHENTI - tabel ada tapi KOSONG, tidak ada akun untuk disalin.
    echo   Kalau diteruskan, akun lokal Anda terhapus dan Anda terkunci.
    echo   Database lokal TIDAK disentuh.
    pause & exit /b 1
)

REM ---------------------------------------------------------------- 1
echo.
echo [1/6] Akun yang ADA DI VPS ^(akan menggantikan yang lokal^):
echo ------------------------------------------------------------
ssh %VPS% "sudo -u postgres psql -d %VPSDB% -c \"SELECT id, email, role FROM %TABEL% ORDER BY id\""
echo ------------------------------------------------------------
echo   ^(hash sandi sengaja tidak ditampilkan^)

echo.
echo [2/6] Akun Branch Ops di LOKAL sekarang ^(akan HILANG^):
echo ------------------------------------------------------------
"%PSQL%" -U postgres -h localhost -d %LOKALDB% -c "SELECT id, email, role FROM %TABEL% ORDER BY id;" 2>nul
if not %errorlevel%==0 echo   ^(tabel %TABEL% lokal belum ada - tidak ada yang hilang^)
echo ------------------------------------------------------------

echo.
echo   Pastikan Anda TAHU SANDI salah satu akun VPS di atas.
echo   Kalau tidak, Anda akan terkunci dari Branch Ops lokal.
echo.
echo   Ketik  SALIN  untuk melanjutkan, atau apa saja untuk batal.
set /p KONFIRM=  ^>
if /I not "%KONFIRM%"=="SALIN" ( echo   Dibatalkan. Tidak ada yang berubah. & pause & exit /b 0 )

REM ---------------------------------------------------------------- 3
echo.
echo [3/6] Mencadangkan tabel %TABEL% lokal...
"%PGDUMP%" -U postgres -h localhost --clean --if-exists -t %TABEL% %LOKALDB% > "%BACKUP%" 2>nul
set SZ=0
for %%A in ("%BACKUP%") do set SZ=%%~zA
if "!SZ!"=="" set SZ=0
if !SZ! LSS 200 (
    echo   Cadangan gagal / tabel lokal belum ada ^(!SZ! byte^).
    echo   Lanjut tanpa cadangan? Ketik LANJUT bila ya.
    set /p K2=  ^>
    if /I not "!K2!"=="LANJUT" ( echo   Dibatalkan. & pause & exit /b 1 )
) else (
    echo   Tersimpan: %BACKUP%  ^(!SZ! byte^)
)

REM ---------------------------------------------------------------- 4
echo.
echo [4/6] Menarik tabel %TABEL% dari VPS ^(hanya membaca^)...
ssh %VPS% "sudo -u postgres pg_dump --clean --if-exists -t %TABEL% %VPSDB%" > "%FRESH%"
if not %errorlevel%==0 (
    echo   GAGAL menarik dari VPS. Lokal TIDAK disentuh.
    echo   Cadangan tetap ada: %BACKUP%
    del "%FRESH%" 2>nul
    pause & exit /b 1
)

REM ---------------------------------------------------------------- 5
echo.
echo [5/6] Memeriksa hasil tarikan sebelum diterapkan...
set FSZ=0
for %%A in ("%FRESH%") do set FSZ=%%~zA
if "%FSZ%"=="" set FSZ=0
echo   Ukuran berkas : %FSZ% byte
if %FSZ% LSS 500 (
    echo   GAGAL: berkas terlalu kecil, hampir pasti tidak lengkap.
    echo   Lokal TIDAK disentuh. Cadangan: %BACKUP%
    pause & exit /b 1
)
findstr /C:"PostgreSQL database dump complete" "%FRESH%" >nul
if not %errorlevel%==0 (
    echo   GAGAL: penanda akhir dump tidak ditemukan - tarikan terpotong.
    echo   Lokal TIDAK disentuh. Cadangan: %BACKUP%
    pause & exit /b 1
)
REM  Palang terakhir: dump HARUS hanya berisi tabel branchops_users.
findstr /R /C:"^CREATE TABLE " "%FRESH%" | findstr /V /C:"%TABEL%" >nul
if %errorlevel%==0 (
    echo   GAGAL: dump berisi tabel selain %TABEL% - tidak aman diterapkan.
    echo   Lokal TIDAK disentuh. Cadangan: %BACKUP%
    pause & exit /b 1
)
echo   Tarikan lengkap dan hanya berisi %TABEL%.

REM ---------------------------------------------------------------- 6
echo.
echo [6/6] Menerapkan ke database lokal...
"%PSQL%" -U postgres -h localhost -d %LOKALDB% -v ON_ERROR_STOP=0 -q -f "%FRESH%" 2>nul

echo.
echo   Akun Branch Ops di LOKAL sekarang:
echo ------------------------------------------------------------
"%PSQL%" -U postgres -h localhost -d %LOKALDB% -c "SELECT id, email, role FROM %TABEL% ORDER BY id;"
echo ------------------------------------------------------------

echo.
echo ============================================================
echo   SELESAI
echo.
echo   Cadangan akun lokal lama : %BACKUP%
echo   Salinan mentah dari VPS  : %FRESH%
echo.
echo   KALAU ANDA TIDAK BISA MASUK ke Branch Ops lokal:
echo.
echo   Cara 1 - kembalikan akun lama:
echo     "%PSQL%" -U postgres -h localhost -d %LOKALDB% -f "%BACKUP%"
echo.
echo   Cara 2 - buat ulang akun admin dengan sandi baru:
echo     cd backend
echo     py -3 init_db.py email-anda@contoh.com SandiBaru
echo.
echo   Catatan: kedua berkas .sql di atas berisi hash sandi.
echo   Hash tidak bisa dibaca balik, tapi tetap jangan disimpan
echo   sembarangan dan jangan dimasukkan ke Git.
echo ============================================================
echo.
pause
