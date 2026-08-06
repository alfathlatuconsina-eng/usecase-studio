# Runbook — mendorong Branch Ops ke VPS (159.65.139.45)

Arah **LOKAL → VPS**. Kebalikannya ada di `5-tarik-dari-vps.md`.

Ditulis ulang 7 Agu 2026. Versi sebelumnya memakai `1-export-lokal.bat`
yang hanya mengirim DATA dalam tiga berkas terpisah; itu mengandaikan
struktur kedua sisi sama, dan ternyata tidak. Sekarang struktur ikut
dikirim, dan seluruh proses dijalankan satu skrip.

> **VPS adalah PRODUKSI.** Claude tidak bisa menjalankan apa pun di sini —
> tidak ada rute ke VPS maupun ke PostgreSQL di komputer ini. Semua
> perintah di bawah Anda yang menjalankan.

---

## Cara menjalankan

1. Commit dan push kode lebih dulu — VPS mengambilnya lewat `git pull`:

   ```
   git add -A
   git commit -m "Branch Ops: TBO target + layar edit + tooling VPS"
   git push origin main
   ```

2. Klik dua kali `deploy\2-push-ke-vps.bat`
3. Masukkan sandi `postgres` lokal
4. **Baca perbandingan LOKAL vs VPS yang ditampilkan**, lalu ketik `PUSH`

Aplikasi mati sekitar 30 detik saat pemuatan.

---

## Yang berubah di VPS

| Berubah | Tidak berubah |
|---|---|
| `backend/app.py`, `backend/branchops/` (lewat git) | `branchops_users` — akun login produksi |
| `frontend/branchops.html` (lewat git) | `branchops_audit` — jejak audit produksi |
| Struktur **dan** isi 11 tabel `branchops_*` | dashboard PMO, People, Quality, E-Library |
| | berkas di `uploads/` |

Sebelas tabel yang didorong: `branchops_branches`, `_ref_values`,
`_role_menus`, `_settings`, `_batches`, `_stg`, `_issues`, `_it_break`,
`_pencairan`, `_tbo`, `_rekon`.

**Tidak ada dependensi Python baru.** `requirements.txt` tidak berubah,
jadi tidak perlu `pip install` apa pun di VPS.

---

## Bahaya utama — baca sebelum mengetik PUSH

**Data VPS DIGANTI, bukan digabung.** Kalau di VPS ada unggahan yang belum
pernah ditarik ke komputer ini, unggahan itu hilang.

Langkah 2 skrip menampilkan kedua sisi berdampingan: jumlah baris per
tabel, batch terakhir per jenis, dan berapa unggahan dalam 14 hari
terakhir. Kalau angka VPS lebih besar, atau `unggahan_terakhir` di VPS
lebih baru daripada di lokal:

> **BERHENTI.** Jalankan `deploy\6-tarik-dari-vps.bat` dulu untuk membawa
> data produksi ke lokal, baru dorong balik.

Skrip tidak bisa memutuskan ini untuk Anda — hanya Anda yang tahu apakah
data lokal memang lebih baru, atau justru tertinggal.

---

## Apa yang dikerjakan skrip

| # | Di mana | Langkah | Kalau gagal di sini |
|---|---|---|---|
| 0 | lokal | uji psql lokal + ssh | VPS belum disentuh |
| 1 | lokal | cek pohon kerja git bersih | VPS belum disentuh |
| 2 | keduanya | tampilkan isi lokal dan VPS, minta ketik `PUSH` | VPS belum disentuh |
| 3 | lokal | `pg_dump` struktur + isi 11 tabel | VPS belum disentuh |
| 4 | lokal | `scp` dump + skrip pemuat ke `/tmp` VPS | VPS belum disentuh |
| 5 | VPS | `2-vps-muat.sh` — lihat di bawah | ada cadangan; lihat "Kalau harus mundur" |
| 6 | lokal | tampilkan hasil pemeriksaan | — |

`2-vps-muat.sh` di langkah 5, berurutan:

1. cadangkan seluruh basis data VPS **dan** cadangan per-tabel branchops
2. `git pull --ff-only origin main` di `/opt/pmo`
3. `systemctl stop pmo.service`
4. muat dump dengan `psql -1` — satu transaksi
5. jalankan `backend/branchops/schema.sql`
6. setel ulang sequence
7. `systemctl start pmo.service`, lalu periksa

---

## Kenapa langkahnya begitu

**Struktur ikut dikirim.** Ekspor data-saja mengandaikan kedua sisi punya
kolom yang sama persis. Tidak: `branchops_branches` di VPS masih punya
kolom `region` yang sudah dibuang di lokal, dan `branchops_tbo` /
`branchops_pencairan` di VPS belum punya kolom Agustus 2026. Membawa
struktur menghapus seluruh kelas kegagalan itu sekaligus.

**Pemuatan satu transaksi.** DDL di PostgreSQL ikut transaksional, jadi
`psql -1` membungkus DROP, CREATE dan INSERT bersama. Kegagalan
meninggalkan tabel VPS apa adanya. Versi lama menjalankan pengosongan
terpisah dan pernah meninggalkan tabel KOSONG saat pemuatan gagal.

