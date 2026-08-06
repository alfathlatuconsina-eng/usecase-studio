#!/usr/bin/env bash
# =====================================================================
#  Dijalankan DI VPS oleh 6-tarik-dari-vps.bat lewat ssh.
#  Hanya MEMBACA. Tidak ada INSERT, UPDATE, DELETE, DROP atau ALTER
#  yang dijalankan terhadap basis data VPS.
#
#  Mengekspor STRUKTUR + ISI sebelas tabel modul Branch Ops.
#
#  KENAPA struktur ikut diekspor (berubah 6 Agu 2026):
#  Percobaan sebelumnya gagal karena branchops_branches di VPS masih
#  punya kolom 'region', yang sudah dibuang di lokal lewat
#  hapus-kolom-region-lama.sql. Ekspor data-saja mengandaikan kedua
#  sisi berbentuk sama - dan itu tidak benar. Dengan membawa struktur
#  sekaligus, tabel dibuat ulang persis seperti di VPS, jadi tidak ada
#  lagi kemungkinan kolom tidak cocok, sekarang atau nanti.
#
#  --clean --if-exists membuat berkasnya berisi DROP TABLE lalu
#  CREATE TABLE lalu INSERT. Sisi lokal menjalankannya dalam SATU
#  transaksi, jadi kalau ada yang gagal, tabel lama tetap utuh.
#
#  DUA tabel sengaja TIDAK diekspor:
#    branchops_users  - berisi akun login. Kalau ikut ditimpa, sandi
#                       lokal berubah jadi sandi VPS dan Anda bisa
#                       terkunci di luar dashboard sendiri.
#    branchops_audit  - jejak audit lokal adalah catatan pekerjaan Anda
#                       di komputer ini.
#
#  Hasil: /tmp/vps-branchops.sql
# =====================================================================
set -euo pipefail

DB=pmo
PSQL="sudo -u postgres psql -d $DB"
PGDUMP="sudo -u postgres pg_dump -d $DB"

TABEL=(
  branchops_branches branchops_ref_values
  branchops_role_menus branchops_settings
  branchops_batches branchops_stg
  branchops_issues branchops_it_break
  branchops_pencairan branchops_tbo
  branchops_rekon
)

echo "== Isi Branch Ops di VPS =="

NTAB=$($PSQL -tAc "SELECT count(*) FROM pg_tables
                    WHERE schemaname='public' AND tablename LIKE 'branchops%'")
if [ "$NTAB" -eq 0 ]; then
  echo "BERHENTI: VPS tidak punya tabel branchops_* sama sekali."
  exit 3
fi

# Pastikan kesebelas tabel memang ada sebelum diekspor. Tanpa ini,
# pg_dump diam-diam melewati tabel yang tidak ada dan hasilnya berkas
# yang tampak wajar tapi kurang satu tabel.
HILANG=""
for t in "${TABEL[@]}"; do
  ADA=$($PSQL -tAc "SELECT count(*) FROM pg_tables
                     WHERE schemaname='public' AND tablename='$t'")
  [ "$ADA" -eq 0 ] && HILANG="$HILANG $t"
done
if [ -n "$HILANG" ]; then
  echo "BERHENTI: tabel berikut tidak ada di VPS:$HILANG"
  exit 6
fi

$PSQL -c "
  SELECT 'branches'   AS tabel, count(*) FROM branchops_branches
  UNION ALL SELECT 'ref_values', count(*) FROM branchops_ref_values
  UNION ALL SELECT 'role_menus', count(*) FROM branchops_role_menus
  UNION ALL SELECT 'settings',   count(*) FROM branchops_settings
  UNION ALL SELECT 'batches',    count(*) FROM branchops_batches
  UNION ALL SELECT 'stg',        count(*) FROM branchops_stg
  UNION ALL SELECT 'issues',     count(*) FROM branchops_issues
  UNION ALL SELECT 'it_break',   count(*) FROM branchops_it_break
  UNION ALL SELECT 'pencairan',  count(*) FROM branchops_pencairan
  UNION ALL SELECT 'tbo',        count(*) FROM branchops_tbo
  UNION ALL SELECT 'rekon',      count(*) FROM branchops_rekon
  ORDER BY 1;"

NROW=$($PSQL -tAc "SELECT sum(c) FROM (
          SELECT count(*) c FROM branchops_it_break
          UNION ALL SELECT count(*) FROM branchops_pencairan
          UNION ALL SELECT count(*) FROM branchops_tbo) t")
if [ "$NROW" -eq 0 ]; then
  echo "BERHENTI: tabel branchops_* di VPS ADA tapi seluruhnya KOSONG."
  echo "Menariknya hanya akan mengosongkan data lokal Anda."
  exit 4
fi

echo
echo "== Mengekspor struktur + isi =="

ARG=()
for t in "${TABEL[@]}"; do ARG+=(-t "$t"); done

# --clean --if-exists : DROP dulu, baru CREATE. Berkasnya jadi mandiri.
# --no-owner --no-privileges : peran di VPS (misal 'postgres' milik VPS)
#   tidak selalu ada di komputer lokal; tanpa ini pemuatan gagal dengan
#   "role does not exist".
# --column-inserts : INSERT menyebut nama kolomnya, lebih mudah dibaca
#   dan diperiksa daripada blok COPY.
$PGDUMP --clean --if-exists --no-owner --no-privileges --column-inserts \
  "${ARG[@]}" -f /tmp/vps-branchops.sql

chmod 600 /tmp/vps-branchops.sql

echo
ls -l /tmp/vps-branchops.sql
echo "tabel_dibuat=$(grep -c '^CREATE TABLE' /tmp/vps-branchops.sql)"
echo "EKSPOR-SELESAI"
