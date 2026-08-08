# Sebelum menjalankan 2-push-ke-vps.bat — daftar periksa

Ditulis 8 Agu 2026. Dibaca SEBELUM `RUNBOOK-branchops-ke-vps.md`, yang
langkah pertamanya mengandaikan kode sudah di-commit. Saat ini belum.

> **VPS adalah PRODUKSI.** Claude tidak bisa menjalankan apa pun di sini —
> tidak ada rute ke VPS maupun ke PostgreSQL di komputer ini. Seluruh
> perintah di bawah Anda yang menjalankan.

Buang berkas ini kalau kedua penghalang di bawah sudah beres dan pushnya
sudah berhasil. Isinya menggambarkan satu keadaan tertentu, bukan aturan
tetap.

---

## Dua penghalang, dan urutannya tidak boleh dibalik

`2-push-ke-vps.bat` mengambil kode di VPS lewat `git pull`. Artinya yang
sampai ke produksi adalah **isi git**, bukan isi folder kerja ini.

**Penghalang 1 — kode lokal belum di-commit.**
HEAD masih `1b3842a`. Tiga belas berkas terlacak berubah dan belum
di-commit. Push sekarang mengirim `claude.md` yang menjelaskan aturan
12–18 dan TIDAK mengirim satu baris pun kodenya. Dua di antaranya
menutup lubang sungguhan:

- aturan 12 — `/summary` berhenti mengirim baris d2/d3 ke peran yang
  hak menunya sudah dicabut
- aturan 18 — editor tidak bisa lagi mengunggah data cabang lain

**Penghalang 2 — enam berkas terlacak disunting langsung di VPS.**
`backend/app.py`, `backend/init_db.py`, `backend/requirements.txt`,
`frontend/landing.html`, `frontend/people.html`, `frontend/quality.html`.
`git pull` menimpanya. `app.py` memuat kelima dashboard, jadi perbaikan
yang hanya ada di produksi untuk PMO / People / Quality / E-Library ikut
hilang.

Urutan yang tidak membuang pekerjaan siapa pun:
**selesaikan 2 → commit lokal (1) → uji lokal → baru push.**

---

## A. Selesaikan suntingan yang hanya ada di VPS

    deploy\1-lihat-suntingan-vps.bat

Menyalin diff dan versi VPS keenam berkas itu ke
`deploy\masuk\suntingan-vps-<stempel>\`. Tidak mengubah apa pun.

Lalu putuskan per berkas. Kalau sebuah perbaikan hanya ada di produksi,
pindahkan ke lokal, commit, baru push — kalau tidak, `git pull`
menghapusnya.

> `init_db.py` di VPS adalah salinan RUSAK: ia mengimpor model
> `QualitySurvey` yang tidak ada, jadi berkas itu gagal saat diimpor.
> Jangan bawa yang itu kembali ke lokal.

---

## B. Commit pekerjaan lokal

Periksa dulu apa yang akan masuk:

    git status --untracked-files=no
    git diff --stat

Dua commit sudah cukup, dan pemisahannya bersih karena berkasnya tidak
bertumpang tindih.

**B1 — perkakas deploy** (dari sesi sebelumnya, bukan bagian aturan 12–18):

    git add deploy/2-push-ke-vps.bat deploy/2-vps-muat.sh
    git commit -m "Deploy: penjaga git pakai --untracked-files=no, cek foreign key sebelum DROP"

**B2 — Branch Ops, aturan 12 sampai 18:**

    git add backend/app.py backend/branchops/ frontend/branchops.html frontend/branchops-login.html claude.md
    git commit -m "Branch Ops: hak menu di Beranda, Dashboard 2 dirombak, unggah dari dashboard, keluar otomatis, jejak login, jatah pada unggahan"

Kenapa aturan 12–18 tidak dipecah satu commit per aturan: perubahannya
berselang-seling di dalam `analytics.py` dan `branchops.html`. Memisahkan
berarti `git add -p` memilah puluhan hunk di dua berkas besar, dan commit
setengah jadi yang lolos dari situ lebih berbahaya daripada satu commit
yang agak besar tapi utuh.

    git push origin main

---

## C. Jalankan sekali di lokal sebelum menyentuh produksi

Belum ada satu pun pekerjaan Agustus 2026 yang pernah berjalan melawan
basis data sungguhan. Aturan 16, 17 dan 18 diuji dengan jam, request dan
basis data tiruan — itu bukan berarti pernah jalan.

1. **Restart backend.** `schema.sql` sekarang memuat tiga
   `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` dan satu baris pengaturan
   baru. Semuanya idempoten, tapi tidak berlaku sampai aplikasi
   dijalankan ulang — dan sampai itu, tab Audit dan tab Unggah akan galat
   karena kolomnya belum ada.

       cd backend
       py -3 app.py

2. **Unggah** `contoh\Template-02-Pencairan-Deposito.xlsx` sebagai admin.
   Menguji kolom baru, parser, dan urutan sequence sekaligus.

3. **Unggah berkas yang sama sebagai editor** yang jatahnya satu cabang.
   Harus DITOLAK 403 dengan daftar kode cabang di luar jatah, dan
   **tidak boleh** meninggalkan draft di tab Unggah (aturan 18).

4. **Tab Audit** — harus ada baris `masuk` untuk login Anda, dengan
   kolom Alamat IP dan Perangkat terisi.

5. **Diamkan layar** selama `idle_timeout_menit` (bawaannya 1 menit).
   Harus terlempar ke halaman masuk dengan keterangan menganggur.
   Sebaliknya: buka kotak pilih berkas dan diamkan lebih lama dari itu —
   TIDAK boleh keluar (aturan 16).

Kalau salah satu gagal, jangan push. Perbaiki lalu commit lagi.

---

## D. Push, lalu restart VPS

    deploy\2-push-ke-vps.bat

Baca perbandingan LOKAL vs VPS yang ditampilkan, baru ketik `PUSH`.

Sesudahnya, **restart layanan di VPS** dengan alasan yang sama seperti
langkah C1: `ensure_schema()` hanya berjalan saat aplikasi start.

Lalu periksa di produksi:

- tab Unggah punya kolom **Lingkup** (kode cabang, atau "se-bank")
- tab Audit punya kolom **Alamat IP** dan **Perangkat**

Kolom IP kemungkinan besar berisi `127.0.0.1` untuk semua orang. Itu
bukan bug di aplikasi — blok nginx di catatan pemasangan hanya
meneruskan `Host`. Perbaikannya di nginx:

    proxy_set_header X-Real-IP        $remote_addr;
    proxy_set_header X-Forwarded-For  $proxy_add_x_forwarded_for;

Catatan: mempercayai `X-Forwarded-For` hanya aman SELAMA ada proxy yang
menimpanya. Kalau aplikasi suatu saat diakses langsung tanpa nginx,
header itu dikendalikan pengirim dan tidak boleh dipercaya.

---

## Yang TIDAK dibereskan push ini

Masih ada di data, tidak berhubungan dengan kode (lihat "Known data
problems" di CLAUDE.md):

- batch 16 — baris Juni yang tampak sintetis
- batch 21 — `tgl_input` salah tahun
- batch 27 — sudah dibatalkan
