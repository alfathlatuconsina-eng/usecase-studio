@echo off
REM ===================================================================
REM  6 - IMPOR STRUKTUR + ISI MODUL BRANCH OPS DARI VPS KE LOKAL
REM      Arah: VPS -> LOKAL
REM
REM  Panduan: deploy\5-tarik-dari-vps.md
REM  Kalau perlu mundur: deploy\9-pulihkan-lokal.bat
REM ===================================================================
REM
REM  SEBELAS tabel dibuat ulang persis seperti di VPS, lalu diisi:
REM    branchops_branches    branchops_ref_values
REM    branchops_role_menus  branchops_settings
REM    branchops_batches     branchops_stg
REM    branchops_issues      branchops_it_break
REM    branchops_pencairan   branchops_tbo
REM    branchops_rekon
REM
REM  DUA tabel sengaja TIDAK disentuh:
REM    branchops_users   akun login. Kalau ikut ditimpa, sandi lokal
REM                      Anda berubah jadi sandi VPS dan Anda bisa
REM                      terkunci di luar dashboard sendiri.
REM    branchops_audit   jejak audit lokal = catatan pekerjaan Anda
REM                      di komputer ini.
REM
REM  Keempat dashboard lain (PMO, People Development, Service Quality,
REM  E-Library) tidak disentuh sama sekali.
REM
REM  VPS TIDAK DIUBAH. Di sana hanya pg_dump dan psql SELECT.
REM ===================================================================
REM
REM  PERBAIKAN 6 Agu 2026 - dua kesalahan pada versi sebelumnya:
REM
REM  1. Struktur kini ikut disalin. Versi lama hanya menyalin DATA dan
REM     mengandaikan kedua sisi berbentuk sama. Ternyata tidak:
REM     branchops_branches di VPS masih punya kolom 'region' yang sudah
REM     dibuang di lokal, jadi pemuatan gagal di baris pertama.
REM
REM  2. Pengosongan dan pemuatan kini SATU transaksi. Versi lama
REM     menjalankan TRUNCATE di panggilan psql terpisah, jadi ketika
REM     pemuatan gagal, TRUNCATE sudah terlanjur commit dan tabel
REM     tertinggal KOSONG. Sekarang keduanya berdiri atau jatuh bersama.
REM ===================================================================

if not "%~1"=="lanjut" (
    cmd /k ""%~f0" lanjut"
    exit /b
)

setlocal EnableDelayedExpansion
cd /d "%~dp0"

set VPS=root@159.65.139.45
set PGUSER=postgres
set PGDB=pmo
set HERE=%~dp0
set MASUK=%HERE%masuk
set CADANGAN=%HERE%cadangan

set PGBIN=
for %%V in (18 17 16 15) do (
    if exist "C:\Program Files\PostgreSQL\%%V\bin\psql.exe" (
        if "!PGBIN!"=="" set "PGBIN=C:\Program Files\PostgreSQL\%%V\bin"
    )
)
if "%PGBIN%"=="" (
    echo   GAGAL: PostgreSQL tidak ditemukan di C:\Program Files\PostgreSQL\
    pause & exit /b 1
)
set "PSQL=%PGBIN%\psql.exe"
set "PGDUMP=%PGBIN%\pg_dump.exe"

where ssh >nul 2>&1
if not %errorlevel%==0 (
    echo   GAGAL: perintah ssh tidak ada.
    echo   Settings ^> Apps ^> Optional features ^> OpenSSH Client
    pause & exit /b 1
)

echo.
echo ===================================================================
echo   IMPOR BRANCH OPS ^(STRUKTUR + ISI^)   VPS  -^>  LOKAL
echo ===================================================================
echo   Sumber : %VPS% , basis data %PGDB%   ^(hanya dibaca^)
echo   Tujuan : localhost , basis data %PGDB%
echo.

REM ---------------------------------------------------------------- 0
echo [0/6] Menguji sambungan...
set /p PGPASSWORD=  Kata sandi 'postgres' LOKAL ^(kosongkan kalau tanpa sandi^):
"%PSQL%" -U %PGUSER% -h localhost -d %PGDB% -c "SELECT 1;" >nul 2>&1
if not %errorlevel%==0 (
    echo   GAGAL menghubungi PostgreSQL lokal.
    echo   Sandi salah, layanan mati, atau basis data "%PGDB%" tidak ada.
    pause & exit /b 1
)
echo   PostgreSQL lokal OK

