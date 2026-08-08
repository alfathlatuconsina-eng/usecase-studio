#!/usr/bin/env bash
# =====================================================================
#  Dijalankan DI VPS oleh 2-push-ke-vps.bat lewat ssh.
#  Arah: LOKAL -> VPS.
#
#  Ini SATU-SATUNYA berkas di deploy/ yang MENGUBAH basis data VPS.
#  Semua yang lain hanya membaca. Baca seluruhnya sebelum dipakai.
#
#  Urutannya:
#    1. cadangkan SELURUH basis data pmo di VPS
#    2. tarik kode terbaru dari git
#    3. matikan layanan  (migrasi tidak boleh jalan 3x bersamaan)
#    4. muat struktur + data branchops dalam SATU transaksi
#    5. terapkan schema.sql (migrasi lokal, idempoten)
#    6. setel ulang sequence
#    7. hidupkan layanan, lalu periksa
#
#  branchops_users dan branchops_audit TIDAK ikut dimuat - lihat
#  komentar di 2-push-ke-vps.bat.
# =====================================================================
set -euo pipefail

DB=pmo
APP=/opt/pmo                       # WorkingDirectory pmo.service = /opt/pmo/backend
SVC=pmo.service
DUMP=/tmp/lokal-branchops.sql
PSQL="sudo -u postgres psql -d $DB -v ON_ERROR_STOP=1"
STAMP=$(date +%Y%m%d-%H%M)

if [ ! -s "$DUMP" ]; then
  echo "BERHENTI: $DUMP tidak ada atau kosong."; exit 2
fi
if ! grep -q '^CREATE TABLE' "$DUMP"; then
  echo "BERHENTI: $DUMP tidak memuat CREATE TABLE."
  echo "Itu ekspor data-saja; strukturnya tidak ikut dan pemuatan akan gagal"
  echo "kalau kolom kedua sisi berbeda. Ulangi ekspor dari komputer lokal."
  exit 3
fi

echo "== 1/7  Mencadangkan seluruh basis data VPS =="
sudo -u postgres pg_dump "$DB" > ~/pmo-sebelum-push-$STAMP.sql
ls -lh ~/pmo-sebelum-push-$STAMP.sql
if [ "$(stat -c%s ~/pmo-sebelum-push-$STAMP.sql)" -lt 10000 ]; then
  echo "BERHENTI: cadangan terlalu kecil, mencurigakan."; exit 4
fi

# Cadangan per-tabel juga - inilah yang dipakai kalau perlu mundur tanpa
# mengganggu keempat dashboard lain.
sudo -u postgres pg_dump -d "$DB" --clean --if-exists --no-owner \
  --no-privileges --column-inserts \
  -t branchops_branches   -t branchops_ref_values \
  -t branchops_role_menus -t branchops_settings \
  -t branchops_batches    -t branchops_stg \
  -t branchops_issues     -t branchops_it_break \
  -t branchops_pencairan  -t branchops_tbo \
  -t branchops_rekon \
  > ~/bo-vps-sebelum-push-$STAMP.sql
echo "cadangan per-tabel: ~/bo-vps-sebelum-push-$STAMP.sql"

echo
echo "== 2/7  Menarik kode terbaru dari git =="
cd "$APP"

# Berhenti HANYA kalau ada berkas TERLACAK yang disunting langsung di VPS.
# Menimpa suntingan darurat produksi diam-diam adalah cara paling mudah
# kehilangannya.
#
# --untracked-files=no PENTING. Tanpa itu, berkas nyasar yang memang tidak
# pernah masuk repo — cadangan *.bak lama, skrip patch sekali pakai,
# lampiran .xlsx — ikut terhitung dan push berhenti tanpa alasan yang
# benar. Berkas seperti itu tidak akan tersentuh `git pull`, dan kalau
# suatu saat memang bentrok, git sendiri yang menolak dan menyebut nama
# berkasnya. Itu penjagaan yang tepat, di tempat yang tepat.
KOTOR=$(git status --porcelain --untracked-files=no)
if [ -n "$KOTOR" ]; then
  echo "BERHENTI: ada berkas TERLACAK yang berubah di $APP:"
  echo "$KOTOR"
  echo
  echo "Ini suntingan langsung di produksi. Simpan dulu:"
  echo "    cd $APP && git stash        # atau salin berkasnya"
  echo "lalu jalankan lagi push dari komputer lokal."
  exit 5
fi

