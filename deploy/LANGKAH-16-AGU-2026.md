# Langkah deploy — 16 Agustus 2026

Mendorong pekerjaan hari ini ke VPS: **program dan tabel sekaligus**,
karena data BranchOps di komputer lokal adalah yang paling mutakhir.

Lima tahap. Kerjakan **berurutan**, jangan melompat. Tiap langkah
menyebutkan apa yang harus terlihat kalau berhasil. **Kalau satu langkah
tidak sesuai, berhenti di situ** dan tanyakan — hampir semua kerusakan
mahal di catatan proyek ini terjadi karena satu langkah gagal lalu
langkah berikutnya tetap dijalankan.

---

## Dua hal yang perlu Anda tahu lebih dulu

**1. Satu skrip mengurus semuanya.** `2-push-ke-vps.bat` menarik kode di
langkah 2/7, memuat data di 4/7, menerapkan `schema.sql` di 5/7, dan
menghidupkan layanan di 7/7. Tidak perlu deploy kode terpisah.

**2. Ia memuat STRUKTUR + DATA** (`--clean --if-exists`), bukan data
saja. Ini penting hari ini: tabel di VPS dibuat ulang mengikuti struktur
lokal, jadi CHECK constraint yang baru ikut terbawa. Kalau ia memuat
data saja, setiap baris `Tidak ada TBO` akan ditolak CHECK lama di VPS
dan pemuatan gagal di 4/7 — dengan layanan sudah mati sejak 3/7.

**Yang TIDAK ikut terdorong, dan itu disengaja:** `branchops_users` dan
`branchops_audit`. Sandi dan jejak audit di VPS tetap milik VPS.

---

## Selalu jalankan ini dulu di setiap Command Prompt baru

Command Prompt terbuka di `C:\Users\...`, bukan di drive D.

    cd /d "D:\Claude Projects\UseCase-Studio.XYZ\Dashboard Development"

`/d` wajib — tanpa itu `cd` menolak pindah drive tanpa pesan apa pun.
Pastikan dengan `dir CLAUDE.md`.

---

## TAHAP 0 — Nyalakan swap di VPS (2 menit)

**Jangan dilewati.** Tahap 3 nanti memuat seluruh basis data ke
PostgreSQL di mesin ber-RAM **458 MB tanpa swap aktif**. Itu operasi
paling haus memori yang akan Anda jalankan hari ini. Kalau memori habis
di tengah pemuatan, kernel membunuh prosesnya dan Anda mendapat
produksi mati tanpa satu pun baris log yang menyebut sebabnya.

Dua berkas swap sudah ada di sana sejak Juni, keduanya mati.

**0.1** Nyalakan yang besar:

    ssh root@159.65.139.45 "swapon /swapfile2 && swapon --show && free -h"

Berhasil kalau baris `Swap:` menunjukkan sekitar **1,5 Gi**.

Kalau gagal dengan pesan seperti *invalid argument*, berkasnya belum
pernah diformat:

    ssh root@159.65.139.45 "mkswap /swapfile2 && swapon /swapfile2 && free -h"

**0.2** Supaya bertahan setelah reboot:

    ssh root@159.65.139.45 "grep -q '/swapfile2' /etc/fstab || echo '/swapfile2 none swap sw 0 0' >> /etc/fstab"

**0.3** Hapus yang tidak dipakai, sekalian membebaskan 1 GB:

    ssh root@159.65.139.45 "rm -f /swapfile && df -h /"

---

## TAHAP 1 — Uji di komputer sendiri (15 menit)

**Ini bukan tahap opsional.** Dump yang didorong ke VPS diambil DARI
basis data lokal Anda. Kalau migrasinya belum jalan di sini, yang
terdorong adalah data versi lama — dan VPS mendapat kode baru di atas
data lama.

### 1.1 Cadangkan — WAJIB

Dua migrasi berjalan sendiri saat backend dinyalakan:

1. `status_tbo_baku_migrasi` — `Dikecualikan` → `Tidak ada TBO`, di tabel
   TBO **dan** Pencairan, berikut membongkar-pasang dua CHECK constraint
2. `jenis_rekening_baku_migrasi` — 84 baris `jenis_rekening`

<!-- -->

    deploy\8-cadangkan-sebelum-restart.bat

