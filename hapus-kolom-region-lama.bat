@echo off
REM ======================================================================
REM  Membuang kolom 'region' lama dari tabel branchops_branches
REM
REM  Urutannya sengaja begini: tidak ada yang dihapus sebelum cadangan
REM  terbukti jadi dan ukurannya masuk akal.
REM
REM    1. Cari PostgreSQL, minta sandi, uji koneksi
REM    2. Tampilkan apa yang akan hilang
REM    3. Cadangkan database
REM    4. Periksa cadangan benar-benar jadi
REM    5. Baru hapus kolomnya
REM
REM  Kolom 'region' berisi tebakan wilayah yang tidak pernah bekerja -
REM  seluruh cabang bernilai "Kantor Pusat". Penggantinya region_class.
REM  Aplikasi sudah berhenti memakainya, jadi ini boleh ditunda.
REM ======================================================================
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set LOKALDB=pmo
set STAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%-%TIME:~0,2%%TIME:~3,2%
set STAMP=%STAMP: =0%
set BACKUP=cadangan-sebelum-drop-region-%STAMP%.sql

echo.
echo ============================================================
echo   HAPUS KOLOM 'region' LAMA
echo ============================================================
echo   Database : localhost / %LOKALDB%
echo   Cadangan : %BACKUP%
echo.

REM ---------- cari psql / pg_dump ----------
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
echo   PostgreSQL: %PGBIN%

if not exist "hapus-kolom-region-lama.sql" (
    echo   GAGAL: berkas hapus-kolom-region-lama.sql tidak ada di folder ini.
    pause & exit /b 1
)

REM ---------- sandi ----------
echo.
set /p PGPASSWORD=  Kata sandi 'postgres':
"%PSQL%" -U postgres -h localhost -d %LOKALDB% -c "SELECT 1;" >nul 2>&1
if not %errorlevel%==0 (
    echo   GAGAL: sandi salah, database '%LOKALDB%' tidak ada, atau layanan mati.
    pause & exit /b 1
)

REM ---------------------------------------------------------------- 1
echo.
echo [1/4] Apakah kolomnya memang masih ada?
"%PSQL%" -U postgres -h localhost -d %LOKALDB% -tAc "SELECT count(*) FROM information_schema.columns WHERE table_name='branchops_branches' AND column_name='region'" | findstr "1" >nul
if not %errorlevel%==0 (
    echo   Kolom 'region' sudah tidak ada. Tidak ada yang perlu dikerjakan.
    pause & exit /b 0
)
echo   Masih ada. Isinya:
"%PSQL%" -U postgres -h localhost -d %LOKALDB% -c "SELECT region AS nilai_yang_akan_hilang, count(*) AS jumlah_cabang FROM branchops_branches GROUP BY region;"

echo.
echo   Ketik  HAPUS  untuk melanjutkan, atau apa saja untuk batal.
set /p KONFIRM=  ^>
if /I not "%KONFIRM%"=="HAPUS" ( echo   Dibatalkan. Tidak ada yang berubah. & pause & exit /b 0 )

REM ---------------------------------------------------------------- 2
echo.
echo [2/4] Mencadangkan database...
"%PGDUMP%" -U postgres -h localhost --clean --if-exists %LOKALDB% > "%BACKUP%" 2>nul
if not %errorlevel%==0 (
    echo   GAGAL mencadangkan. Kolom TIDAK dihapus.
    del "%BACKUP%" 2>nul
    pause & exit /b 1
)

REM ---------------------------------------------------------------- 3
echo.
echo [3/4] Memeriksa cadangan...
for %%A in ("%BACKUP%") do set SZ=%%~zA
echo   Ukuran: !SZ! byte
if !SZ! LSS 100000 (
    echo   GAGAL: cadangan mencurigakan kecil. Kolom TIDAK dihapus.
    pause & exit /b 1
)
findstr /C:"PostgreSQL database dump complete" "%BACKUP%" >nul
if not %errorlevel%==0 (
    echo   GAGAL: penanda akhir tidak ditemukan - cadangan terpotong.
    echo   Kolom TIDAK dihapus.
    pause & exit /b 1
)
echo   Cadangan lengkap.

REM ---------------------------------------------------------------- 4
echo.
echo [4/4] Menghapus kolom...
"%PSQL%" -U postgres -h localhost -d %LOKALDB% -v ON_ERROR_STOP=1 -f "hapus-kolom-region-lama.sql"
if not %errorlevel%==0 (
    echo.
    echo   GAGAL saat menghapus. Database kemungkinan besar tidak berubah
    echo   karena perintahnya dibungkus transaksi.
    echo   Untuk memulihkan dari cadangan:
    echo     "%PSQL%" -U postgres -h localhost -d %LOKALDB% -f "%BACKUP%"
    pause & exit /b 1
)

echo.
echo ============================================================
echo   SELESAI
echo.
echo   Cadangan : %BACKUP%
echo.
echo   Untuk kembali ke kondisi sebelum skrip ini:
echo     "%PSQL%" -U postgres -h localhost -d %LOKALDB% -f "%BACKUP%"
echo.
echo   Cadangan berisi data internal. Simpan aman, hapus bila
echo   sudah tidak diperlukan. Berkas *.sql tidak ikut ke git.
echo ============================================================
echo.
pause
