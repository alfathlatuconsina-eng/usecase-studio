@echo off
REM ===================================================================
REM  Langkah 1 (DI KOMPUTER LOKAL) - ekspor tabel Branch Ops
REM ===================================================================
REM  Menghasilkan tiga berkas TERPISAH, supaya bisa dipilih mana yang
REM  dikirim ke VPS dan mana yang tidak:
REM
REM    bo-acuan.sql       master cabang, wilayah, hak menu, pengaturan
REM    bo-transaksi.sql   data harian hasil unggah Excel
REM    bo-pengguna.sql    akun branchops_users (email + sandi + jatah)
REM
REM  branchops_audit SENGAJA TIDAK diekspor. Jejak audit di VPS adalah
REM  catatan produksi; menimpanya dengan jejak dari komputer lokal akan
REM  merusak riwayat yang justru paling perlu dipercaya.
REM ===================================================================

setlocal
set PGBIN=C:\Program Files\PostgreSQL\18\bin
set PGUSER=postgres
set PGDB=pmo
set KELUAR=%~dp0keluaran

if not exist "%PGBIN%\pg_dump.exe" (
  echo.
  echo GAGAL: pg_dump tidak ditemukan di "%PGBIN%"
  echo Perbaiki baris "set PGBIN=" di berkas ini lalu jalankan lagi.
  echo.
  pause
  exit /b 1
)

if not exist "%KELUAR%" mkdir "%KELUAR%"

echo.
echo === 1/3  Tabel acuan (master cabang, wilayah, hak menu, pengaturan)
"%PGBIN%\pg_dump.exe" -U %PGUSER% -d %PGDB% --data-only --column-inserts ^
  -t branchops_branches -t branchops_ref_values ^
  -t branchops_role_menus -t branchops_settings ^
  -f "%KELUAR%\bo-acuan.sql"
if errorlevel 1 goto :gagal

echo === 2/3  Tabel transaksi (hasil unggah Excel harian)
"%PGBIN%\pg_dump.exe" -U %PGUSER% -d %PGDB% --data-only --column-inserts ^
  -t branchops_batches -t branchops_stg -t branchops_issues ^
  -t branchops_it_break -t branchops_pencairan ^
  -t branchops_tbo -t branchops_rekon ^
  -f "%KELUAR%\bo-transaksi.sql"
if errorlevel 1 goto :gagal

echo === 3/3  Akun pengguna Branch Ops
"%PGBIN%\pg_dump.exe" -U %PGUSER% -d %PGDB% --data-only --column-inserts ^
  -t branchops_users ^
  -f "%KELUAR%\bo-pengguna.sql"
if errorlevel 1 goto :gagal

echo.
echo SELESAI. Berkas ada di:
echo   %KELUAR%
echo.
echo PERIKSA DULU isi bo-pengguna.sql sebelum dikirim ke VPS.
echo Berkas itu berisi email dan hash sandi akun Anda.
echo.
pause
exit /b 0

:gagal
echo.
echo GAGAL. Periksa pesan di atas.
echo Penyebab tersering: sandi PostgreSQL, atau nama basis data bukan "%PGDB%".
echo.
pause
exit /b 1