ssh -o ConnectTimeout=15 %VPS% "echo ok" >nul 2>&1
if not %errorlevel%==0 (
    echo   GAGAL: tidak bisa masuk ke %VPS%. Lokal TIDAK disentuh.
    pause & exit /b 1
)
echo   sambungan VPS OK

REM ---------------------------------------------------------------- 1
echo.
echo [1/6] Mengekspor DI VPS ^(hanya membaca^)...
echo.
scp -q "%HERE%6-vps-ekspor.sh" %VPS%:/tmp/6-vps-ekspor.sh
if not %errorlevel%==0 ( echo   GAGAL menyalin skrip ke VPS. & pause & exit /b 1 )
ssh %VPS% "sed -i 's/\r$//' /tmp/6-vps-ekspor.sh && bash /tmp/6-vps-ekspor.sh"
if not %errorlevel%==0 (
    echo.
    echo   BERHENTI. Ekspor di VPS tidak selesai - baca pesan di atas.
    echo   Basis data lokal TIDAK disentuh.
    pause & exit /b 1
)

REM ---------------------------------------------------------------- 2
echo.
echo [2/6] Menyalin hasil ke komputer ini...
if not exist "%MASUK%" mkdir "%MASUK%"
scp -q %VPS%:/tmp/vps-branchops.sql "%MASUK%\vps-branchops.sql"
if not %errorlevel%==0 ( echo   GAGAL menyalin dari VPS. Lokal TIDAK disentuh. & pause & exit /b 1 )
for %%A in ("%MASUK%\vps-branchops.sql") do (
  echo   vps-branchops.sql : %%~zA byte
  if %%~zA LSS 500 ( echo   GAGAL: berkas hampir kosong. & pause & exit /b 1 )
)

REM  Berkas harus memuat CREATE TABLE. Kalau tidak, yang terunduh adalah
REM  ekspor data-saja versi lama - memuatnya akan mengulang kegagalan
REM  yang sama persis.
findstr /b /c:"CREATE TABLE" "%MASUK%\vps-branchops.sql" >nul
if errorlevel 1 (
    echo.
    echo   GAGAL: berkas tidak memuat CREATE TABLE, jadi ini ekspor
    echo   data-saja, bukan struktur+isi. Lokal TIDAK disentuh.
    pause & exit /b 1
)

REM ---------------------------------------------------------------- 3
echo.
echo [3/6] Isi Branch Ops LOKAL sekarang:
"%PSQL%" -U %PGUSER% -h localhost -d %PGDB% -c "SELECT (SELECT count(*) FROM branchops_branches) AS cabang, (SELECT count(*) FROM branchops_batches) AS batches, (SELECT count(*) FROM branchops_it_break) AS it_break, (SELECT count(*) FROM branchops_pencairan) AS pencairan, (SELECT count(*) FROM branchops_tbo) AS tbo, (SELECT count(*) FROM branchops_rekon) AS rekon;"

echo.
echo   Sebelas tabel di atas akan DIBUAT ULANG mengikuti struktur VPS,
echo   lalu diisi data VPS. branchops_users dan branchops_audit aman.
echo.
echo   ^>^>^> Ketik  YA  lalu Enter. Apa pun selain itu = batal. ^<^<^<
echo.
set /p LANJUT=  Jawab:
if /i not "!LANJUT!"=="YA" (
  echo.
  echo   Dibatalkan. Tidak ada yang diubah.
  pause & exit /b 0
)

REM ---------------------------------------------------------------- 4
if not exist "%CADANGAN%" mkdir "%CADANGAN%"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmm"') do set STAMP=%%i

echo.
echo [4/6] Mencadangkan struktur + isi lokal...
REM  Cadangan ini juga --clean, jadi bisa dipakai memulihkan sendiri
REM  tanpa perlu mengosongkan tabel lebih dulu.
"%PGDUMP%" -U %PGUSER% -h localhost -d %PGDB% ^
  --clean --if-exists --no-owner --no-privileges --column-inserts ^
  -t branchops_branches   -t branchops_ref_values ^
  -t branchops_role_menus -t branchops_settings ^
  -t branchops_batches    -t branchops_stg ^
  -t branchops_issues     -t branchops_it_break ^
  -t branchops_pencairan  -t branchops_tbo ^
  -t branchops_rekon ^
  -f "%CADANGAN%\bo-lokal-sebelum-impor-%STAMP%.sql"
if errorlevel 1 goto :gagal
for %%A in ("%CADANGAN%\bo-lokal-sebelum-impor-%STAMP%.sql") do (
  if %%~zA LSS 1000 ( echo   GAGAL: cadangan terlalu kecil. Berhenti. & goto :gagal )
  echo   cadangan\bo-lokal-sebelum-impor-%STAMP%.sql  ^(%%~zA byte^)
)

