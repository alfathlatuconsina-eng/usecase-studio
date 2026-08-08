@echo off
REM ===================================================================
REM  1 - LIHAT SUNTINGAN YANG ADA DI VPS  (HANYA MEMBACA)
REM
REM  Dijalankan ketika 2-push-ke-vps.bat berhenti di langkah 2 dengan
REM  pesan "ada berkas TERLACAK yang berubah di /opt/pmo".
REM
REM  Artinya seseorang pernah menyunting berkas LANGSUNG di produksi,
REM  dan suntingan itu tidak pernah masuk git. `git pull` akan menimpanya.
REM
REM  Berkas ini TIDAK mengubah apa pun. Ia hanya menyalin turun:
REM    - diff lengkap tiap berkas yang berubah
REM    - salinan utuh berkas versi VPS
REM  supaya bisa dibaca dan dibandingkan sebelum memutuskan.
REM
REM  JANGAN langsung `git stash` di VPS sebelum melihat isinya. app.py
REM  memuat KELIMA dashboard; membuang suntingan di sana bisa mematikan
REM  PMO, People, Quality atau E-Library sekaligus.
REM ===================================================================

if not "%~1"=="lanjut" (
    cmd /k ""%~f0" lanjut"
    exit /b
)

setlocal EnableDelayedExpansion
cd /d "%~dp0"
set VPS=root@159.65.139.45
set APP=/opt/pmo
set KELUAR=%~dp0masuk\suntingan-vps

where ssh >nul 2>&1 || ( echo   GAGAL: ssh tidak ada. & pause & exit /b 1 )

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmm"') do set STAMP=%%i
set TUJUAN=%KELUAR%-%STAMP%
if not exist "%TUJUAN%" mkdir "%TUJUAN%"

echo.
echo ===================================================================
echo   SUNTINGAN LANGSUNG DI VPS  %APP%
echo ===================================================================
echo.

echo [1/4] Daftar berkas yang berubah
ssh %VPS% "cd %APP% && git status --porcelain --untracked-files=no"
if not %errorlevel%==0 ( echo   GAGAL menghubungi VPS. & pause & exit /b 1 )

echo.
echo [2/4] Ringkasan besar perubahan
ssh %VPS% "cd %APP% && git diff --stat"

echo.
echo [3/4] Menyimpan diff lengkap ke komputer ini
ssh %VPS% "cd %APP% && git diff" > "%TUJUAN%\suntingan-vps.diff" 2>nul
for %%A in ("%TUJUAN%\suntingan-vps.diff") do echo        suntingan-vps.diff  (%%~zA byte)

echo.
echo [4/4] Menyalin berkas versi VPS apa adanya
REM  Diff saja kadang tidak cukup: kalau berkas di VPS jauh berbeda,
REM  lebih mudah membandingkan berkas utuh berdampingan.
for %%F in (backend/app.py backend/init_db.py backend/requirements.txt
            frontend/landing.html frontend/people.html frontend/quality.html) do (
  for %%N in (%%~nxF) do (
    scp -q %VPS%:%APP%/%%F "%TUJUAN%\%%N.vps" 2>nul && echo        %%N.vps
  )
)

REM  Commit yang sedang dipakai VPS - untuk tahu diff-nya terhadap apa.
ssh %VPS% "cd %APP% && git rev-parse --short HEAD && git log -1 --format=%%s" > "%TUJUAN%\commit-vps.txt" 2>nul
type "%TUJUAN%\commit-vps.txt"

echo.
echo ===================================================================
echo   TERSIMPAN DI:
echo   %TUJUAN%
echo ===================================================================
echo.
echo   LANGKAH BERIKUTNYA - baca dulu, jangan langsung stash:
echo.
echo   1. Buka suntingan-vps.diff. Untuk tiap perubahan, tanya:
echo      apakah ini perbaikan yang HANYA ada di produksi?
echo.
echo   2. Kalau perubahan itu MASIH DIPERLUKAN:
echo      terapkan juga di komputer lokal, commit, push. Baru dorong.
echo      Kalau tidak, perbaikan itu hilang saat git pull.
echo.
echo   3. Kalau perubahan itu SUDAH TIDAK RELEVAN (mis. sudah ada versi
echo      lebih baru di lokal), simpan saja sebagai jaring pengaman:
echo         ssh %VPS% "cd %APP% && git stash push -m sebelum-push-%STAMP%"
echo      lalu jalankan 2-push-ke-vps.bat lagi.
echo      Mengambilnya kembali: git stash list / git stash pop
echo.
echo   PERHATIAN KHUSUS:
echo     backend/app.py        memuat KELIMA dashboard, bukan Branch Ops saja
echo     backend/init_db.py    salinan VPS diketahui rusak (impor QualitySurvey
echo                           yang tidak ada) - JANGAN dibawa ke lokal
echo     requirements.txt      kalau ada paket tambahan di VPS, pip install
echo                           akan hilang setelah pull
echo.
pause
exit /b 0
