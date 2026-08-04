@echo off
REM ======================================================================
REM  Menyamakan sandi admin@mncbank.co.id di VPS dengan yang di LOKAL
REM  untuk 4 modul: PMO, People Development, Service Quality, E-Library.
REM
REM  Cara kerja (aman):
REM   - Sandi disimpan sebagai hash bcrypt (tidak bisa dibaca balik).
REM   - Skrip MENYALIN hash dari database lokal ke database VPS.
REM   - Tidak ada sandi teks biasa yang diketik atau terlihat.
REM   - Hasilnya: sandi di VPS PERSIS sama dengan di lokal.
REM
REM  Yang disentuh HANYA baris admin@mncbank.co.id pada 4 tabel user.
REM  Modul Branch Ops tidak termasuk (tidak diminta).
REM ======================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set VPS=root@159.65.139.45
set VPSDB=pmo
set LOKALDB=pmo
set EMAIL=admin@mncbank.co.id
set SQLFILE=%TEMP%\set-admin-vps-%RANDOM%.sql

echo.
echo ============================================================
echo   SAMAKAN SANDI ADMIN  LOKAL  -^>  VPS
echo ============================================================
echo   Akun  : %EMAIL%
echo   Modul : PMO, People Development, Service Quality, E-Library
echo   Tujuan: %VPS% , database %VPSDB%
echo.

REM ---------- cari psql lokal ----------
set PGBIN=
for %%V in (18 17 16 15) do (
    if exist "C:\Program Files\PostgreSQL\%%V\bin\psql.exe" (
        if "!PGBIN!"=="" set "PGBIN=C:\Program Files\PostgreSQL\%%V\bin"
    )
)
if "%PGBIN%"=="" ( echo   GAGAL: PostgreSQL lokal tidak ditemukan. & pause & exit /b 1 )
set "PSQL=%PGBIN%\psql.exe"
echo   PostgreSQL lokal: %PGBIN%

where ssh >nul 2>&1
if not %errorlevel%==0 ( echo   GAGAL: perintah ssh tidak ada. Pasang OpenSSH Client. & pause & exit /b 1 )

REM ---------- sandi postgres lokal ----------
echo.
set /p PGPASSWORD=  Kata sandi 'postgres' lokal:
"%PSQL%" -U postgres -h localhost -c "SELECT 1;" >nul 2>&1
if not %errorlevel%==0 ( echo   GAGAL: sandi salah atau PostgreSQL lokal mati. & pause & exit /b 1 )

echo.
echo   Ketik  SAMAKAN  untuk melanjutkan, atau apa saja untuk batal.
set /p KONFIRM=  ^>
if /I not "%KONFIRM%"=="SAMAKAN" ( echo   Dibatalkan. Tidak ada yang berubah. & pause & exit /b 0 )

REM ---------------------------------------------------------------- 1
echo.
echo [1/4] Membaca hash sandi dari database lokal + menyusun perintah...
"%PSQL%" -U postgres -h localhost -d %LOKALDB% -X -A -t -q -o "%SQLFILE%" -c "SELECT string_agg(s, chr(10)) FROM (SELECT 'UPDATE users SET pw_hash=' || quote_literal(pw_hash) || ' WHERE lower(email)=lower(' || quote_literal('%EMAIL%') || ');' AS s FROM users WHERE lower(email)=lower('%EMAIL%') UNION ALL SELECT 'UPDATE people_users SET pw_hash=' || quote_literal(pw_hash) || ' WHERE lower(email)=lower(' || quote_literal('%EMAIL%') || ');' FROM people_users WHERE lower(email)=lower('%EMAIL%') UNION ALL SELECT 'UPDATE quality_users SET pw_hash=' || quote_literal(pw_hash) || ' WHERE lower(email)=lower(' || quote_literal('%EMAIL%') || ');' FROM quality_users WHERE lower(email)=lower('%EMAIL%') UNION ALL SELECT 'UPDATE elibrary_users SET pw_hash=' || quote_literal(pw_hash) || ' WHERE lower(email)=lower(' || quote_literal('%EMAIL%') || ');' FROM elibrary_users WHERE lower(email)=lower('%EMAIL%')) q;"
if not exist "%SQLFILE%" ( echo   GAGAL menyusun perintah. Batal. & pause & exit /b 1 )

REM ---- periksa jumlah baris UPDATE ----
for /f %%C in ('findstr /R /C:"^UPDATE" "%SQLFILE%" ^| find /c /v ""') do set NUP=%%C
echo   Modul dengan akun %EMAIL% di lokal: %NUP%  ^(diharapkan 4^)
findstr /R /C:"^UPDATE" "%SQLFILE%" | findstr /O "UPDATE" >nul
echo   Rincian modul yang ditemukan:
for /f "tokens=2" %%T in ('findstr /R /C:"^UPDATE" "%SQLFILE%"') do echo      - %%T
if %NUP% LSS 1 (
    echo   GAGAL: tidak ada akun ditemukan di lokal. Batal.
    del "%SQLFILE%" 2^>nul & pause & exit /b 1
)
if %NUP% LSS 4 (
    echo.
    echo   CATATAN: sebagian modul belum punya akun ini di LOKAL, jadi
    echo   tidak bisa disalin. Yang ada tetap disamakan. Lanjut? Ketik LANJUT.
    set /p K2=  ^>
    if /I not "!K2!"=="LANJUT" ( echo   Dibatalkan. & del "%SQLFILE%" 2^>nul & pause & exit /b 0 )
)

REM ---------------------------------------------------------------- 2
echo.
echo [2/4] Menerapkan ke VPS...
type "%SQLFILE%" | ssh %VPS% "sudo -u postgres psql -d %VPSDB% -v ON_ERROR_STOP=1"
set APPLYRC=%errorlevel%

REM ---------------------------------------------------------------- 3
echo.
echo [3/4] Membersihkan berkas sementara ^(berisi hash^)...
del "%SQLFILE%" 2>nul

if not %APPLYRC%==0 (
    echo.
    echo   GAGAL menerapkan ke VPS. Tidak ada perubahan tuntas. Coba lagi.
    pause & exit /b 1
)

REM ---------------------------------------------------------------- 4
echo.
echo ============================================================
echo   [4/4] SELESAI
echo.
echo   Setiap baris "UPDATE 1" di atas = 1 akun berhasil disamakan.
echo   "UPDATE 0" = akun itu belum ada di VPS ^(beri tahu saya^).
echo.
echo   Coba login memakai %EMAIL% + sandi yang sama seperti localhost:
echo     https://usecase-studio.xyz/login            (PMO)
echo     https://usecase-studio.xyz/people-login     (People)
echo     https://usecase-studio.xyz/quality-login    (Service Quality)
echo     https://usecase-studio.xyz/elibrary-login   (E-Library)
echo ============================================================
echo.
pause
