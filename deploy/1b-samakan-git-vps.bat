@echo off
REM ===================================================================
REM  1b - MENYAMAKAN RIWAYAT GIT VPS DENGAN origin/main
REM
REM  Dijalankan sekali, sebelum 2-push-ke-vps.bat, ketika VPS berada di
REM  commit yang TIDAK ADA di origin/main.
REM
REM  Keadaan yang ditangani (7 Agu 2026):
REM    /opt/pmo ada di commit 2886401
REM      "Make PD import dedup date-aware to stop merging recycled-code events"
REM    Commit itu dibuat LANGSUNG di VPS dan tidak pernah di-push, jadi
REM    tidak ada di origin/main maupun di komputer lokal.
REM
REM  Akibatnya `git pull --ff-only` GAGAL: HEAD di VPS bukan leluhur
REM  origin/main, jadi tidak ada jalur maju yang bisa diikuti.
REM
REM  Yang dikerjakan berkas ini, berurutan:
REM    1. tampilkan isi commit 2886401 dan simpan sebagai patch ke lokal
REM    2. simpan suntingan pohon kerja ke git stash (bisa diambil lagi)
REM    3. reset /opt/pmo ke origin/main
REM    4. periksa hasilnya
REM
REM  TIDAK menyentuh basis data sama sekali.
REM ===================================================================

if not "%~1"=="lanjut" (
    cmd /k ""%~f0" lanjut"
    exit /b
)

setlocal EnableDelayedExpansion
cd /d "%~dp0"
set VPS=root@159.65.139.45
set APP=/opt/pmo
set TUJUAN=%~dp0masuk

where ssh >nul 2>&1 || ( echo   GAGAL: ssh tidak ada. & pause & exit /b 1 )
if not exist "%TUJUAN%" mkdir "%TUJUAN%"

for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmm"') do set STAMP=%%i

echo.
echo ===================================================================
echo   MENYAMAKAN RIWAYAT GIT DI VPS
echo ===================================================================
echo.

echo [1/5] Keadaan sekarang di %APP%
ssh %VPS% "cd %APP% && echo 'HEAD  :' $(git rev-parse --short HEAD) && echo 'pesan :' $(git log -1 --format=%%s) && git fetch origin -q && echo 'origin:' $(git rev-parse --short origin/main)"
if not %errorlevel%==0 ( echo   GAGAL menghubungi VPS. & pause & exit /b 1 )

echo.
echo [2/5] Isi commit yang HANYA ada di VPS
echo        ^(berkas apa saja yang disentuh, dan berapa barisnya^)
ssh %VPS% "cd %APP% && git log --oneline origin/main..HEAD && echo '--- berkas ---' && git diff --stat origin/main...HEAD"

echo.
echo        Menyimpan patch-nya ke komputer ini, supaya tidak hilang:
ssh %VPS% "cd %APP% && git format-patch origin/main..HEAD --stdout" > "%TUJUAN%\commit-hanya-di-vps-%STAMP%.patch" 2>nul
for %%A in ("%TUJUAN%\commit-hanya-di-vps-%STAMP%.patch") do (
  echo        masuk\commit-hanya-di-vps-%STAMP%.patch  ^(%%~zA byte^)
  if %%~zA LSS 40 echo        ^(kosong - berarti tidak ada commit khas VPS^)
)

echo.
echo ===================================================================
echo   BACA DUA HAL DI ATAS SEBELUM MELANJUTKAN
echo ===================================================================
echo.
echo   Commit yang hanya ada di VPS akan DIBUANG dari cabangnya.
echo   Patch-nya sudah tersimpan di komputer ini, jadi masih bisa
echo   diterapkan lagi nanti dengan:  git am ^< berkas.patch
echo.
echo   Kalau perubahannya MASIH DIPERLUKAN dan belum ada di lokal:
echo   BERHENTI sekarang, terapkan patch itu di komputer lokal,
echo   commit, push, baru ulangi.
echo.
echo   Diperiksa 7 Agu 2026: kelima berkas selain init_db.py sudah
echo   BYTE-IDENTIK dengan versi lokal, dan init_db.py versi VPS adalah
echo   salinan rusak ^(mengimpor QualitySurvey yang tidak ada^). Jadi
echo   membuangnya memang yang diinginkan.
echo.
echo   ^>^>^> Ketik  SAMAKAN  lalu Enter untuk melanjutkan. ^<^<^<
echo.
set /p LANJUT=  Jawab:
if /i not "!LANJUT!"=="SAMAKAN" ( echo. & echo   Dibatalkan. VPS tidak diubah. & pause & exit /b 0 )

echo.
echo [3/5] Menyimpan suntingan pohon kerja ke stash
REM  Stash, bukan checkout: isinya masih bisa diambil kembali dengan
REM  `git stash pop`. Kalau ternyata ada yang terlewat, tidak hilang.
ssh %VPS% "cd %APP% && git stash push -u -m 'sebelum-samakan-%STAMP%' || echo '(tidak ada yang perlu disimpan)'"

echo.
echo [4/5] Mengarahkan cabang ke origin/main
ssh %VPS% "cd %APP% && git reset --hard origin/main"
if not %errorlevel%==0 ( echo   GAGAL melakukan reset. & pause & exit /b 1 )

echo.
echo [5/5] Hasil
ssh %VPS% "cd %APP% && echo 'HEAD  :' $(git rev-parse --short HEAD) && echo 'pesan :' $(git log -1 --format=%%s) && echo '--- status ---' && git status --porcelain --untracked-files=no && echo '(kosong di atas = bersih)' && echo '--- stash tersimpan ---' && git stash list"

echo.
echo ===================================================================
echo   SELESAI
echo ===================================================================
echo.
echo   Kalau "status" di atas KOSONG, riwayat VPS sudah sama dengan
echo   origin/main dan 2-push-ke-vps.bat bisa dijalankan sekarang.
echo.
echo   Basis data belum disentuh sama sekali oleh berkas ini.
echo.
echo   Kalau perlu mengembalikan suntingan yang disimpan:
echo     ssh %VPS% "cd %APP% && git stash list"
echo     ssh %VPS% "cd %APP% && git stash pop"
echo.
pause
exit /b 0
