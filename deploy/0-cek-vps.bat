@echo off
REM ===================================================================
REM  0 - PERIKSA ISI VPS  (HANYA MEMBACA)
REM
REM  Klik dua kali berkas ini. Tidak mengubah apa pun, di VPS maupun di
REM  komputer ini - hanya menampilkan:
REM
REM    - jumlah baris tiap tabel branchops di VPS
REM    - batch terakhir per jenis dan kapan diunggah
REM    - apakah kolom Agustus 2026 sudah ada di sana
REM    - apakah kolom lama 'region' masih ada
REM    - commit git yang sedang dipakai /opt/pmo
REM
REM  Gunanya: sebelum menjalankan 2-push-ke-vps.bat, pastikan VPS TIDAK
REM  memuat data yang belum pernah ditarik ke komputer ini. Mendorong
REM  data lokal akan menggantikannya.
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
echo   MEMERIKSA ISI VPS %VPS%   (hanya membaca)
echo ===================================================================
echo.

echo [1/2] Mengirim skrip pemeriksa...
scp -q "%~dp02-cek-dua-sisi.sh" %VPS%:/tmp/2-cek-dua-sisi.sh
if not %errorlevel%==0 (
  echo.
  echo   GAGAL menyalin ke VPS. Periksa koneksi dan kunci SSH:
  echo     ssh %VPS% "echo ok"
  echo.
  pause & exit /b 1
)

echo [2/2] Menjalankan di VPS...
echo.
REM  sed membuang carriage return Windows; tanpa itu bash menolak berkasnya
REM  dengan pesan "$'\r': command not found" yang membingungkan.
ssh %VPS% "sed -i 's/\r$//' /tmp/2-cek-dua-sisi.sh && bash /tmp/2-cek-dua-sisi.sh"
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
echo   Bandingkan angka baris VPS dengan isi LOKAL Anda.
echo.
echo     VPS LEBIH SEDIKIT / sama  -^> aman, lanjut ke 2-push-ke-vps.bat
echo     VPS LEBIH BANYAK          -^> ADA data produksi yang belum ada di
echo                                  komputer ini. Tarik dulu dengan
echo                                  6-tarik-dari-vps.bat, baru dorong.
echo.
echo   "unggahan_terakhir" lebih baru di VPS juga berarti hal yang sama.
echo.
echo   Kalau baris "target_pemenuhan_tbo" dan "no_cif" TIDAK muncul,
echo   berarti VPS memang belum menerima perubahan Agustus 2026 - itu
echo   wajar sebelum push pertama.
echo.
echo   Untuk melihat isi LOKAL sebagai pembanding, jalankan:
echo     "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d pmo -c "SELECT (SELECT count(*) FROM branchops_batches) AS batches, (SELECT count(*) FROM branchops_it_break) AS it_break, (SELECT count(*) FROM branchops_pencairan) AS pencairan, (SELECT count(*) FROM branchops_tbo) AS tbo;"
echo.
pause
exit /b 0
