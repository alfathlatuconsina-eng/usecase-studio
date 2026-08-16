#!/usr/bin/env bash
# =====================================================================
#  Dijalankan DI VPS oleh 0b-cek-disk-vps.bat lewat ssh.
#  HANYA MEMBACA. Tidak ada satu pun berkas yang dihapus, dipindahkan
#  atau diubah. Tidak ada layanan yang di-restart. Aman dijalankan
#  kapan saja, termasuk saat aplikasi sedang dipakai.
#
#  Menjawab satu pertanyaan: disk 8,7 GB itu isinya apa.
#
#  CATATAN PENTING SOAL ANGKA 8,7 GB - ini UKURAN disk, bukan jumlah
#  yang terpakai. Lihat "Pushing to the VPS - failure 1" di CLAUDE.md:
#  "The VPS disk is 8.7 GB and it HAS hit 100%". Jadi persoalannya
#  bukan ada sesuatu yang menggelembung sampai 8,7 GB, melainkan
#  seluruh disknya memang hanya sebesar itu dan berkali-kali penuh.
#  Yang perlu dicari adalah apa yang TUMBUH, bukan apa yang besar.
#
#  Pasangannya: 0c-bersihkan-vps.bat, yang membersihkan.
# =====================================================================
set -uo pipefail          # sengaja TANPA -e: satu perintah yang tidak
                          # tersedia tidak boleh menghentikan laporan

garis() { printf '%s\n' "-------------------------------------------------------------------"; }
judul() { echo; garis; echo "  $*"; garis; }

echo "==================================================================="
echo "  LAPORAN DISK VPS   $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "  hanya membaca - tidak ada yang diubah"
echo "==================================================================="

judul "1. Ruang disk"
df -h / 2>/dev/null
echo
echo "  inode (bisa habis walau byte masih sisa):"
df -i / 2>/dev/null | tail -1

judul "1b. SWAP - ditambahkan 16 Agu 2026, dan ternyata yang TERBESAR"
# Pada pemeriksaan pertama 16 Agu 2026, /swapfile (1,0 GB) dan /swapfile2
# (1,5 GB) bersama-sama memakai 2,5 GB - 38% dari seluruh ruang terpakai,
# lebih besar daripada segala hal lain di mesin ini. Versi pertama skrip
# ini tidak menyebutnya sama sekali; keduanya hanya muncul kebetulan di
# daftar "berkas lebih dari 20 MB". Sesuatu sebesar itu harus punya
# bagiannya sendiri.
#
# JANGAN buru-buru menghapus. Swap yang dibuang dari mesin ber-RAM kecil
# membuat proses dimatikan OOM killer, dan itu jauh lebih mahal daripada
# 1 GB disk. Yang dicari di sini: apakah KEDUANYA memang dipakai.
echo "  berkas swap yang ADA di disk:"
ls -lh /swapfile* 2>/dev/null | awk '{ printf "    %-8s %s\n", $5, $9 }' || echo "    (tidak ada)"
echo
echo "  yang benar-benar AKTIF menurut kernel:"
swapon --show 2>/dev/null | sed 's/^/    /' || echo "    (tidak ada yang aktif)"
echo
echo "  memori:"
free -h 2>/dev/null | sed 's/^/    /'
echo
SWAP_AKTIF=$(swapon --show --noheadings 2>/dev/null | wc -l)
RAM_MB=$(free -m 2>/dev/null | awk '/^Mem:/{print $2}')
echo "  Cara membacanya - dan URUTAN pertanyaannya penting:"
echo
if [ "${SWAP_AKTIF:-0}" -eq 0 ]; then
  echo "  >>> TIDAK ADA SWAP YANG AKTIF SAMA SEKALI. <<<"
  echo
  echo "  Kalau ada berkas swap di daftar teratas, jangan buru-buru"
  echo "  menghapusnya. Mesin ini punya RAM ${RAM_MB:-?} MB dan sedang"
  echo "  berjalan TANPA jaring pengaman: begitu memori habis, kernel"
  echo "  membunuh proses - bisa postgres, bisa pmo.service - tanpa"
  echo "  peringatan apa pun. Itu jauh lebih mahal daripada 1 GB disk."
  echo
  echo "  Yang benar: NYALAKAN satu, HAPUS sisanya."
  echo "    swapon /swapfile2 && swapon --show     # kalau gagal: mkswap dulu"
  echo "    grep swap /etc/fstab                   # supaya bertahan reboot"
  echo "    rm -f /swapfile                        # baru hapus yang tidak dipakai"
  echo
  echo "  Berkas swap yang tidak masuk /etc/fstab akan mati lagi pada"
  echo "  reboot berikutnya, dan tidak ada yang memberi tahu Anda."
