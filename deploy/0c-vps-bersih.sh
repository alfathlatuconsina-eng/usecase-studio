#!/usr/bin/env bash
# =====================================================================
#  Dijalankan DI VPS oleh 0c-bersihkan-vps.bat lewat ssh.
#
#  DUA MODE, dan bawaannya yang aman:
#    bash 0c-vps-bersih.sh              -> LAPORAN saja, tidak menghapus
#    bash 0c-vps-bersih.sh BERSIHKAN    -> benar-benar menghapus
#
#  Laporan menghitung dan menyebutkan setiap berkas yang akan dihapus
#  beserta ukurannya, jadi tidak ada yang hilang tanpa Anda lihat dulu.
#
#  YANG TIDAK PERNAH DISENTUH, disebut di sini supaya tidak perlu
#  dibaca dari kodenya:
#    - basis data PostgreSQL. Tidak ada satu pun perintah SQL di berkas
#      ini. VACUUM sekalipun tidak.
#    - /opt/pmo dan seluruh isinya, termasuk .git
#    - /opt/pmo/uploads/** - berkas unggahan E-Library. CLAUDE.md:
#      "never delete these without asking".
#    - dua cadangan SQL TERBARU dari tiap keluarga di /root
#    - berkas terhapus yang masih dipegang proses. Hanya dilaporkan;
#      membebaskannya berarti me-restart layanan, dan me-restart
#      produksi adalah keputusan Anda.
# =====================================================================
set -uo pipefail

MODE="${1:-LAPORAN}"
NYATA=0
[ "$MODE" = "BERSIHKAN" ] && NYATA=1

SIMPAN=2                 # berapa cadangan terbaru per keluarga dipertahankan
JOURNAL_MAKS=50M         # log systemd dipangkas sampai sebesar ini.
                         # Dulu 100M - dan pada pemeriksaan 16 Agu 2026
                         # journal-nya 92 MB, jadi angka itu tidak akan
                         # membebaskan apa pun. Ambang yang tidak pernah
                         # tercapai sama saja dengan tidak ada.

total_kb=0
garis() { printf '%s\n' "-------------------------------------------------------------------"; }

kb() { du -sk "$1" 2>/dev/null | cut -f1; }
mb() { awk -v k="${1:-0}" 'BEGIN{ printf "%.1f MB", k/1024 }'; }

catat() {   # catat <kb> <keterangan>
  total_kb=$((total_kb + ${1:-0}))
  printf "     %10s  %s\n" "$(mb "${1:-0}")" "$2"
}

echo "==================================================================="
if [ "$NYATA" -eq 1 ]; then
  echo "  PEMBERSIHAN DISK VPS - MODE NYATA, BERKAS AKAN DIHAPUS"
else
  echo "  PEMBERSIHAN DISK VPS - MODE LAPORAN, TIDAK ADA YANG DIHAPUS"
fi
echo "  $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo "==================================================================="
echo
echo "  Sebelum:"
df -h / | tail -1 | awk '{ printf "     ukuran %s, terpakai %s (%s), sisa %s\n", $2, $3, $5, $4 }'
SISA_AWAL=$(df -k / | tail -1 | awk '{print $4}')

# ------------------------------------------------------------------ 1
echo
garis
echo "  1. Cadangan SQL lama di /root"
garis
echo "     Sebabnya struktural: tiap kali 2-push-ke-vps.bat berjalan,"
echo "     langkah 1/7 menulis dua berkas ke sini dan tidak ada yang"
echo "     pernah menghapusnya. $SIMPAN terbaru tiap keluarga disimpan."
echo
BUANG=""
for pola in 'pmo-sebelum-push-' 'bo-vps-sebelum-push-'; do
  simpan=$(ls -1t /root/${pola}*.sql 2>/dev/null | head -$SIMPAN)
  buang=$(ls -1t /root/${pola}*.sql 2>/dev/null | tail -n +$((SIMPAN+1)))
  [ -n "$simpan" ] && echo "$simpan" | sed 's/^/     SIMPAN  /'
  if [ -n "$buang" ]; then
    while IFS= read -r f; do
      [ -n "$f" ] || continue
      catat "$(kb "$f")" "hapus  $f"
      BUANG="$BUANG$f"$'\n'
    done <<< "$buang"
  fi