Berhasil kalau muncul berkas baru di `deploy\cadangan\` berukuran
beberapa MB. **Catat namanya** — itu titik mundur Anda.

### 1.2 Nyalakan backend

    cd /d "D:\Claude Projects\UseCase-Studio.XYZ\Dashboard Development\backend"
    py -3 app.py

Biarkan jendela ini terbuka. Berhasil kalau tidak ada baris ERROR dan
aplikasi menyala di `http://localhost:8000`.

### 1.3 Periksa migrasi 1 — status TBO

Command Prompt **baru**:

    "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d pmo -c "SELECT 'tbo' AS tabel, status_tbo, count(*) FROM branchops_tbo GROUP BY 1,2 UNION ALL SELECT 'pencairan', status_tbo, count(*) FROM branchops_pencairan GROUP BY 1,2 ORDER BY 1,2;"

Harus hanya ada `Outstanding`, `Lengkap`, `Tidak ada TBO`.
**Satu baris pun `Dikecualikan` = berhenti.**

### 1.4 Periksa migrasi 2 — jenis rekening

    "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d pmo -c "SELECT COALESCE(jenis_rekening,'(kosong)') AS nilai, count(*) FROM branchops_tbo GROUP BY 1 ORDER BY 2 DESC;"

Harus terlihat:

    Non Perorangan (Perusahaan)   84
    Perorangan                    57
    Transfer                      31    <- baris bergeser kolom, memang dibiarkan
    Deposito                       3    <- sama
    (kosong)                       1

**`Perusahaan (Non Perorangan)` masih ada = berhenti.**

### 1.5 Periksa CHECK constraint ikut pindah

    "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -d pmo -c "SELECT conrelid::regclass, conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE contype='c' AND pg_get_constraintdef(oid) LIKE '%status_tbo%';"

Kedua definisinya harus menyebut `Tidak ada TBO`. Kalau salah satu masih
`Dikecualikan`, basis datanya setengah jalan — **berhenti**.

### 1.6 Lihat di layar

Buka `http://localhost:8000` → menu **TBO** → **Ubah** pada dua baris:

- **Baris biasa** — Jenis Rekening, Jenis Setoran, Jenis Produk kini
  kotak pilihan, dan Status TBO berbunyi `Tidak ada TBO`.
- **Baris dari batch 26** (Jenis Rekening-nya `Transfer`) — nilai itu
  harus **tetap muncul dan terpilih**. Tekan Simpan tanpa mengubah apa
  pun, buka lagi: masih `Transfer`. Kalau berubah jadi `Perorangan`,
  **berhenti** — data tertimpa diam-diam.

Cek juga menu **Pencairan** → Ubah: Status TBO di sana ikut berubah.

### 1.7 Uji unggah

Unggah `contoh\Template-03-Data-TBO.xlsx` lewat tab Unggah, lalu
**Batalkan**. Ini yang membuktikan sequence lokal masih benar.

---

## TAHAP 2 — Simpan ke git (5 menit)

Kode harus ada di GitHub sebelum tahap 3, karena VPS menarik dari sana.

### 2.1

    cd /d "D:\Claude Projects\UseCase-Studio.XYZ\Dashboard Development"
    git status

