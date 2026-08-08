@echo off
REM ===================================================================
REM  2 - DORONG BRANCH OPS DARI LOKAL KE VPS
REM      kode (lewat git) + struktur tabel + data
REM
REM  Panduan lengkap: deploy\RUNBOOK-branchops-ke-vps.md
REM ===================================================================
REM
REM  VPS ADALAH PRODUKSI. Skrip ini MENGUBAHNYA. Bacalah dua hal ini:
REM
REM  1. Data branchops di VPS DIGANTI oleh data lokal. Kalau di VPS ada
REM     unggahan yang belum pernah ditarik ke komputer ini, unggahan itu
REM     HILANG. Langkah 2 menampilkan isi kedua sisi supaya bisa
REM     dibandingkan sebelum melanjutkan - baca angkanya, jangan dilewati.
REM
REM  2. Yang TIDAK disentuh di VPS:
REM       branchops_users   akun login produksi. Menimpanya mengganti
REM                         sandi produksi dengan sandi percobaan lokal.
REM                         Untuk memindahkan akun, pakai
REM                         3-pengguna-pilih-satu.sql.
REM       branchops_audit   jejak audit produksi. Itu catatan yang paling
REM                         perlu dipercaya; menimpanya merusaknya.
REM       Dashboard PMO, People, Quality, E-Library - tidak tersentuh.
REM
REM  SEBELAS tabel yang didorong:
REM    branchops_branches   branchops_ref_values
REM    branchops_role_menus branchops_settings
REM    branchops_batches    branchops_stg
REM    branchops_issues     branchops_it_break
REM    branchops_pencairan  branchops_tbo
REM    branchops_rekon
REM ===================================================================

if not "%~1"=="lanjut" (
    cmd /k ""%~f0" lanjut"
    exit /b
)

setlocal EnableDelayedExpansion
cd /d "%~dp0"

set VPS=root@159.65.139.45
set PGUSER=postgres
set PGDB=pmo
set HERE=%~dp0
set KELUAR=%HERE%keluaran
set DUMP=%KELUAR%\lokal-branchops.sql

set PGBIN=
for %%V in (18 17 16 15) do (
    if exist "C:\Program Files\PostgreSQL\%%V\bin\psql.exe" (
        if "!PGBIN!"=="" set "PGBIN=C:\Program Files\PostgreSQL\%%V\bin"
    )
)
if "%PGBIN%"=="" ( echo   GAGAL: PostgreSQL tidak ditemukan. & pause & exit /b 1 )
set "PSQL=%PGBIN%\psql.exe"
set "PGDUMP=%PGBIN%\pg_dump.exe"

where ssh >nul 2>&1 || ( echo   GAGAL: perintah ssh tidak ada. & pause & exit /b 1 )
where git >nul 2>&1 || ( echo   GAGAL: perintah git tidak ada. & pause & exit /b 1 )

echo.
echo ===================================================================
echo   DORONG BRANCH OPS   LOKAL  -^>  VPS   ^(PRODUKSI^)
echo ===================================================================
echo.

REM ---------------------------------------------------------------- 0
echo [0/6] Menguji sambungan...
set /p PGPASSWORD=  Kata sandi 'postgres' LOKAL ^(kosongkan kalau tanpa sandi^):
"%PSQL%" -U %PGUSER% -h localhost -d %PGDB% -c "SELECT 1;" >nul 2>&1
if not %errorlevel%==0 ( echo   GAGAL menghubungi PostgreSQL lokal. & pause & exit /b 1 )
echo   PostgreSQL lokal OK
ssh -o ConnectTimeout=15 %VPS% "echo ok" >nul 2>&1
if not %errorlevel%==0 ( echo   GAGAL: tidak bisa masuk ke %VPS%. & pause & exit /b 1 )
echo   sambungan VPS OK

REM ---------------------------------------------------------------- 1
echo.
echo [1/6] Kode: pastikan sudah di-commit dan di-push
git status --porcelain > "%TEMP%\gitstat.txt"
for /f %%A in ("%TEMP%\gitstat.txt") do set GSZ=%%~zA
if not "!GSZ!"=="0" (
  echo.
  echo   Ada berkas yang belum di-commit:
  git status --short
  echo.
  echo   VPS mengambil kode lewat "git pull", jadi apa pun yang belum
  echo   di-push TIDAK akan ikut. Commit dan push dulu:
  echo.
  echo     git add -A
  echo     git commit -m "Branch Ops: TBO target + layar edit + tarik/dorong VPS"
  echo     git push origin main
  echo.
  set /p TETAP=  Ketik TETAP untuk lanjut tanpa itu, atau Enter untuk berhenti:
  if /i not "!TETAP!"=="TETAP" ( del "%TEMP%\gitstat.txt" 2>nul & pause & exit /b 0 )
) else ( echo   pohon kerja bersih )
del "%TEMP%\gitstat.txt" 2>nul

