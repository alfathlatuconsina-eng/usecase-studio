@echo off
REM ===================================================================
REM  8 - CADANGKAN SELURUH MODUL BRANCH OPS SEBELUM RESTART PERTAMA
REM
REM  Dipakai SEKALI, sebelum backend dijalankan pertama kali setelah
REM  perubahan 15 Agustus 2026. Restart itu menjalankan ensure_schema(),
REM  dan schema.sql kini memuat TIGA migrasi yang belum pernah menyentuh
REM  basis data mana pun:
REM
REM    1. harus_ganti_sandi pada branchops_users, plus pembebasan
REM       sekali-jalan untuk pengguna yang sudah ada        (aturan 22)
REM    2. lima kolom baru pada branchops_pencairan          (aturan 23)
REM    3. penyeragaman ejaan: 'Dipercepat dari Jatuh Tempo' ->
REM       'Dipercepat (Break)' dan 'Pemindahbukuan' ->
REM       'Pemindah-bukuan', ~308 baris                     (aturan 24)
REM
REM  Ketiganya berjalan otomatis dan tidak bisa dibatalkan setengah
REM  jalan. Berkas ini adalah titik mundurnya.
REM
REM  BEDA DARI CADANGAN LAIN DI FOLDER INI:
REM  bo-lokal-sebelum-impor-*.sql hanya memuat SEBELAS tabel data.
REM  Berkas ini memuat SEMUA tabel branchops_*, TERMASUK
REM  branchops_users dan branchops_audit - karena migrasi 1 mengubah
REM  branchops_users, dan ketiganya menulis kunci baru ke
REM  branchops_settings. Cadangan yang tidak memuat keduanya tidak bisa
REM  mengembalikan keadaan sebelum restart.
REM
REM  VPS TIDAK DISENTUH. Skrip ini hanya membaca basis data LOKAL.
REM ===================================================================

if not "%~1"=="lanjut" (
    cmd /k ""%~f0" lanjut"
    exit /b
)

setlocal EnableDelayedExpansion
cd /d "%~dp0"

set PGUSER=postgres
set PGDB=pmo
set HERE=%~dp0
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

echo.
echo ===================================================================
echo   CADANGAN BRANCH OPS - sebelum restart pertama
echo ===================================================================
echo   Sumber : localhost , basis data %PGDB%   ^(hanya dibaca^)
echo   Tujuan : deploy\cadangan\
echo.

REM ---------------------------------------------------------------- 1
echo [1/4] Menguji sambungan ke PostgreSQL lokal...
set /p PGPASSWORD=  Kata sandi 'postgres' LOKAL ^(kosongkan kalau tanpa sandi^):
"%PSQL%" -U %PGUSER% -h localhost -d %PGDB% -c "SELECT 1;" >nul 2>&1
if not %errorlevel%==0 (
    echo   GAGAL menghubungi PostgreSQL lokal.
    echo   Sandi salah, layanan mati, atau basis data "%PGDB%" tidak ada.
    pause & exit /b 1
)
echo   PostgreSQL lokal OK

REM ---------------------------------------------------------------- 2
echo.
echo [2/4] Isi Branch Ops SEKARANG ^(catat angkanya^):
"%PSQL%" -U %PGUSER% -h localhost -d %PGDB% -c "SELECT (SELECT count(*) FROM branchops_branches) AS cabang, (SELECT count(*) FROM branchops_batches) AS batches, (SELECT count(*) FROM branchops_pencairan) AS pencairan, (SELECT count(*) FROM branchops_tbo) AS tbo, (SELECT count(*) FROM branchops_users) AS pengguna, (SELECT count(*) FROM branchops_audit) AS audit;"

REM  Angka yang paling berarti untuk migrasi ejaan: berapa baris yang
REM  AKAN diubah. Sesudah restart, keduanya harus 0.
echo.
echo   Baris yang akan diubah migrasi ejaan ^(sesudah restart harus 0^):
"%PSQL%" -U %PGUSER% -h localhost -d %PGDB% -c "SELECT count(*) FILTER (WHERE jenis_pencairan='Dipercepat dari Jatuh Tempo') AS ejaan_pencairan_lama, count(*) FILTER (WHERE jenis_penarikan='Pemindahbukuan') AS ejaan_penarikan_lama FROM branchops_pencairan;"