# Berkas nyasar hanya DILAPORKAN, tidak menghentikan apa pun.
NYASAR=$(git status --porcelain --untracked-files=normal | grep '^??' || true)
if [ -n "$NYASAR" ]; then
  echo "Catatan: ada berkas tak terlacak di $APP (diabaikan, tidak akan"
  echo "tersentuh git pull). Bersihkan sendiri kalau memang sampah:"
  echo "$NYASAR" | sed 's/^/    /'
  echo
fi

git pull --ff-only origin main
git log --oneline -3

echo
echo "== 3/7  Mematikan layanan =="
# ensure_schema() jalan saat app.py diimpor, dan gunicorn mengimpornya
# SEKALI PER WORKER. Dengan 3 worker, migrasi yang sama berjalan tiga kali
# bersamaan; pemeriksaan IF NOT EXISTS terjadi sebelum kunci tabel didapat,
# jadi dua worker bisa sama-sama menyimpulkan kolomnya belum ada.
sudo systemctl stop "$SVC"
sleep 1

echo
echo "== 3b  Memeriksa ketergantungan sebelum DROP =="
# pg_dump --clean menulis "DROP TABLE IF EXISTS ..." TANPA CASCADE.
# Kalau ada tabel LAIN di VPS yang menunjuk salah satu dari sebelas tabel
# ini lewat foreign key, DROP-nya gagal dengan
#   "cannot drop table ... because other objects depend on it"
# dan seluruh transaksi dibatalkan. Tersangka utama:
# branchops_user_menus, tabel mati peninggalan desain lama yang ada di
# VPS tapi tidak dipakai kode mana pun.
#
# Diperiksa lebih dulu supaya pesannya jelas, bukan galat mentah
# PostgreSQL di tengah pemuatan.
GANTUNG=$(sudo -u postgres psql -d "$DB" -tA -c "
  SELECT t.relname || ' -> ' || r.relname || '  (constraint ' || c.conname || ')'
    FROM pg_constraint c
    JOIN pg_class t ON t.oid = c.conrelid
    JOIN pg_class r ON r.oid = c.confrelid
   WHERE c.contype = 'f'
     AND r.relname IN ('branchops_branches','branchops_ref_values',
                       'branchops_role_menus','branchops_settings',
                       'branchops_batches','branchops_stg','branchops_issues',
                       'branchops_it_break','branchops_pencairan',
                       'branchops_tbo','branchops_rekon')
     AND t.relname NOT IN ('branchops_branches','branchops_ref_values',
                       'branchops_role_menus','branchops_settings',
                       'branchops_batches','branchops_stg','branchops_issues',
                       'branchops_it_break','branchops_pencairan',
                       'branchops_tbo','branchops_rekon');")

if [ -n "$GANTUNG" ]; then
  echo "BERHENTI: ada tabel di luar sebelas tabel ini yang menunjuk ke sana:"
  echo "$GANTUNG" | sed 's/^/    /'
  echo
  echo "DROP TABLE tanpa CASCADE akan gagal karenanya, dan seluruh"
  echo "pemuatan dibatalkan. Basis data VPS TIDAK diubah."
  echo
  echo "Kalau itu branchops_user_menus: tabel mati, 0 baris, tidak dibaca"
  echo "kode mana pun (lihat 'Dead tables' di CLAUDE.md). Periksa dulu,"
  echo "lalu buang sendiri kalau memang benar kosong:"
  echo "    sudo -u postgres psql -d $DB -c 'SELECT count(*) FROM branchops_user_menus;'"
  echo "    sudo -u postgres psql -d $DB -c 'DROP TABLE branchops_user_menus;'"
  echo "lalu jalankan push lagi dari komputer lokal."
  sudo systemctl start "$SVC" || true
  exit 7
fi
echo "  tidak ada ketergantungan dari luar - aman"

echo
echo "== 4/7  Memuat struktur + data (satu transaksi) =="
# -1: DROP, CREATE dan INSERT berdiri atau jatuh bersama. DDL di PostgreSQL
# ikut transaksional, jadi kegagalan meninggalkan tabel VPS apa adanya.
sudo -u postgres psql -d "$DB" -1 -v ON_ERROR_STOP=1 -f "$DUMP"

echo
echo "== 5/7  Menerapkan schema.sql =="
# Struktur yang baru masuk berasal dari lokal, jadi sudah benar. schema.sql
# tetap dijalankan untuk kolom milik branchops_users (region_class,
# branch_codes, CHECK jatah) yang TIDAK ikut dalam dump. Seluruhnya
# dijaga IF NOT EXISTS / IF EXISTS, aman diulang.
$PSQL -f "$APP/backend/branchops/schema.sql"

echo
echo "== 6/7  Menyetel ulang sequence =="
# pg_dump menulis id secara eksplisit, dan itu TIDAK menggerakkan sequence.
# Tanpa langkah ini unggahan Excel berikutnya di VPS gagal dengan
# "duplicate key" sementara datanya terlihat baik-baik saja.
$PSQL <<'SQL'
SELECT setval(pg_get_serial_sequence('branchops_ref_values','id'),
              COALESCE(MAX(id),1), MAX(id) IS NOT NULL) FROM branchops_ref_values;
SELECT setval(pg_get_serial_sequence('branchops_batches','id'),
              COALESCE(MAX(id),1), MAX(id) IS NOT NULL) FROM branchops_batches;
SELECT setval(pg_get_serial_sequence('branchops_stg','id'),
              COALESCE(MAX(id),1), MAX(id) IS NOT NULL) FROM branchops_stg;
SELECT setval(pg_get_serial_sequence('branchops_issues','id'),
              COALESCE(MAX(id),1), MAX(id) IS NOT NULL) FROM branchops_issues;
SELECT setval(pg_get_serial_sequence('branchops_it_break','id'),
              COALESCE(MAX(id),1), MAX(id) IS NOT NULL) FROM branchops_it_break;
SELECT setval(pg_get_serial_sequence('branchops_pencairan','id'),
              COALESCE(MAX(id),1), MAX(id) IS NOT NULL) FROM branchops_pencairan;
SELECT setval(pg_get_serial_sequence('branchops_tbo','id'),
              COALESCE(MAX(id),1), MAX(id) IS NOT NULL) FROM branchops_tbo;
SELECT setval(pg_get_serial_sequence('branchops_rekon','id'),
              COALESCE(MAX(id),1), MAX(id) IS NOT NULL) FROM branchops_rekon;
SQL

echo
echo "== 7/7  Menghidupkan layanan =="
sudo systemctl start "$SVC"
sleep 2
sudo systemctl is-active "$SVC" || { echo "LAYANAN TIDAK HIDUP"; \
  sudo journalctl -u "$SVC" -n 40 --no-pager; exit 6; }

echo
echo "=== Pemeriksaan ==="
$PSQL -c "
  SELECT 'branches' AS tabel, count(*) FROM branchops_branches
  UNION ALL SELECT 'batches',   count(*) FROM branchops_batches
  UNION ALL SELECT 'it_break',  count(*) FROM branchops_it_break
  UNION ALL SELECT 'pencairan', count(*) FROM branchops_pencairan
  UNION ALL SELECT 'tbo',       count(*) FROM branchops_tbo
  UNION ALL SELECT 'rekon',     count(*) FROM branchops_rekon
  UNION ALL SELECT 'users (tidak disentuh)', count(*) FROM branchops_users
  ORDER BY 1;"

echo
echo "--- kolom baru Agustus 2026 sudah ada? ---"
$PSQL -c "
  SELECT table_name, column_name
    FROM information_schema.columns
   WHERE table_name IN ('branchops_tbo','branchops_pencairan')
     AND column_name IN ('target_pemenuhan_tbo','status_tbo','tgl_tbo_lengkap',
                         'no_cif','no_rekening','tbo_updated_by','tbo_updated_at')
   ORDER BY 1,2;"

echo
echo "--- pengguna VPS yang jatahnya jadi kosong (master cabang diganti) ---"
$PSQL -c "
  SELECT email, role, region_class, branch_codes
    FROM branchops_users u
   WHERE u.role <> 'admin'
     AND ((u.region_class IS NOT NULL AND u.region_class <> 'SEMUA'
           AND NOT EXISTS (SELECT 1 FROM branchops_branches b
                            WHERE b.region_class = u.region_class))
       OR (u.branch_codes IS NOT NULL
           AND NOT EXISTS (SELECT 1 FROM branchops_branches b
                            WHERE b.branch_code = ANY(u.branch_codes))))
   ORDER BY email;"

echo
echo "SELESAI. Cadangan:"
echo "  ~/pmo-sebelum-push-$STAMP.sql        (seluruh basis data)"
echo "  ~/bo-vps-sebelum-push-$STAMP.sql     (tabel branchops saja)"
echo
echo "Berkas berisi NAMA NASABAH asli. Hapus kalau sudah tidak perlu:"
echo "  shred -u $DUMP"
