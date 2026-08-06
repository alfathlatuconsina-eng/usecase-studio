@echo off
REM ===================================================================
REM  9 - MEMULIHKAN data Branch Ops LOKAL dari cadangan
REM
REM  Dipakai setelah impor dari VPS gagal di tengah jalan: tabel sudah
REM  dikosongkan tapi data VPS gagal masuk, jadi tabel tinggal kosong.
REM
REM  Cadangan yang dipakai dibuat oleh 6-tarik-dari-vps.bat langkah 4,
REM  SEBELUM tabel dikosongkan. Isinya lengkap - sebelas tabel.
REM
REM  Hanya menyentuh tabel branchops_* (kecuali users dan audit).
REM  Keempat dashboard lain tidak disentuh.
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
if "%PGBIN%"=="" ( echo   GAGAL: PostgreSQL tidak ditemukan. & pause & exit /b 1 )
set "PSQL=%PGBIN%\psql.exe"

echo.
echo ===================================================================
echo   PULIHKAN DATA BRANCH OPS LOKAL DARI CADANGAN
echo ===================================================================
echo.

REM ---------- pilih cadangan terbaru ----------
set BERKAS=
for /f "delims=" %%F in ('dir /b /o-d "%CADANGAN%\bo-lokal-sebelum-impor-*.sql" 2^>nul') do (
    if "!BERKAS!"=="" set "BERKAS=%CADANGAN%\%%F"
)
if "%BERKAS%"=="" (
    echo   GAGAL: tidak ada berkas cadangan bo-lokal-sebelum-impor-*.sql
    echo   di folder %CADANGAN%
    pause & exit /b 1
)
for %%A in ("%BERKAS%") do echo   Cadangan : %%~nxA  ^(%%~zA byte^)
echo.

set /p PGPASSWORD=  Kata sandi 'postgres' LOKAL ^(kosongkan kalau tanpa sandi^):
"%PSQL%" -U %PGUSER% -h localhost -d %PGDB% -c "SELECT 1;" >nul 2>&1
if not %errorlevel%==0 (
    echo   GAGAL menghubungi PostgreSQL lokal. Tidak ada yang diubah.
    pause & exit /b 1
)

echo.
echo   Isi Branch Ops lokal SEKARANG:
"%PSQL%" -U %PGUSER% -h localhost -d %PGDB% -c "SELECT (SELECT count(*) FROM branchops_branches) AS cabang, (SELECT count(*) FROM branchops_batches) AS batches, (SELECT count(*) FROM branchops_it_break) AS it_break, (SELECT count(*) FROM branchops_pencairan) AS pencairan, (SELECT count(*) FROM branchops_tbo) AS tbo, (SELECT count(*) FROM branchops_rekon) AS rekon;"

echo.
echo   Semuanya akan diganti dengan isi cadangan di atas.
echo.
echo   ^>^>^> Ketik  PULIHKAN  lalu Enter. Apa pun selain itu = batal. ^<^<^<
echo.
set /p JWB=  Jawab:
if /i not "!JWB!"=="PULIHKAN" ( echo   Dibatalkan. & pause & exit /b 0 )

REM  Kosongkan + muat dalam SATU transaksi. Kalau pemuatan gagal, TRUNCATE
REM  ikut dibatalkan dan tabel tetap seperti sebelumnya. Inilah yang
REM  TIDAK dilakukan skrip impor - dan itulah sebabnya tabel bisa
REM  tertinggal kosong.
echo.
echo   Memulihkan ^(satu transaksi - gagal = batal semua^)...
(
  echo BEGIN;
  echo TRUNCATE TABLE branchops_rekon, branchops_it_break, branchops_pencairan,
  echo   branchops_tbo, branchops_issues, branchops_stg, branchops_batches,
  echo   branchops_branches, branchops_ref_values, branchops_role_menus,
  echo   branchops_settings CASCADE;
  echo \i '%BERKAS:\=/%'
  echo COMMIT;
) > "%TEMP%\bo-pulih.sql"

"%PSQL%" -U %PGUSER% -h localhost -d %PGDB% -v ON_ERROR_STOP=1 -f "%TEMP%\bo-pulih.sql"
if errorlevel 1 (
    del "%TEMP%\bo-pulih.sql" 2>nul
    echo.
    echo   GAGAL memulihkan. Karena dibungkus satu transaksi, tabel
    echo   TIDAK berubah - keadaannya sama seperti sebelum skrip ini.
    echo   Baca pesan kesalahan di atas.
    pause & exit /b 1
)
del "%TEMP%\bo-pulih.sql" 2>nul

echo.
echo   Menyetel ulang sequence...
"%PSQL%" -U %PGUSER% -h localhost -d %PGDB% -v ON_ERROR_STOP=1 -f "%HERE%6b-selesaikan-lokal.sql"

echo.
echo ===================================================================
echo   SELESAI - periksa angka "Jumlah baris per tabel" di atas.
echo   Yang diharapkan kembali:
echo     branches 44 , batches 21 , it_break 1327 ,
echo     pencairan 754 , tbo 129 , rekon 348 , stg 2229
echo ===================================================================
echo.
pause
exit /b 0