REM ---------------------------------------------------------------- 3
if not exist "%CADANGAN%" mkdir "%CADANGAN%"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmm"') do set STAMP=%%i
set "BERKAS=%CADANGAN%\bo-sebelum-restart-%STAMP%.sql"

echo.
echo [3/4] Mencadangkan struktur + isi seluruh tabel branchops_*...
REM  --clean --if-exists : berkas ini bisa dimuat langsung di atas basis
REM  data yang sudah ada, tanpa perlu mengosongkan tabel lebih dulu.
REM  --column-inserts    : lebih lambat, tetapi setiap baris berdiri
REM                        sendiri, jadi satu baris rusak tidak
REM                        menggagalkan seluruh berkas.
REM  pg_dump MELEWATI tabel yang tidak ada tanpa berkata apa-apa, jadi
REM  ukuran berkas diperiksa di bawah - bukan sekadar errorlevel.
"%PGDUMP%" -U %PGUSER% -h localhost -d %PGDB% ^
  --clean --if-exists --no-owner --no-privileges --column-inserts ^
  -t branchops_branches   -t branchops_ref_values ^
  -t branchops_role_menus -t branchops_settings ^
  -t branchops_batches    -t branchops_stg ^
  -t branchops_issues     -t branchops_it_break ^
  -t branchops_pencairan  -t branchops_tbo ^
  -t branchops_rekon      -t branchops_users ^
  -t branchops_audit      -t branchops_user_menus ^
  -f "%BERKAS%"
if errorlevel 1 (
    echo   GAGAL membuat cadangan. Jangan restart backend dulu.
    pause & exit /b 1
)

for %%A in ("%BERKAS%") do (
  if %%~zA LSS 10000 (
      echo   GAGAL: cadangan hanya %%~zA byte - terlalu kecil untuk benar.
      echo   Jangan restart backend dulu.
      pause & exit /b 1
  )
  echo   %BERKAS%
  echo   ukuran: %%~zA byte
)

REM ---------------------------------------------------------------- 4
echo.
echo [4/4] Memastikan berkas benar-benar berisi tabel...
findstr /b /c:"CREATE TABLE" "%BERKAS%" >nul
if errorlevel 1 (
    echo   GAGAL: berkas tidak memuat CREATE TABLE. Jangan restart backend.
    pause & exit /b 1
)
echo   OK - berkas memuat struktur dan isi.

echo.
echo ===================================================================
echo   SELESAI - aman untuk menjalankan backend
echo ===================================================================
echo.
echo   Sekarang jalankan:  cd backend  ^&^&  py -3 app.py
echo.
echo   PERHATIKAN layar startup. schema.sql dijalankan di situ, dan
echo   tiga migrasi berjalan sekali saja. Kalau ada pesan galat di
echo   antaranya, BERHENTI dan pulihkan - jangan menyimpan apa pun
echo   lewat aplikasi lebih dulu.
echo.
echo   Sesudah backend hidup, dua pemeriksaan yang paling berarti:
echo     1. Masuk dengan akun LAMA. Harus langsung masuk, tanpa
echo        diminta mengganti sandi. Itu bukti pembebasan sekali-jalan
echo        berjalan ^(aturan 22^).
echo     2. Jalankan lagi skrip ini. Dua angka "ejaan_..._lama" di
echo        langkah 2 harus sudah 0 ^(aturan 24^).
echo.
echo   CARA MUNDUR - satu perintah, satu transaksi:
echo.
echo     "%PSQL%" -U %PGUSER% -h localhost -d %PGDB% -1 -v ON_ERROR_STOP=1 -f "%BERKAS%"
echo.
echo   Berkas ini --clean, jadi tidak perlu mengosongkan tabel dulu.
echo   Gagal = dibatalkan seluruhnya, basis data tidak berubah.
echo   JANGAN pakai 9-pulihkan-lokal.bat untuk berkas ini: skrip itu
echo   hanya mencari bo-lokal-sebelum-impor-*.sql dan hanya
echo   mengosongkan sebelas tabel - tanpa pengguna dan audit.
echo.
echo   INGAT: berkas ini berisi NAMA NASABAH ASLI. Penyamaran terjadi
echo   di API, bukan di basis data. Hapus setelah tidak diperlukan.
echo.
pause
endlocal
