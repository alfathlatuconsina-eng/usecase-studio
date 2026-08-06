#!/usr/bin/env bash
# =====================================================================
#  Dijalankan DI VPS, HANYA MEMBACA. Tidak mengubah apa pun.
#  Dipanggil 2-push-ke-vps.bat sebelum apa pun dikirim, supaya isi VPS
#  terlihat lebih dulu dan bisa dibandingkan dengan isi lokal.
#
#  Kenapa penting: VPS adalah PRODUKSI. Kalau di sana ada unggahan yang
#  belum pernah ada di komputer lokal, mendorong data lokal akan
#  MENGHAPUSNYA. Angka di bawah adalah satu-satunya cara mengetahuinya
#  sebelum terlambat.
# =====================================================================
set -euo pipefail
DB=pmo
PSQL="sudo -u postgres psql -d $DB -tA"

echo "VPS-CEK-MULAI"
echo "waktu=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

for t in branchops_branches branchops_batches branchops_it_break \
         branchops_pencairan branchops_tbo branchops_rekon branchops_users; do
  ada=$($PSQL -c "SELECT count(*) FROM pg_tables
                   WHERE schemaname='public' AND tablename='$t'")
  if [ "$ada" -eq 0 ]; then echo "$t=TIDAK_ADA"; else
    echo "$t=$($PSQL -c "SELECT count(*) FROM $t")"
  fi
done

# Batch terakhir per jenis: kalau tanggalnya lebih baru daripada di lokal,
# ada unggahan produksi yang belum pernah ditarik ke lokal.
echo "--- batch terakhir per jenis (committed) ---"
$PSQL -c "
  SELECT jenis || '|' || max(id)::text || '|' || max(uploaded_at)::text
    FROM branchops_batches WHERE status='committed' GROUP BY jenis ORDER BY jenis;" \
  2>/dev/null || echo "(tabel batches belum ada)"

echo "--- unggahan 14 hari terakhir ---"
$PSQL -c "
  SELECT count(*) FROM branchops_batches
   WHERE uploaded_at > now() - interval '14 days';" 2>/dev/null || echo "0"

# Kolom Agustus 2026: kalau belum ada, VPS memang tertinggal dan push ini
# memang yang membawanya.
echo "--- kolom baru sudah ada di VPS? ---"
$PSQL -c "
  SELECT table_name || '.' || column_name
    FROM information_schema.columns
   WHERE table_name IN ('branchops_tbo','branchops_pencairan')
     AND column_name IN ('target_pemenuhan_tbo','status_tbo','no_cif','no_rekening')
   ORDER BY 1;" 2>/dev/null || true

echo "--- kolom lama 'region' masih ada di VPS? ---"
$PSQL -c "
  SELECT count(*) FROM information_schema.columns
   WHERE table_name='branchops_branches' AND column_name='region';"

echo "--- git di /opt/pmo ---"
cd /opt/pmo 2>/dev/null && {
  echo "commit=$(git rev-parse --short HEAD)"
  n=$(git status --porcelain | wc -l)
  echo "perubahan_belum_commit=$n"
} || echo "commit=(folder tidak ditemukan)"

echo "VPS-CEK-SELESAI"