done
[ -z "$BUANG" ] && echo "     (tidak ada yang perlu dihapus)"

# ------------------------------------------------------------------ 2
echo
garis
echo "  2. Cache - terbentuk lagi sendiri, tidak ada data di dalamnya"
garis
CACHE=""
# /var/lib/apt/lists DITAMBAHKAN 16 Agu 2026. Pemeriksaan pertama
# menemukannya 193 MB - lebih besar daripada seluruh cadangan SQL di
# /root yang selama ini dianggap penyebab utama. apt-get clean TIDAK
# menyentuhnya; hanya /var/cache/apt/archives yang ia bereskan.
# Akibat yang perlu diketahui: sesudah ini apt tidak bisa memasang
# apa pun sampai "apt-get update" dijalankan sekali. Itu saja.
for d in /root/.npm/_cacache /root/.cache /var/cache/apt/archives /var/lib/apt/lists; do
  if [ -d "$d" ]; then
    k=$(kb "$d")
    if [ "${k:-0}" -gt 1024 ]; then
      catat "$k" "kosongkan  $d"
      CACHE="$CACHE$d"$'\n'
    fi
  fi
done
[ -z "$CACHE" ] && echo "     (cache sudah kecil)"

# ------------------------------------------------------------------ 3
echo
garis
echo "  3. Log systemd"
garis
J=$(journalctl --disk-usage 2>/dev/null | grep -o '[0-9.]*[KMG]' | head -1)
echo "     sekarang: ${J:-tidak terbaca}, akan dipangkas ke $JOURNAL_MAKS"

# ------------------------------------------------------------------ 3b
echo
garis
echo "  3b. Catatan login GAGAL yang sudah dirotasi"
garis
echo "     /var/log/btmp mencatat percobaan masuk yang GAGAL. Pada 16 Agu"
echo "     2026 isinya 26 MB - itu banyak, dan artinya ada yang rutin"
echo "     mencoba menebak SSH Anda. Wajar untuk server yang terbuka ke"
echo "     internet, tapi layak Anda ketahui."
echo
echo "     Yang dihapus HANYA btmp.1, salinan lama hasil rotasi. btmp yang"
echo "     sedang aktif dibiarkan - itu jejak yang masih berjalan."
BTMP=""
if [ -f /var/log/btmp.1 ]; then
  catat "$(kb /var/log/btmp.1)" "hapus  /var/log/btmp.1"
  BTMP=/var/log/btmp.1
else
  echo "     (tidak ada btmp.1)"
fi

# ------------------------------------------------------------------ 4
echo
garis
echo "  4. Dump berisi NAMA NASABAH ASLI"
garis
echo "     Penyamaran \"***\" terjadi di lapisan API, bukan di berkas ini."
echo "     Dihapus dengan shred, bukan rm."
RAHASIA=""
for f in /tmp/lokal-branchops.sql /tmp/vps-branchops.sql /tmp/6-vps-ekspor.sh; do
  if [ -f "$f" ]; then
    catat "$(kb "$f")" "shred  $f"
    RAHASIA="$RAHASIA$f"$'\n'
  fi
done
[ -z "$RAHASIA" ] && echo "     (tidak ada - sudah bersih)"

# ------------------------------------------------------------------ 5
echo
garis
echo "  5. Paket dan kernel lama - DILAPORKAN saja, tidak dihapus skrip ini"
garis
# grep -c keluar dengan status 1 saat hitungannya nol, jadi || true -
# bukan || echo 0, yang akan mencetak "0" dua kali.
BUANGABLE=$(apt-get -s autoremove --purge 2>/dev/null | grep -c '^Remv' || true)
echo "     paket yang bisa dibuang apt: ${BUANGABLE:-0}"
echo "     kernel terpasang:"
dpkg -l 'linux-image-*' 2>/dev/null | awk '/^ii/ { print "       " $2 }'
echo "     kernel dipakai sekarang: $(uname -r)"
echo
echo "     Menghapus kernel lama biasanya aman dan sering membebaskan"
echo "     ratusan MB, tetapi ia menyentuh /boot dan butuh reboot untuk"
echo "     benar-benar rapi. Jalankan sendiri kalau memang mau:"
echo "       apt-get autoremove --purge"

