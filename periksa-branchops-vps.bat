@echo off
REM ======================================================================
REM  PERIKSA data Branch Ops di VPS  -  HANYA MEMBACA
REM
REM  Skrip ini TIDAK mengubah apa pun, di VPS maupun di komputer lokal.
REM  Tidak ada pg_dump, tidak ada psql ke database lokal, tidak ada
REM  DROP / CREATE / INSERT. Hanya menghitung isi tabel branchops_* di VPS
REM  lalu menampilkannya di layar.
REM
REM  Tujuannya menjawab satu pertanyaan sebelum menyalin apa pun:
REM     "Apakah VPS benar-benar punya data Branch Ops?"
REM
REM  Latar belakang: cadangan vps-sebelum-push-20260726-2231.sql (26 Juli)
REM  berisi 18 tabel dan TIDAK ada satu pun tabel branchops_*. Kalau itu
REM  masih berlaku, menyalin dari VPS ke lokal justru akan MENGHAPUS data
REM  Branch Ops lokal dan menggantinya dengan tabel kosong.
REM ======================================================================
REM  Jaring pengaman: kalau dibuka dengan KLIK DUA KALI, jalankan ulang di
REM  jendela cmd yang tidak menutup sendiri, supaya pesan tetap terbaca.
if not "%~1"=="lanjut" (
    cmd /k ""%~f0" lanjut"
    exit /b
)

setlocal EnableDelayedExpansion
cd /d "%~dp0"

set VPS=root@159.65.139.45
set VPSDB=pmo

echo.
echo ============================================================
echo   PERIKSA BRANCH OPS DI VPS   ^(hanya membaca^)
echo ============================================================
echo   Server   : %VPS%
echo   Database : %VPSDB%
echo.
echo   Skrip ini tidak mengubah apa pun. Aman dijalankan.
echo.

REM ---------- pastikan ssh ada ----------
where ssh >nul 2>&1
if not %errorlevel%==0 (
    echo   GAGAL: perintah ssh tidak ditemukan.
    echo   Pasang lewat: Settings ^> Apps ^> Optional features ^> OpenSSH Client
    echo.
    pause & exit /b 1
)

echo [1/3] Menghubungi VPS...
ssh -o ConnectTimeout=10 %VPS% "echo terhubung" >nul 2>&1
if not %errorlevel%==0 (
    echo   GAGAL: tidak bisa masuk ke %VPS%.
    echo   Periksa koneksi internet dan kunci SSH Anda.
    echo   Tidak ada yang berubah di mana pun.
    echo.
    pause & exit /b 1
)
echo   Terhubung.

REM ---------------------------------------------------------------- 2
echo.
echo [2/3] Daftar tabel branchops_* yang ADA di VPS:
echo ------------------------------------------------------------
ssh %VPS% "sudo -u postgres psql -d %VPSDB% -c \"SELECT tablename AS tabel FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'branchops%%' ORDER BY tablename;\""
echo ------------------------------------------------------------
echo   ^(Kalau daftar di atas kosong / '0 rows', artinya VPS BELUM
echo    punya modul Branch Ops sama sekali.^)

REM ---------------------------------------------------------------- 3
echo.
echo [3/3] Jumlah baris per tabel branchops_* di VPS:
echo ------------------------------------------------------------
REM  Query ini membangun sendiri perintah hitung untuk tiap tabel yang ada,
REM  jadi tidak error kalau sebagian tabel belum dibuat.
ssh %VPS% "sudo -u postgres psql -d %VPSDB% -t -A -F' = ' -c \"SELECT relname, n_live_tup FROM pg_stat_user_tables WHERE relname LIKE 'branchops%%' ORDER BY relname;\""
echo ------------------------------------------------------------
echo   Catatan: angka di atas adalah perkiraan cepat dari statistik
echo   PostgreSQL. Untuk modul yang kosong angkanya 0.
echo.

echo ============================================================
echo   SELESAI - tidak ada yang diubah
echo.
echo   Cara membaca hasilnya:
echo.
echo   * Daftar kosong, atau semua angka 0
echo       -^> VPS tidak punya data Branch Ops.
echo          JANGAN menyalin dari VPS ke lokal: data lokal Anda
echo          akan tertimpa tabel kosong.
echo.
echo   * Ada tabel dengan jumlah baris ^> 0
echo       -^> VPS memang punya data. Beri tahu saya angkanya,
echo          nanti saya buatkan skrip salin khusus branchops_*
echo          yang mencadangkan database lokal lebih dulu.
echo ============================================================
echo.
pause
