@echo off
REM ===================================================================
REM  0b - PERIKSA PEMAKAIAN DISK VPS  (HANYA MEMBACA)
REM
REM  Klik dua kali. Tidak mengubah apa pun di VPS: tidak menghapus
REM  berkas, tidak me-restart layanan, tidak menyentuh basis data.
REM
REM  Menjawab "disk 8,7 GB itu isinya apa": direktori terbesar, berkas
REM  besar, cadangan SQL yang menumpuk di /root, cache, log systemd,
REM  berkas terhapus yang masih dipegang proses, ukuran basis data dan
REM  WAL, kernel lama, dan berapa besar uploads/ yang JANGAN dihapus.
REM
REM  CATATAN: 8,7 GB itu UKURAN disknya, bukan yang terpakai. Lihat
REM  "failure 1" di CLAUDE.md - disk sekecil itu memang sudah pernah
REM  penuh 100%. Yang dicari skrip ini adalah apa yang TUMBUH.
REM
REM  Pasangannya: 0c-bersihkan-vps.bat
REM ===================================================================

if not "%~1"=="lanjut" (
    cmd /k ""%~f0" lanjut"
    exit /b
)

setlocal
cd /d "%~dp0"
set VPS=root@159.65.139.45

where ssh >nul 2>&1
if not %errorlevel%==0 (
  echo.
  echo   GAGAL: perintah ssh tidak ada di komputer ini.
  echo   Pasang lewat: Settings ^> Apps ^> Optional features ^> OpenSSH Client
  echo.
  pause & exit /b 1
)

echo.
echo ===================================================================
echo   MEMERIKSA DISK VPS %VPS%   ^(hanya membaca^)
echo ===================================================================
echo.

echo [1/2] Mengirim skrip pemeriksa...
scp -q "%~dp00b-vps-disk.sh" %VPS%:/tmp/0b-vps-disk.sh
if not %errorlevel%==0 (
  echo.
  echo   GAGAL menyalin ke VPS. Periksa koneksi dan kunci SSH:
  echo     ssh %VPS% "echo ok"
  echo.
  pause & exit /b 1
)

echo [2/2] Menjalankan di VPS...
echo.
REM  sed membuang carriage return Windows; tanpa itu bash menolak
REM  berkasnya dengan pesan "$'\r': command not found".
REM
REM  JANGAN menambahkan pipe ke PowerShell di sini. Lihat kegagalan 2
REM  di CLAUDE.md: Tee-Object -Encoding tidak ada di PowerShell 5.1,
REM  pipenya mati, ssh ikut terbunuh di tengah jalan, dan skripnya
REM  menyalahkan VPS padahal VPS baik-baik saja.
ssh %VPS% "sed -i 's/\r$//' /tmp/0b-vps-disk.sh && bash /tmp/0b-vps-disk.sh"
if not %errorlevel%==0 (
  echo.
  echo   GAGAL menjalankan pemeriksa di VPS. Baca pesan di atas.
  echo.
  pause & exit /b 1
)

echo.
echo ===================================================================
echo   CARA MEMBACA HASIL DI ATAS
echo ===================================================================
echo.
echo   Bagian 4 ^(cadangan SQL di /root^) adalah yang paling sering jadi
echo   sebab. Setiap push menambah sepasang berkas ~30 MB dan sampai
echo   16 Agu 2026 tidak ada yang pernah menghapusnya.
echo.
echo   Bagian 5 ^(cache^) aman dihapus seluruhnya - isinya bukan data.
echo.
echo   Bagian 7 ^(berkas terhapus yang masih dipegang proses^) tidak bisa
echo   dibebaskan dengan menghapus apa pun. Ruangnya baru kembali kalau
echo   prosesnya di-restart.
echo.
echo   Bagian 10 JANGAN dihapus. Itu berkas unggahan E-Library.
echo.
echo   Kalau sisa ruang di bawah ~1 GB, bersihkan SEBELUM push
echo   berikutnya, bukan sesudah push gagal:
echo     0c-bersihkan-vps.bat
echo.
pause
exit /b 0