Harus muncul 13 berkas disunting dan 5 berkas baru di `deploy\`.
(`deploy\8-cadangkan-sebelum-restart.bat` yang tampak "modified" dari
Linux adalah artefak CRLF — di Windows tidak muncul.)

### 2.2

    git add -A
    git commit -m "Branch Ops: kotak pilihan di Ubah TBO, ejaan baku jenis_rekening, Dikecualikan jadi Tidak ada TBO, perkakas disk VPS"
    git push origin main

Berhasil kalau `git push` selesai tanpa galat. Kalau muncul
`Could not resolve host: github.com`, itu DNS — tunggu sebentar, ulangi
`git push origin main` saja.

---

## TAHAP 3 — Dorong ke VPS (10 menit)

### 3.1 Periksa dua sisi dulu — hanya membaca

    deploy\0-cek-vps.bat

Bandingkan jumlah baris VPS dengan lokal. **VPS lebih banyak** berarti
ada data produksi yang belum pernah ditarik ke sini — kalau begitu
**berhenti**, karena push akan menimpanya.

### 3.2 Jalankan push

    deploy\2-push-ke-vps.bat

Skripnya berhenti dan bertanya sebelum mengubah apa pun. Baca dulu,
baru jawab.

**Yang harus terlihat, tujuh langkah sampai habis:**

- `1/7` cadangan VPS dibuat
- `2/7` **Fast-forward** — kalau muncul kata *merge*, VPS punya commit
  sendiri, berhenti dan tanyakan
- `4a` `3 baris khusus versi baru dibuang` (PG18 → PG16, wajar)
- `4/7` pemuatan selesai tanpa ERROR
- `5/7` `schema.sql` — NOTICE "already exists, skipping" itu normal
- `6/7` sequence disetel ulang
- `7/7` layanan `active`
- baris terakhir: **`SELESAI. Cadangan:`**

Marker terakhir itulah yang dicari skripnya. **Kalau ia tidak muncul,
push belum selesai** apa pun yang tercetak sebelumnya.

### 3.3 Kalau push gagal di tengah

Layanan dimatikan di 3/7 dan baru dihidupkan di 7/7. Gagal di antaranya
= **produksi mati tanpa pemberitahuan**. Perintah pertama, selalu:

    ssh root@159.65.139.45 "systemctl start pmo && systemctl is-active pmo"

Baru cari sebabnya.

---

## TAHAP 4 — Periksa hasilnya (5 menit)

### 4.1 Tabel di VPS

    ssh root@159.65.139.45 "sudo -u postgres psql -d pmo -c \"SELECT 'tbo' AS t, status_tbo, count(*) FROM branchops_tbo GROUP BY 1,2 UNION ALL SELECT 'pencairan', status_tbo, count(*) FROM branchops_pencairan GROUP BY 1,2 ORDER BY 1,2;\""

Angkanya harus sama dengan langkah 1.3.

**Tidak ada perbaikan tangan yang perlu dijalankan setelah push ini.**
Itu tidak selalu begitu — lihat kegagalan 8 di CLAUDE.md: push data
membawa `branchops_settings` berisi kunci penjaga, jadi `schema.sql` di
VPS melewati semua blok migrasi. Kali ini tidak merugikan, karena
tabelnya dibuat ulang dari struktur lokal dan datanya sudah termigrasi
sebelum dikirim. Untuk push berikutnya, tanyakan lagi pertanyaan yang
sama.

### 4.2 Di peramban

**Ctrl+F5 dulu** — `branchops.html` di-cache, dan cache basi terlihat
persis seperti deploy yang gagal.

- **Menu TBO** → Ubah → tiga kotak pilihan, Status TBO `Tidak ada TBO`
- **Dashboard 4 (Rekonsiliasi)** → harus ada isinya. Kosong, atau
  semuanya "Tidak dilaporkan cabang", berarti kode dan data tidak
  sepakat soal ejaan — beri tahu saya
- **Unggah satu Excel lalu Batalkan** → membuktikan sequence di VPS

---

## TAHAP 5 — Bersihkan (2 menit)

Berkas yang berpindah antar mesin memuat **NAMA NASABAH ASLI**;
penyamaran `***` terjadi di lapisan API, bukan di berkas.

    del "deploy\keluaran\lokal-branchops.sql"
    ssh root@159.65.139.45 "shred -u /tmp/lokal-branchops.sql"

Periksa sisa disk VPS — push menambah ~30 MB cadangan, dan sejak hari
ini skripnya memangkas sendiri sisanya:

    ssh root@159.65.139.45 "df -h / && ls -lht /root/*.sql"

---

## Kalau harus mundur

- **Basis data lokal** — berkas dari langkah 1.1 di `deploy\cadangan\`,
  atau `deploy\9-pulihkan-lokal.bat`
- **Basis data VPS** — `~/pmo-sebelum-push-*.sql` dan
  `~/bo-vps-sebelum-push-*.sql` di sana, dibuat di langkah 1/7
- **Kode** — `git log --oneline -5` lalu `git revert <commit>`

Yang **tidak** bisa dipulihkan, dan karena itu tidak disentuh oleh apa
pun di runbook ini: `uploads/elibrary` di VPS.

---

## Yang TIDAK termasuk deploy ini

Dua batch pencairan yang menghitung ganda (43, 50, 51 — Rp 206 juta pada
10 dan 12 Agustus, plus Rp 200 juta bertanggal 8 November). Itu
dibereskan lewat tombol **Batalkan** di tab Unggah, bukan lewat deploy,
dan perlu satu keputusan Anda soal batch 43. Rinciannya di CLAUDE.md
bagian "Known data problems".
