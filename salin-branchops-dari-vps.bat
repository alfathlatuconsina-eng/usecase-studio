@echo off
REM ======================================================================
REM  Menyalin HANYA modul Branch Ops dari VPS ke komputer lokal
REM
REM  Bedanya dengan sync-dari-vps.bat: skrip itu menyalin SELURUH database
REM  pmo (kelima dashboard). Skrip ini hanya menyentuh tabel branchops_*,
REM  sesuai aturan di CLAUDE.md bahwa dashboard lain tidak boleh terganggu.
REM
REM  Urutan sengaja dibuat begini: tidak ada apa pun dihapus di lokal
REM  sebelum terbukti VPS memang punya data untuk disalin.
REM
REM    0. PERIKSA dulu: apakah VPS punya tabel branchops_* berisi data?
REM       Kalau tidak -> berhenti, database lokal tidak disentuh sama sekali.
REM    1. Tampilkan isi lokal sekarang, supaya terlihat apa yang dipertaruhkan
REM    2. Cadangkan SELURUH database lokal -> berkas bertanggal
REM    3. Tarik tabel branchops_* dari VPS (pg_dump, hanya MEMBACA)
REM    4. Periksa hasil tarikan: ukuran, penanda akhir, jumlah tabel
REM    5. Baru terapkan ke lokal
REM    6. Bandingkan jumlah baris sesudahnya
REM
REM  VPS tidak diubah sama sekali. pg_dump dan psql SELECT hanya membaca.
REM
REM  CATATAN PENTING - tabel branchops_users TIDAK ikut disalin.
REM  Tabel itu berisi akun login Branch Ops. Kalau ikut ditimpa, sandi
REM  lokal Anda berubah jadi sandi VPS dan Anda bisa terkunci di luar.
REM  Yang disalin hanya tabel DATA.
REM ======================================================================
REM ----------------------------------------------------------------------
REM  Jaring pengaman: kalau berkas ini dibuka dengan KLIK DUA KALI, skrip
REM  menjalankan ulang dirinya di jendela cmd yang TIDAK menutup sendiri.
REM  Dengan begitu, seandainya ada kesalahan, pesannya masih terbaca dan
REM  tidak hilang bersama jendelanya.
REM ----------------------------------------------------------------------
if not "%~1"=="lanjut" (
    cmd /k ""%~f0" lanjut"
    exit /b
)

setlocal EnableDelayedExpansion
cd /d "%~dp0"

set VPS=root@159.65.139.45
set VPSDB=pmo
set LOKALDB=pmo
set STAMP=%DATE:~-4%%DATE:~3,2%%DATE:~0,2%-%TIME:~0,2%%TIME:~3,2%
set STAMP=%STAMP: =0%
set BACKUP=backup-lokal-sebelum-branchops-%STAMP%.sql
set FRESH=vps-branchops-%STAMP%.sql

echo.
echo ============================================================
echo   SALIN MODUL BRANCH OPS   VPS  -^>  LOKAL
echo ============================================================
echo   Sumber  : %VPS% , database %VPSDB%      ^(hanya dibaca^)
echo   Tujuan  : localhost , database %LOKALDB%
echo   Cakupan : tabel branchops_* saja, KECUALI branchops_users
echo.
echo   Dashboard lain ^(PMO, People, Quality, E-Library^) tidak disentuh.
echo.

REM ---------- cari PostgreSQL lokal ----------
set PGBIN=
for %%V in (18 17 16 15) do (
    if exist "C:\Program Files\PostgreSQL\%%V\bin\psql.exe" (
        if "!PGBIN!"=="" set "PGBIN=C:\Program Files\PostgreSQL\%%V\bin"
    )
)
if "%PGBIN%"=="" ( echo   GAGAL: PostgreSQL tidak ditemukan. & pause & exit /b 1 )
set "PSQL=%PGBIN%\psql.exe"
set "PGDUMP=%PGBIN%\pg_dump.exe"
echo   PostgreSQL lokal: %PGBIN%

where ssh >nul 2>&1
if not %errorlevel%==0 (
    echo.
    echo   GAGAL: perintah ssh tidak ada.
    echo   Pasang lewat: Settings ^> Apps ^> Optional features ^> OpenSSH Client
    pause & exit /b 1
)

REM ---------- sandi postgres lokal ----------
echo.
set /p PGPASSWORD=  Kata sandi 'postgres' lokal:
"%PSQL%" -U postgres -h localhost -c "SELECT 1;" >nul 2>&1
if not %errorlevel%==0 ( echo   GAGAL: sandi salah atau layanan PostgreSQL mati. & pause & exit /b 1 )

REM ---------------------------------------------------------------- 0
echo.
echo [0/6] Memeriksa dulu apakah VPS punya data Branch Ops...
echo       ^(kalau tidak ada, skrip berhenti dan lokal tidak disentuh^)