REM ---------------------------------------------------------------- 2
echo.
echo [2/6] Membandingkan isi LOKAL dan VPS  ^(hanya membaca^)
echo.
echo   --- LOKAL ---
"%PSQL%" -U %PGUSER% -h localhost -d %PGDB% -c "SELECT (SELECT count(*) FROM branchops_branches) AS cabang, (SELECT count(*) FROM branchops_batches) AS batches, (SELECT count(*) FROM branchops_it_break) AS it_break, (SELECT count(*) FROM branchops_pencairan) AS pencairan, (SELECT count(*) FROM branchops_tbo) AS tbo, (SELECT count(*) FROM branchops_rekon) AS rekon;"
"%PSQL%" -U %PGUSER% -h localhost -d %PGDB% -c "SELECT jenis, max(id) AS batch_terakhir, max(uploaded_at) AS unggahan_terakhir FROM branchops_batches WHERE status='committed' GROUP BY jenis ORDER BY jenis;"
echo.
echo   --- VPS ---
scp -q "%HERE%2-cek-dua-sisi.sh" %VPS%:/tmp/2-cek-dua-sisi.sh
if not %errorlevel%==0 ( echo   GAGAL menyalin skrip pemeriksa. & pause & exit /b 1 )
ssh %VPS% "sed -i 's/\r$//' /tmp/2-cek-dua-sisi.sh && bash /tmp/2-cek-dua-sisi.sh"
if not %errorlevel%==0 ( echo   GAGAL memeriksa VPS. Tidak ada yang diubah. & pause & exit /b 1 )

echo.
echo ===================================================================
echo   BANDINGKAN ANGKA DI ATAS SEBELUM MELANJUTKAN
echo ===================================================================
echo.
echo   Kalau baris VPS LEBIH BANYAK, atau "unggahan terakhir" di VPS
echo   lebih baru daripada di lokal, berarti ada data produksi yang
echo   belum pernah ditarik ke komputer ini. Melanjutkan akan
echo   MENGHAPUSNYA.
echo.
echo   Dalam hal itu: BERHENTI, jalankan deploy\6-tarik-dari-vps.bat
echo   lebih dulu, lalu ulangi dari sini.
echo.
echo   ^>^>^> Ketik  PUSH  lalu Enter untuk melanjutkan. ^<^<^<
echo.
set /p LANJUT=  Jawab:
if /i not "!LANJUT!"=="PUSH" ( echo. & echo   Dibatalkan. VPS tidak disentuh. & pause & exit /b 0 )

REM ---------------------------------------------------------------- 3
echo.
echo [3/6] Mengekspor struktur + data dari LOKAL
if not exist "%KELUAR%" mkdir "%KELUAR%"
REM  --clean --if-exists : berkasnya mandiri (DROP lalu CREATE lalu INSERT)
REM  --no-owner --no-privileges : peran 'postgres' lokal tidak selalu sama
REM     dengan di VPS; tanpa ini pemuatan gagal "role does not exist"
"%PGDUMP%" -U %PGUSER% -h localhost -d %PGDB% ^
  --clean --if-exists --no-owner --no-privileges --column-inserts ^
  -t branchops_branches   -t branchops_ref_values ^
  -t branchops_role_menus -t branchops_settings ^
  -t branchops_batches    -t branchops_stg ^
  -t branchops_issues     -t branchops_it_break ^
  -t branchops_pencairan  -t branchops_tbo ^
  -t branchops_rekon ^
  -f "%DUMP%"
if errorlevel 1 ( echo   GAGAL mengekspor. VPS tidak disentuh. & pause & exit /b 1 )
for %%A in ("%DUMP%") do (
  echo   %%~nxA : %%~zA byte
  if %%~zA LSS 1000 ( echo   GAGAL: ekspor hampir kosong. & pause & exit /b 1 )
)
findstr /b /c:"CREATE TABLE" "%DUMP%" >nul
if errorlevel 1 ( echo   GAGAL: ekspor tidak memuat CREATE TABLE. & pause & exit /b 1 )

REM ---------------------------------------------------------------- 4
echo.
echo [4/6] Mengirim ke VPS
scp -q "%DUMP%" %VPS%:/tmp/lokal-branchops.sql
if not %errorlevel%==0 ( echo   GAGAL mengirim dump. VPS tidak disentuh. & pause & exit /b 1 )
scp -q "%HERE%2-vps-muat.sh" %VPS%:/tmp/2-vps-muat.sh
if not %errorlevel%==0 ( echo   GAGAL mengirim skrip pemuat. & pause & exit /b 1 )
echo   terkirim