# ------------------------------------------------------------------ 6
echo
garis
echo "  6. Berkas terhapus yang masih dipegang proses - DILAPORKAN saja"
garis
ADA=0
for fd in /proc/[0-9]*/fd/*; do
  t=$(readlink "$fd" 2>/dev/null) || continue
  case "$t" in *"(deleted)")
    u=$(stat -Lc%s "$fd" 2>/dev/null) || continue
    [ "${u:-0}" -lt 10485760 ] && continue
    pid=$(echo "$fd" | cut -d/ -f3)
    printf "     %10s  pid %-7s %-16s %s\n" \
      "$(mb $((u/1024)))" "$pid" "$(cat /proc/$pid/comm 2>/dev/null)" "${t% (deleted)}"
    ADA=1 ;;
  esac
done
[ "$ADA" -eq 0 ] && echo "     (tidak ada yang berarti)"
[ "$ADA" -eq 1 ] && {
  echo
  echo "     Ruang ini HANYA kembali setelah prosesnya di-restart, dan"
  echo "     skrip ini sengaja tidak melakukannya: salah satunya bisa"
  echo "     saja pmo.service, dan mematikan produksi bukan efek samping"
  echo "     yang pantas dari sebuah pembersih disk."
}

# ------------------------------------------------------------------
echo
garis
printf "  PERKIRAAN YANG DIBEBASKAN: %s\n" "$(mb "$total_kb")"
garis

if [ "$NYATA" -eq 0 ]; then
  echo
  echo "  MODE LAPORAN - tidak ada satu pun berkas yang dihapus."
  echo "  Kalau daftar di atas sudah Anda setujui, jalankan lagi dengan"
  echo "  mengetik BERSIHKAN saat diminta."
  echo
  exit 0
fi

echo
echo "  MENGHAPUS..."
if [ -n "$BUANG" ]; then
  while IFS= read -r f; do [ -n "$f" ] && rm -f -- "$f" && echo "     dihapus  $f"; done <<< "$BUANG"
fi
if [ -n "$CACHE" ]; then
  while IFS= read -r d; do
    [ -n "$d" ] || continue
    case "$d" in
      /var/cache/apt/archives) apt-get clean >/dev/null 2>&1 && echo "     apt clean" ;;
      /var/lib/apt/lists) rm -rf -- /var/lib/apt/lists/* 2>/dev/null &&
        echo "     dikosongkan  /var/lib/apt/lists  (jalankan apt-get update sebelum memasang paket)" ;;
      *) rm -rf -- "${d:?}"/* 2>/dev/null && echo "     dikosongkan  $d" ;;
    esac
  done <<< "$CACHE"
fi
journalctl --vacuum-size=$JOURNAL_MAKS >/dev/null 2>&1 && echo "     journal dipangkas ke $JOURNAL_MAKS"
[ -n "$BTMP" ] && rm -f -- "$BTMP" && echo "     dihapus  $BTMP"
if [ -n "$RAHASIA" ]; then
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    if command -v shred >/dev/null 2>&1; then shred -u -- "$f" && echo "     di-shred  $f"
    else rm -f -- "$f" && echo "     dihapus (shred tidak ada)  $f"; fi
  done <<< "$RAHASIA"
fi

echo
echo "  Sesudah:"
df -h / | tail -1 | awk '{ printf "     ukuran %s, terpakai %s (%s), sisa %s\n", $2, $3, $5, $4 }'
SISA_AKHIR=$(df -k / | tail -1 | awk '{print $4}')
printf "     benar-benar dibebaskan: %s\n" "$(mb $((SISA_AKHIR - SISA_AWAL)))"
echo
echo "  Basis data, /opt/pmo dan uploads/ tidak disentuh sama sekali."
echo