else
  echo "  Berkas yang ADA di disk tetapi TIDAK muncul di daftar aktif"
  echo "  adalah ruang terbuang - hapus yang itu saja, sesudah memastikan"
  echo "  yang aktif memang mencukupi."
  echo "  Mengurangi swap yang sedang AKTIF: swapoff dulu, jangan rm"
  echo "  langsung, dan hanya kalau kolom 'used' pada baris Swap kecil."
fi

judul "2. Direktori terbesar (kedalaman 2, tidak melintasi mount lain)"
du -x -h --max-depth=2 / 2>/dev/null | sort -rh | head -22

judul "3. Berkas tunggal lebih dari 20 MB"
find / -xdev -type f -size +20M -printf '%10s  %TY-%Tm-%Td  %p\n' 2>/dev/null \
  | sort -rn | head -25 \
  | awk '{ printf "  %8.1f MB  %s  %s\n", $1/1048576, $2, $3 }'

judul "4. Cadangan SQL di /root  - INI PENYEBAB YANG BERULANG"
# Setiap kali 2-push-ke-vps.bat berjalan, langkah 1/7 menulis dua berkas
# ke sini dan tidak ada yang pernah menghapusnya. Lima percobaan dalam
# satu malam pada 8 Agu 2026 meninggalkan ~150 MB.
if ls /root/*.sql >/dev/null 2>&1; then
  ls -lht --time-style=long-iso /root/*.sql | awk '{ printf "  %s  %s %s  %s\n", $5, $6, $7, $9 }'
  echo
  echo "  jumlah berkas : $(ls -1 /root/*.sql 2>/dev/null | wc -l)"
  echo "  total ukuran  : $(du -ch /root/*.sql 2>/dev/null | tail -1 | cut -f1)"
  echo
  echo "  yang akan DISIMPAN oleh 0c-bersihkan-vps (2 terbaru per keluarga):"
  for pola in 'pmo-sebelum-push-*' 'bo-vps-sebelum-push-*'; do
    ls -1t /root/$pola.sql 2>/dev/null | head -2 | sed 's/^/     simpan  /'
  done
  echo "  yang akan DIHAPUS:"
  {
    for pola in 'pmo-sebelum-push-*' 'bo-vps-sebelum-push-*'; do
      ls -1t /root/$pola.sql 2>/dev/null | tail -n +3
    done
  } | sed 's/^/     hapus   /' || true
else
  echo "  (tidak ada /root/*.sql - bagus)"
fi

judul "5. Cache - semuanya aman dihapus dan akan terbentuk lagi sendiri"
for d in /root/.npm /root/.cache /home/*/.npm /home/*/.cache \
         /var/cache/apt/archives /var/lib/apt/lists; do
  [ -d "$d" ] && printf "  %10s  %s\n" "$(du -sh "$d" 2>/dev/null | cut -f1)" "$d"
done

judul "6. Log systemd"
journalctl --disk-usage 2>/dev/null || echo "  journalctl tidak tersedia"
echo
echo "  log terbesar di /var/log:"
du -ah /var/log 2>/dev/null | sort -rh | head -8 | sed 's/^/    /'

judul "7. Berkas TERHAPUS yang masih dipegang proses"
# Ruangnya tidak kembali sampai prosesnya di-restart. Pada 8 Agu 2026
# ada enam berkas seperti ini dan itu bagian dari sebab disk penuh.
ADA=0
for fd in /proc/[0-9]*/fd/*; do
  tautan=$(readlink "$fd" 2>/dev/null) || continue
  case "$tautan" in
    *"(deleted)")
      ukuran=$(stat -Lc%s "$fd" 2>/dev/null) || continue
      [ "${ukuran:-0}" -lt 1048576 ] && continue      # abaikan yang kecil
      pid=$(echo "$fd" | cut -d/ -f3)
      nama=$(cat /proc/$pid/comm 2>/dev/null)
      printf "  %8.1f MB  pid %-7s %-16s %s\n" \
             "$(echo "$ukuran" | awk '{print $1/1048576}')" "$pid" "$nama" "${tautan% (deleted)}"
      ADA=1 ;;
  esac
done
[ "$ADA" -eq 0 ] && echo "  (tidak ada yang berarti - bagus)"
echo
echo "  Kalau ada isinya: ruang itu HANYA kembali setelah prosesnya"
echo "  di-restart. 0c-bersihkan-vps sengaja TIDAK melakukannya sendiri -"
echo "  me-restart layanan produksi adalah keputusan Anda, bukan skrip."

judul "8. PostgreSQL"
sudo -u postgres psql -tAc "
  SELECT '  basis data ' || datname || ' : ' || pg_size_pretty(pg_database_size(datname))
    FROM pg_database WHERE datistemplate = false ORDER BY pg_database_size(datname) DESC;" 2>/dev/null \
  || echo "  tidak bisa membaca ukuran basis data"
echo
echo "  WAL (log tulis-di-muka):"
du -sh "$(sudo -u postgres psql -tAc 'SHOW data_directory' 2>/dev/null)/pg_wal" 2>/dev/null \
  | sed 's/^/    /' || echo "    tidak terbaca"
echo
echo "  sepuluh tabel terbesar di pmo:"
sudo -u postgres psql -d pmo -tAc "
  SELECT '    ' || rpad(relname, 26) || pg_size_pretty(pg_total_relation_size(c.oid))
    FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
   WHERE n.nspname = 'public' AND c.relkind = 'r'
   ORDER BY pg_total_relation_size(c.oid) DESC LIMIT 10;" 2>/dev/null

judul "9. Kernel lama (sering ratusan MB, dibersihkan apt autoremove)"
dpkg -l 'linux-image-*' 2>/dev/null | awk '/^ii/ { print "  " $2 }' || true
echo "  kernel yang sedang dipakai: $(uname -r)"

judul "10. JANGAN DIHAPUS - ini data, bukan sampah"
for d in /opt/pmo/uploads /opt/pmo/uploads/elibrary; do
  [ -d "$d" ] && printf "  %10s  %s\n" "$(du -sh "$d" 2>/dev/null | cut -f1)" "$d"
done
echo "  Berkas unggahan E-Library. CLAUDE.md: jangan pernah dihapus"
echo "  tanpa bertanya. Tidak disentuh oleh skrip pembersih mana pun."
echo
echo "  Dump berisi NAMA NASABAH ASLI (penyamaran ada di lapisan API,"
echo "  bukan di berkas). Ini memang layak dihapus, dengan shred:"
for f in /tmp/lokal-branchops.sql /tmp/vps-branchops.sql; do
  [ -f "$f" ] && printf "  %10s  %s   <-- masih ada\n" "$(du -h "$f" | cut -f1)" "$f"
done

judul "SELESAI"
echo "  Tidak ada yang diubah. Untuk membersihkan: 0c-bersihkan-vps.bat"
echo "  yang bawaannya juga hanya melapor sampai Anda mengetik BERSIHKAN."
echo
