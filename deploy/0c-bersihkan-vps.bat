@echo off
REM ===================================================================
REM  0c - BERSIHKAN DISK VPS
REM
REM  DUA LANGKAH, dan langkah pertama tidak menghapus apa pun:
REM
REM    1. LAPORAN  - menampilkan setiap berkas yang akan dihapus
REM                  beserta ukurannya, dan totalnya. Selalu jalan
REM                  lebih dulu, tanpa bisa dilewati.
REM    2. NYATA    - baru menghapus, dan hanya kalau Anda mengetik
REM                  BERSIHKAN. Apa pun selain itu = batal.
REM
REM  YANG TIDAK PERNAH DISENTUH:
REM    - basis data PostgreSQL. Tidak ada satu pun perintah SQL.
REM    - /opt/pmo beserta .git-nya
REM    - /opt/pmo/uploads/** - berkas unggahan E-Library
REM    - dua cadangan SQL terbaru dari tiap keluarga di /root
REM
REM  Layanan pmo TIDAK di-restart. Kalau ada berkas terhapus yang
REM  masih dipegang proses, itu hanya dilaporkan - membebaskannya
REM  berarti me-restart layanan, dan itu keputusan Anda.
REM
REM  Periksa dulu dengan 0b-cek-disk-vps.bat kalau ingin gambaran
REM  lengkapnya sebelum membersihkan.
REM ===================================================================

if not "%~1"=="lanjut" (
    cmd /k ""%~f0" lanjut"
    exit /b
)

setlocal EnableDelayedExpansion
cd /d "%~dp0"
set VPS=root@159.65.139.45

where ssh >nul 2>&1
if not %errorlevel%==0 (
  echo.
  echo   GAGAL: perintah ssh tidak ada di komputer ini.
  echo   Settings ^> Apps ^> Optional features ^> OpenSSH Client
  echo.
  pause & exit /b 1
)

echo.
echo ===================================================================
echo   BERSIHKAN DISK VPS %VPS%
echo ===================================================================
echo.

echo [1/3] Mengirim skrip...
scp -q "%~dp00c-vps-bersih.sh" %VPS%:/tmp/0c-vps-bersih.sh
if not %errorlevel%==0 (
  echo   GAGAL menyalin ke VPS. Periksa: ssh %VPS% "echo ok"
  pause & exit /b 1
)

echo [2/3] LAPORAN - tidak ada yang dihapus pada langkah ini
echo.
ssh %VPS% "sed -i 's/\r$//' /tmp/0c-vps-bersih.sh && bash /tmp/0c-vps-bersih.sh"
if not %errorlevel%==0 (
  echo.
  echo   GAGAL menjalankan laporan. Tidak ada yang dihapus.
  pause & exit /b 1
)

echo.
echo ===================================================================
echo   BACA DAFTAR DI ATAS SEBELUM MENJAWAB
echo ===================================================================
echo.
echo   Setiap berkas yang akan dihapus sudah disebut namanya. Kalau ada
echo   satu saja yang Anda ragukan, batalkan dan periksa dulu.
echo.
echo   ^>^>^> Ketik  BERSIHKAN  lalu Enter. Apa pun selain itu = batal. ^<^<^<
echo.
set /p JAWAB=  Jawab:
if /i not "!JAWAB!"=="BERSIHKAN" (
  echo.
  echo   Dibatalkan. Tidak ada yang dihapus di VPS.
  echo.
  pause & exit /b 0
)

echo.
echo [3/3] Menghapus...
echo.
ssh %VPS% "bash /tmp/0c-vps-bersih.sh BERSIHKAN"
if not %errorlevel%==0 (
  echo.
  echo   Skrip pembersih berhenti dengan galat. Baca pesan di atas.
  echo   Basis data dan uploads tidak pernah disentuh apa pun yang
  echo   terjadi, jadi tidak ada yang perlu dipulihkan.
  pause & exit /b 1
)

echo.
echo ===================================================================
echo   SELESAI
echo ===================================================================
echo.
echo   Baca baris "benar-benar dibebaskan" di atas, bukan sekadar kata
echo   SELESAI. Kalau angkanya jauh lebih kecil dari perkiraan, biasanya
echo   sebabnya ada di bagian 6: berkas terhapus yang masih dipegang
echo   proses. Ruang itu baru kembali setelah layanannya di-restart.
echo.
echo   Sejak 16 Agu 2026, 2-vps-muat.sh memangkas sendiri cadangan lama
echo   di akhir tiap push, jadi /root tidak akan menumpuk lagi seperti
echo   dulu. Pembersihan manual ini seharusnya makin jarang diperlukan.
echo.
pause
exit /b 0