REM ---------------------------------------------------------------- 5
echo.
echo [5/6] Membuat ulang tabel dan memuat data VPS...
echo        ^(satu transaksi - kalau gagal, tabel lama tetap utuh^)
REM  -1 membungkus SELURUH berkas dalam satu transaksi. DDL di
REM  PostgreSQL ikut transaksional, jadi DROP dan CREATE pun dibatalkan
REM  kalau ada satu perintah yang gagal. Inilah yang hilang di versi
REM  sebelumnya dan membuat tabel tertinggal kosong.
"%PSQL%" -U %PGUSER% -h localhost -d %PGDB% -1 -v ON_ERROR_STOP=1 ^
  -f "%MASUK%\vps-branchops.sql"
if errorlevel 1 goto :gagal_muat

REM ---------------------------------------------------------------- 6
echo.
echo [6/6] Menerapkan kembali migrasi lokal, lalu memeriksa...
REM  Struktur yang baru masuk adalah struktur VPS, yang lebih TUA
REM  daripada lokal. schema.sql menambahkan kembali apa yang khas lokal
REM  (region_class, branch_codes, CHECK ck_bo_users_satu_jatah, indeks)
REM  dengan ADD COLUMN IF NOT EXISTS, jadi aman dijalankan berulang dan
REM  tidak menyentuh data yang baru dimuat.
REM  Kolom 'region' lama ikut terbawa dari VPS. Dibiarkan: tidak ada
REM  kode yang membacanya. Buang dengan hapus-kolom-region-lama.sql
REM  kalau ingin bersih.
"%PSQL%" -U %PGUSER% -h localhost -d %PGDB% -v ON_ERROR_STOP=1 ^
  -f "%HERE%..\backend\branchops\schema.sql"
if errorlevel 1 (
    echo.
    echo   PERINGATAN: schema.sql gagal. Data sudah masuk, tapi struktur
    echo   mungkin belum sepenuhnya sesuai versi lokal. Jalankan backend
    echo   sekali - ensure_schema^(^) mencoba hal yang sama saat start.
)

"%PSQL%" -U %PGUSER% -h localhost -d %PGDB% -v ON_ERROR_STOP=1 ^
  -f "%HERE%6b-selesaikan-lokal.sql"
if errorlevel 1 goto :gagal_muat

echo.
echo ===================================================================
echo   SELESAI
echo ===================================================================
echo.
echo   BACA angka pemeriksaan di atas, bukan hanya kata "SELESAI":
echo     - pemeriksaan 3 ^(baris yatim^)     harus 0 semua
echo     - pemeriksaan 5 ^(jatah pengguna^)  idealnya kosong; kalau ada
echo       nama, perbaiki lewat tab Pengguna - akun itu tidak akan
echo       melihat baris apa pun sampai jatahnya benar
echo     - pemeriksaan 6 ^(sequence^)        "sisa" harus ^>= 0
echo.
echo   Rekonsiliasi ikut terbawa, jadi Dashboard 4 langsung terisi.
echo.
echo   Uji terakhir yang paling meyakinkan: unggah satu berkas Excel.
echo   Kalau berhasil, sequence sudah benar.
echo.
echo   Mundur: deploy\9-pulihkan-lokal.bat
echo.
echo   INGAT: deploy\masuk\vps-branchops.sql berisi NAMA NASABAH ASLI.
echo   Penyamaran "***" terjadi di API, bukan di basis data.
echo     del deploy\masuk\vps-branchops.sql
echo     ssh %VPS% "shred -u /tmp/vps-branchops.sql /tmp/6-vps-ekspor.sh"
echo.
pause
exit /b 0

:gagal_muat
echo.
echo ===================================================================
echo   GAGAL MEMUAT
echo ===================================================================
echo.
echo   Baca pesan kesalahan di atas.
echo.
echo   Seluruh pemuatan dibungkus SATU transaksi, jadi tabel lokal
echo   Anda tetap seperti sebelum skrip ini dijalankan. Tidak ada
echo   yang hilang, tidak perlu memulihkan apa pun.
echo.
echo   Cadangan tetap dibuat, untuk berjaga:
echo     cadangan\bo-lokal-sebelum-impor-%STAMP%.sql
echo.
pause
exit /b 1

:gagal
echo.
echo   GAGAL. Basis data lokal TIDAK diubah.
echo.
pause
exit /b 1