ssh -o ConnectTimeout=15 %VPS% "echo ok" >nul 2>&1
if not %errorlevel%==0 (
    echo   GAGAL: tidak bisa masuk ke %VPS%. Periksa koneksi dan kunci SSH.
    echo   Database lokal TIDAK disentuh.
    pause & exit /b 1
)

REM  Hasil perintah jarak jauh ditulis ke berkas sementara lalu dibaca.
REM  Cara ini dipakai supaya tidak perlu menyarangkan tanda kutip di dalam
REM  for /f - penyarangan itulah yang membuat jendela cmd tertutup mendadak.
ssh %VPS% "sudo -u postgres psql -d %VPSDB% -tAc \"SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'branchops%%'\"" > _cek_tabel.txt 2>nul
set NTAB_VPS=0
if exist _cek_tabel.txt set /p NTAB_VPS=<_cek_tabel.txt
del _cek_tabel.txt 2>nul
REM  buang spasi, lalu pastikan benar-benar angka (kalau bukan, anggap 0)
set NTAB_VPS=%NTAB_VPS: =%
echo %NTAB_VPS%| findstr /R "^[0-9][0-9]*$" >nul || set NTAB_VPS=0
echo   Tabel branchops_* di VPS : %NTAB_VPS%

if %NTAB_VPS% LEQ 0 (
    echo.
    echo   ============================================================
    echo   BERHENTI - VPS tidak punya tabel branchops_* sama sekali.
    echo.
    echo   Artinya modul Branch Ops belum pernah dipasang di VPS,
    echo   jadi tidak ada yang bisa disalin. Kalau skrip diteruskan,
    echo   data Branch Ops LOKAL Anda justru akan terhapus dan diganti
    echo   tabel kosong.
    echo.
    echo   Database lokal TIDAK disentuh. Tidak ada yang berubah.
    echo   ============================================================
    echo.
    pause & exit /b 1
)

REM  hitung baris sungguhan pada tiga tabel fakta utama
ssh %VPS% "sudo -u postgres psql -d %VPSDB% -tAc \"SELECT sum(c) FROM (SELECT count(*) c FROM branchops_it_break UNION ALL SELECT count(*) FROM branchops_pencairan UNION ALL SELECT count(*) FROM branchops_tbo) t\"" > _cek_baris.txt 2>nul
set NROW_VPS=0
if exist _cek_baris.txt set /p NROW_VPS=<_cek_baris.txt
del _cek_baris.txt 2>nul
set NROW_VPS=%NROW_VPS: =%
echo %NROW_VPS%| findstr /R "^[0-9][0-9]*$" >nul || set NROW_VPS=0
echo   Baris data di VPS        : %NROW_VPS%  ^(it_break + pencairan + tbo^)

if %NROW_VPS% LEQ 0 (
    echo.
    echo   PERINGATAN: tabel di VPS ADA, tapi seluruhnya KOSONG.
    echo   Menyalin ini akan MENGHAPUS data Branch Ops lokal Anda
    echo   dan menggantinya dengan tabel kosong.
    echo.
    echo   Ketik  TETAP  bila memang itu yang Anda inginkan.
    set /p K0=  ^>
    if /I not "!K0!"=="TETAP" ( echo   Dibatalkan. Tidak ada yang berubah. & pause & exit /b 0 )
)

REM ---------------------------------------------------------------- 1
echo.
echo [1/6] Isi Branch Ops di database LOKAL sekarang ^(yang dipertaruhkan^):
"%PSQL%" -U postgres -h localhost -d %LOKALDB% -c "SELECT (SELECT count(*) FROM branchops_it_break) AS it_break, (SELECT count(*) FROM branchops_pencairan) AS pencairan, (SELECT count(*) FROM branchops_tbo) AS tbo, (SELECT count(*) FROM branchops_batches) AS batch;" 2>nul
if not %errorlevel%==0 echo   ^(tabel branchops_* lokal belum ada - tidak ada yang hilang^)

echo.
echo   Ketik  SALIN  untuk melanjutkan, atau apa saja untuk batal.
set /p KONFIRM=  ^>
if /I not "%KONFIRM%"=="SALIN" ( echo   Dibatalkan. Tidak ada yang berubah. & pause & exit /b 0 )

REM ---------------------------------------------------------------- 2
echo.
echo [2/6] Mencadangkan SELURUH database lokal lebih dahulu...
"%PGDUMP%" -U postgres -h localhost --clean --if-exists %LOKALDB% > "%BACKUP%" 2>nul
if not %errorlevel%==0 (
    echo   GAGAL mencadangkan database lokal.
    echo   Demi keamanan skrip dihentikan. Lokal TIDAK disentuh.
    del "%BACKUP%" 2>nul
    pause & exit /b 1
)
set SZ=0
for %%A in ("%BACKUP%") do set SZ=%%~zA
if "!SZ!"=="" set SZ=0
echo   Tersimpan: %BACKUP%  ^(!SZ! byte^)
if !SZ! LSS 1000 (
    echo   PERINGATAN: cadangan mencurigakan kecil. Dibatalkan demi keamanan.
    pause & exit /b 1
)