**Layanan dimatikan dulu.** `ensure_schema()` jalan saat `app.py`
diimpor, dan gunicorn mengimpornya **sekali per worker**. Dengan 3 worker,
migrasi yang sama berjalan tiga kali bersamaan; pemeriksaan
`IF NOT EXISTS` terjadi sebelum kunci tabel didapat, jadi dua worker bisa
sama-sama menyimpulkan kolomnya belum ada dan yang kalah gagal. Karena
kegagalan itu hanya dicetak, hasilnya membingungkan: ada pesan gagal
padahal basis datanya benar.

**`schema.sql` tetap dijalankan** meski struktur sudah benar, karena
kolom milik `branchops_users` (`region_class`, `branch_codes`, CHECK
`ck_bo_users_satu_jatah`) TIDAK ikut dalam dump — tabel itu sengaja tidak
disentuh. Berkasnya idempoten, jadi aman.

**Sequence disetel ulang.** `pg_dump` menulis id secara eksplisit dan itu
tidak menggerakkan sequence. Tanpa langkah ini, unggahan Excel berikutnya
di VPS gagal dengan `duplicate key` sementara datanya terlihat baik-baik
saja — gejala yang sangat membingungkan.

**`--no-owner --no-privileges`.** Peran pemilik tabel di komputer lokal
tidak selalu ada di VPS; tanpa ini pemuatan gagal dengan
`role "..." does not exist`.

---

## Akun pengguna

`branchops_users` tidak pernah ikut. Kalau memang perlu memindahkan akun,
buka `deploy/3-pengguna-pilih-satu.sql` dan pilih SATU pilihan:

- **A — struktur saja.** Akun dibuat lewat layar Pengguna di VPS. Paling aman.
- **B — bawa jatahnya, sandi diganti.** Peran dan jatah cabang ikut, sandi tidak.
- **C — salin apa adanya.** Termasuk hash sandi. Sandi percobaan lokal
  menjadi sandi produksi yang sah.

Ekspor pengguna terpisah:

```
"C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U postgres -d pmo ^
  --data-only --column-inserts -t branchops_users ^
  -f deploy\keluaran\bo-pengguna.sql
```

Muat ke tabel sementara dulu, bukan langsung ke tabel aslinya — caranya
ada di berkas `3-pengguna-pilih-satu.sql`. Berkas itu berisi email dan
hash sandi; hapus dari `/tmp` VPS setelah selesai.

**Setelah master cabang diganti**, pengguna VPS yang `region_class` atau
`branch_codes`-nya tidak ada lagi di master baru tidak akan melihat baris
apa pun. Skrip menampilkan daftarnya di akhir. Perbaiki lewat tab Pengguna.

---

## Kalau harus mundur

Langkah 1 membuat dua cadangan di home direktori VPS. Pakai yang
per-tabel — empat dashboard lain tidak tersentuh:

```bash
ssh root@159.65.139.45
sudo systemctl stop pmo.service
sudo -u postgres psql -d pmo -1 -v ON_ERROR_STOP=1 \
     -f ~/bo-vps-sebelum-push-<stempel>.sql
sudo systemctl start pmo.service
```

Berkas itu dibuat dengan `--clean`, jadi tidak perlu mengosongkan tabel
lebih dulu.

Kode:

```bash
cd /opt/pmo && git reset --hard <commit-sebelumnya>
sudo systemctl restart pmo.service
```

`~/pmo-sebelum-push-<stempel>.sql` adalah dump polos SELURUH basis data.
Memuatnya di atas basis data yang ada hanya menghasilkan banjir
`already exists`; perlu `dropdb`/`createdb` dulu. Jangan dipakai kecuali
yang per-tabel tidak cukup.

---

## Catatan

- **Folder yang benar adalah `/opt/pmo`.** `pmo.service` memakai
  `WorkingDirectory=/opt/pmo/backend`. Di VPS ada klon kedua di
  `/root/usecase-studio` yang TIDAK dipakai layanan mana pun —
  memperbaruinya tidak mengubah apa pun yang terlihat, dan itulah cara
  paling mudah menghabiskan satu jam tanpa hasil.
- **Jangan jalankan `init_db.py` di VPS.** Salinan lama di sana masih
  `from app import (... QualitySurvey ...)`, dan model itu tidak ada —
  berkasnya gagal saat diimpor. Skema Branch Ops tidak memerlukannya.
- Skrip berhenti kalau `git status` di `/opt/pmo` tidak bersih. Suntingan
  darurat yang pernah dilakukan langsung di produksi akan hilang kalau
  ditimpa diam-diam — simpan dulu, baru ulangi.
- Berkas yang berpindah berisi **nama nasabah asli**; penyamaran `***`
  terjadi di API, bukan di basis data. Hapus dari `/tmp` VPS dan dari
  `deploy\keluaran\` setelah selesai.