REM ---------------------------------------------------------------- 5
echo.
echo [5/6] Menjalankan pemuatan DI VPS
echo        ^(cadangan, git pull, layanan mati sebentar, muat, hidupkan^)
echo.
REM  Seluruh keluaran VPS disimpan ke berkas. Jendela cmd memotong riwayat,
REM  dan pesan galat pentingnya justru yang tergulung hilang - tanpa catatan
REM  ini, kegagalan hanya bisa ditebak.
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmm"') do set STAMP=%%i
set LOG=%KELUAR%\push-log-%STAMP%.txt
REM  JANGAN salurkan keluaran ssh lewat powershell di sini. Versi sebelumnya
REM  memakai:
REM
REM      ssh ... 2>&1 | powershell -Command "$input | Tee-Object -FilePath X -Encoding utf8"
REM
REM  dan itu GAGAL SELALU di Windows PowerShell 5.1 (bawaan Windows 10/11):
REM  Tee-Object di sana TIDAK punya parameter -Encoding, parameter itu baru
REM  ada di PowerShell 6+. Akibatnya powershell mati seketika saat mengikat
REM  parameter, salurannya putus, dan ssh ikut terbunuh DI TENGAH JALAN -
REM  skrip di VPS berhenti setelah membuat cadangan, sebelum git pull.
REM  Berkas catatan tidak pernah dibuat, findstr gagal membacanya, dan skrip
REM  ini melaporkan "GAGAL DI SISI VPS" padahal VPS tidak apa-apa. Kejadian
REM  8 Agu 2026; dua cadangan sia-sia tertinggal di /root.
REM
REM  Sekarang keluaran ssh langsung ditulis ke berkas, lalu dicetak. Tidak
REM  ada powershell, jadi tidak ada yang bisa memutus salurannya. Berkasnya
REM  berisi byte apa adanya dari VPS (UTF-8), bukan UTF-16 - jadi terbaca di
REM  editor mana pun DAN bisa dibaca findstr.
REM
REM  Yang hilang hanya keluaran langsung: layar diam sekitar 30 detik, baru
REM  seluruh catatan tercetak sekaligus. Itu pertukaran yang sepadan dengan
REM  pemuatan yang tidak terputus di tengah.
ssh %VPS% "sed -i 's/\r$//' /tmp/2-vps-muat.sh && bash /tmp/2-vps-muat.sh" > "%LOG%" 2>&1
set RC_SSH=%errorlevel%
type "%LOG%"
REM  Keberhasilan tetap ditentukan penanda yang dicetak skrip VPS di baris
REM  terakhirnya, bukan errorlevel: skrip itu bisa saja keluar dengan kode 0
REM  padahal berhenti lebih awal. RC_SSH hanya dipakai untuk pesan yang lebih
REM  jelas kalau sambungannya sendiri yang putus.
findstr /c:"SELESAI. Cadangan:" "%LOG%" >nul
if errorlevel 1 (
  if not "%RC_SSH%"=="0" echo   ^(ssh keluar dengan kode %RC_SSH% - sambungan putus atau skrip VPS berhenti^)
  goto :gagal_vps
)
echo.
echo   catatan lengkap: %LOG%

REM ---------------------------------------------------------------- 6
echo.
echo [6/6] Selesai
echo ===================================================================
echo.
echo   BACA angka pemeriksaan di atas.
echo   Yang perlu dilihat:
echo     - jumlah baris di VPS sekarang sama dengan di lokal
echo     - kolom baru ^(target_pemenuhan_tbo, status_tbo, no_cif,
echo       no_rekening^) muncul di kedua tabel
echo     - daftar "pengguna VPS yang jatahnya jadi kosong" idealnya
echo       kosong; kalau ada nama, perbaiki lewat tab Pengguna di VPS
echo.
echo   Lalu buka https://159.65.139.45/branchops-login.html dan periksa:
echo     - keempat dashboard terisi
echo     - nama nasabah tetap tersamar ^(***^)
echo     - unggah satu berkas Excel percobaan ^(membuktikan sequence benar^)
echo     - dashboard lain ^(PMO, People, Quality, E-Library^) masih normal
echo.
echo   Berkas berisi nama nasabah asli - hapus kalau sudah tidak perlu:
echo     del "%DUMP%"
echo     ssh %VPS% "shred -u /tmp/lokal-branchops.sql"
echo.
pause
exit /b 0

:gagal_vps
echo.
echo ===================================================================
echo   GAGAL DI SISI VPS
echo ===================================================================
echo.
echo   Catatan lengkap tersimpan di:
echo     %LOG%
echo.
echo   Baris terakhir dari catatan itu:
echo   -----------------------------------------------------------------
powershell -NoProfile -Command "if (Test-Path '%LOG%') { Get-Content '%LOG%' -Tail 18 }"
echo   -----------------------------------------------------------------
echo.
echo   Skrip di VPS berhenti pada langkah yang tercetak terakhir.
echo.
echo   Pemuatan dibungkus satu transaksi, jadi kalau gagal di langkah 4,
echo   tabel VPS tetap seperti semula.
echo.
echo   Kalau layanan tertinggal mati:
echo     ssh %VPS% "sudo systemctl start pmo.service"
echo.
echo   Untuk memulihkan tabel branchops di VPS ^(cadangan dibuat di
echo   langkah 1, namanya tercetak di atas^):
echo     ssh %VPS%
echo     sudo -u postgres psql -d pmo -1 -v ON_ERROR_STOP=1 -f ~/bo-vps-sebelum-push-^<stempel^>.sql
echo     sudo systemctl restart pmo.service
echo.
pause
exit /b 1