REM ---------------------------------------------------------------- 3
echo.
echo [3/6] Menarik tabel branchops_* dari VPS ^(hanya membaca^)...
REM  -t  = hanya tabel yang cocok pola ini
REM  -T  = kecualikan tabel akun login, agar sandi lokal tidak tertimpa
ssh %VPS% "sudo -u postgres pg_dump --clean --if-exists -t 'branchops_*' -T 'branchops_users' %VPSDB%" > "%FRESH%"
if not %errorlevel%==0 (
    echo   GAGAL menarik dari VPS.
    echo   Database lokal TIDAK disentuh. Cadangan tetap ada: %BACKUP%
    del "%FRESH%" 2>nul
    pause & exit /b 1
)

REM ---------------------------------------------------------------- 4
echo.
echo [4/6] Memeriksa hasil tarikan sebelum apa pun ditimpa...
set FSZ=0
for %%A in ("%FRESH%") do set FSZ=%%~zA
if "%FSZ%"=="" set FSZ=0
echo   Ukuran berkas : %FSZ% byte
if %FSZ% LSS 2000 (
    echo   GAGAL: berkas terlalu kecil, hampir pasti tidak lengkap.
    echo   Database lokal TIDAK disentuh. Cadangan: %BACKUP%
    pause & exit /b 1
)
findstr /C:"PostgreSQL database dump complete" "%FRESH%" >nul
if not %errorlevel%==0 (
    echo   GAGAL: penanda akhir dump tidak ditemukan - tarikan terpotong.
    echo   Database lokal TIDAK disentuh. Cadangan: %BACKUP%
    pause & exit /b 1
)
set NTAB=0
for /f %%C in ('findstr /R /C:"^CREATE TABLE" "%FRESH%" ^| find /c /v ""') do set NTAB=%%C
if "%NTAB%"=="" set NTAB=0
echo   Tabel di dalam dump : %NTAB%
if %NTAB% LSS 3 (
    echo   GAGAL: jumlah tabel tidak wajar untuk modul Branch Ops.
    echo   Database lokal TIDAK disentuh. Cadangan: %BACKUP%
    pause & exit /b 1
)
REM  Palang terakhir: pastikan dump BENAR-BENAR hanya berisi tabel branchops_*.
REM  Kalau ada satu saja tabel lain, dashboard lain bisa ikut tertimpa.
findstr /R /C:"^CREATE TABLE " "%FRESH%" | findstr /V /C:"branchops" >nul
if %errorlevel%==0 (
    echo   GAGAL: dump berisi tabel DI LUAR branchops_* - tidak aman diterapkan
    echo   karena bisa menimpa dashboard lain. Lokal TIDAK disentuh.
    pause & exit /b 1
)
echo   Tarikan terlihat lengkap dan hanya berisi tabel branchops_*.

REM ---------------------------------------------------------------- 5
echo.
echo [5/6] Menerapkan ke database lokal...
"%PSQL%" -U postgres -h localhost -d %LOKALDB% -v ON_ERROR_STOP=0 -q -f "%FRESH%" 2>nul
if not %errorlevel%==0 echo   Ada pesan saat menerapkan. Lanjut ke pemeriksaan hasil.

REM ---------------------------------------------------------------- 6
echo.
echo [6/6] Isi Branch Ops di lokal SEKARANG:
"%PSQL%" -U postgres -h localhost -d %LOKALDB% -c "SELECT (SELECT count(*) FROM branchops_it_break) AS it_break, (SELECT count(*) FROM branchops_pencairan) AS pencairan, (SELECT count(*) FROM branchops_tbo) AS tbo, (SELECT count(*) FROM branchops_batches) AS batch;"

echo.
echo ============================================================
echo   SELESAI
echo.
echo   Cadangan sebelum tindakan : %BACKUP%
echo   Salinan mentah dari VPS   : %FRESH%
echo.
echo   Untuk kembali ke kondisi sebelum skrip ini:
echo     "%PSQL%" -U postgres -h localhost -d %LOKALDB% -f "%BACKUP%"
echo.
echo   PERHATIAN - kedua berkas .sql di atas berisi NAMA NASABAH ASLI
echo   dalam bentuk terbaca. Penyamaran "***" hanya berlaku di aplikasi,
echo   bukan di dalam berkas dump. Simpan aman, dan hapus bila sudah
echo   tidak diperlukan. Jangan ikut disalin ke Git.
echo.
echo   Akun login Branch Ops lokal Anda tidak berubah.
echo   Langkah berikutnya: jalankan backend\run_local.bat, lalu
echo   backend\cek_masking.py untuk memastikan nama tetap tersamar.
echo ============================================================
echo.
pause
