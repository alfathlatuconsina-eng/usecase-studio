# Impor modul Branch Ops dari VPS ke komputer lokal

Arah **VPS → LOKAL**. Kebalikan dari `1-export-lokal.bat`.

## Cara menjalankan

1. Tutup backend lokal kalau sedang jalan (`py -3 app.py`).
2. Klik dua kali `deploy\6-tarik-dari-vps.bat`.
3. Masukkan sandi `postgres` lokal saat diminta.
4. Baca angka yang ditampilkan, lalu ketik **`YA`** untuk melanjutkan.

Selesai. Rekonsiliasi ikut terbawa, jadi Dashboard 4 langsung terisi —
tidak perlu menjalankan rekonsiliasi ulang.

## Apa yang diganti

**Sebelas tabel diganti isinya dengan isi VPS:**

`branchops_branches`, `branchops_ref_values`, `branchops_role_menus`,
`branchops_settings`, `branchops_batches`, `branchops_stg`,
`branchops_issues`, `branchops_it_break`, `branchops_pencairan`,
`branchops_tbo`, `branchops_rekon`

**Dua tabel sengaja TIDAK disentuh:**

- `branchops_users` — akun login. Kalau ikut ditimpa, sandi lokal Anda
  berubah jadi sandi VPS dan Anda bisa terkunci di luar dashboard sendiri.
  Cara membawanya tetap ada di `3-pengguna-pilih-satu.sql`.
- `branchops_audit` — jejak audit lokal adalah catatan pekerjaan Anda di
  komputer ini. Menimpanya dengan jejak VPS membuatnya bohong.

`branchops_user_menus` juga dilewati: 0 baris, tidak dibaca kode mana pun
(lihat "Dead tables" di CLAUDE.md).

Keempat dashboard lain (PMO, People Development, Service Quality,
E-Library) tidak disentuh sama sekali.

## Berkas yang dipakai

| Berkas | Jalan di mana |
|---|---|
| `6-tarik-dari-vps.bat` | komputer lokal — menyetir seluruh proses |
| `6-vps-ekspor.sh` | VPS (dikirim otomatis) — ekspor, hanya membaca |
| `6b-selesaikan-lokal.sql` | komputer lokal — setel sequence, periksa |
| `9-pulihkan-lokal.bat` | komputer lokal — memulihkan dari cadangan |

Skrip berhenti sendiri sebelum menyentuh apa pun kalau VPS tidak punya
tabel `branchops_*`, atau tabelnya ada tapi kosong. Sampai Anda mengetik
`YA`, tidak ada satu baris pun di basis data lokal yang berubah.

**Struktur ikut disalin (berubah 6 Agu 2026).** Tabel dibuat ulang persis
seperti di VPS, lalu diisi. Sebelumnya hanya DATA yang disalin, dengan
andaian kedua sisi berbentuk sama — dan itu tidak benar:
`branchops_branches` di VPS masih punya kolom `region` yang sudah dibuang
di lokal, jadi pemuatan gagal di baris pertama. Membawa struktur sekaligus
menghapus seluruh kelas masalah itu.

Sesudah pemuatan, skrip menjalankan `backend/branchops/schema.sql` untuk
menerapkan kembali migrasi khas lokal (`region_class`, `branch_codes`,
CHECK `ck_bo_users_satu_jatah`). Berkas itu seluruhnya dijaga
`IF NOT EXISTS` / `IF EXISTS`, jadi aman dijalankan berulang dan tidak
menyentuh data yang baru masuk. Kolom `region` lama ikut terbawa dari VPS
dan dibiarkan — tidak ada kode yang membacanya. Buang dengan
`hapus-kolom-region-lama.sql` kalau ingin bersih.

**Pengosongan dan pemuatan kini SATU transaksi.** Versi sebelumnya
menjalankan `TRUNCATE` di panggilan `psql` terpisah; ketika pemuatan
gagal, `TRUNCATE` sudah terlanjur commit dan tabel tertinggal kosong.
Sekarang keduanya berdiri atau jatuh bersama — kegagalan meninggalkan
tabel lama utuh, dan tidak ada yang perlu dipulihkan.

---

## Tiga hal yang perlu diketahui

**1. Ini cermin penuh, bukan penggabungan.** `id` di kedua sisi sama-sama
`SERIAL` dan pasti bertabrakan, jadi menggabungkan berarti memberi nomor
ulang setiap baris dan memperbaiki setiap `batch_id` yang menunjuk nomor
lama.

**2. Master cabang diganti, tapi pengguna tidak.** Kalau pengguna lokal
punya `region_class` atau `branch_codes` yang tidak ada di master cabang
VPS, pengguna itu tidak akan melihat baris apa pun. Bukan kerusakan —
penjatahannya menunjuk ke cabang yang sudah tidak ada. **Pemeriksaan 5**
di `6b` menampilkan siapa saja yang kena; perbaiki lewat tab Pengguna.

Hal yang sama berlaku untuk Tipe dan Wilayah yang pernah Anda atur
manual di tab Master Data — nilainya ikut diganti nilai VPS.

**3. Berkas yang berpindah berisi nama nasabah asli.** Penyamaran `***`
terjadi di API, di `masking.py`, bukan di basis data. `vps-branchops.sql`
adalah teks biasa berisi nama nasabah, nomor rekening dan nominal — di
`/tmp` VPS, lewat `scp`, dan di `deploy\masuk\`. Hapus setelah selesai:

```
del deploy\masuk\vps-branchops.sql
ssh root@159.65.139.45 "shred -u /tmp/vps-branchops.sql /tmp/6-vps-ekspor.sh"
```

`.gitignore` sudah mengabaikan `deploy/masuk/` dan `deploy/cadangan/`.
Jangan longgarkan aturan itu.

---

## Sesudahnya — periksa

`6b` menampilkan enam blok. Yang wajib dilihat:

- **3 — baris yatim.** Harus `0` semua. Kalau tidak, dump tidak lengkap.
- **5 — jatah pengguna.** Idealnya kosong. Nama yang muncul tidak akan
  melihat baris apa pun sampai jatahnya diperbaiki.
- **6 — sequence.** Kolom `sisa` harus `>= 0`. Kalau negatif, unggahan
  Excel berikutnya gagal dengan `duplicate key`.
- **4 — cabang tanpa Wilayah.** Boleh ada; cabang itu hanya terlihat oleh
  admin.

Lalu lewat layar, di `http://localhost:8000/branchops-login.html`:

- [ ] Dashboard 1–4 terisi, rentang tanggalnya cocok dengan VPS
- [ ] Nama nasabah tetap `***`, termasuk di ekspor CSV
- [ ] **Unggah satu berkas Excel percobaan** — ini satu-satunya uji yang
      benar-benar membuktikan sequence sudah betul
- [ ] Akun non-admin hanya melihat cabang jatahnya, juga di Dashboard 4
- [ ] Dashboard lain (PMO, People, Quality, E-Library) masih normal

---

## Kalau macet

**Skrip berhenti setelah menampilkan angka, tidak terjadi apa-apa**
Itu prompt `YA`. Harus huruf besar `YA`, lalu Enter. Apa pun selain itu
dianggap batal.

**`GAGAL menghubungi PostgreSQL lokal`**
Sandi salah, layanan PostgreSQL mati, atau basis data `pmo` tidak ada.

**`tidak bisa masuk ke root@159.65.139.45`**
Uji sendiri: `ssh root@159.65.139.45 "echo ok"`.

**`column "..." of relation "..." does not exist`**
Seharusnya tidak muncul lagi sejak struktur ikut disalin. Kalau tetap
muncul, berkas yang dimuat adalah ekspor data-saja versi lama — hapus
`deploy\masuk\vps-branchops.sql` dan jalankan ulang skripnya. Data lokal
Anda aman: pemuatan satu transaksi, jadi kegagalan tidak mengubah apa pun.

**`cannot drop table ... because other objects depend on it`**
Ada tabel di luar kesebelas yang menunjuk ke salah satunya lewat foreign
key — kandidat paling mungkin `branchops_user_menus`, tabel mati yang
tidak dibaca kode mana pun. Periksa dulu, jangan langsung dibuang:

```
psql -U postgres -d pmo -c "\d branchops_user_menus"
```

Sekali lagi, data lokal tetap utuh karena seluruhnya satu transaksi.

**`duplicate key value violates unique constraint`**
Sequence belum disetel ulang. Jalankan `6b-selesaikan-lokal.sql`.

**`role "..." does not exist`**
Seharusnya sudah ditangani `--no-owner --no-privileges` di skrip ekspor.
Kalau muncul, berkas ekspornya dibuat versi lama — ulangi dari awal.

---

## Kalau harus mundur

Cara termudah: klik dua kali **`deploy\9-pulihkan-lokal.bat`**, ketik
`PULIHKAN`. Skrip itu memilih cadangan terbaru sendiri, memulihkan dalam
satu transaksi, lalu menyetel ulang sequence.

Dengan tangan, kalau lebih suka:

```
cd "D:\Claude Projects\UseCase-Studio.XYZ\Dashboard Development"
set PSQL="C:\Program Files\PostgreSQL\18\bin\psql.exe"

%PSQL% -U postgres -d pmo -1 -v ON_ERROR_STOP=1 -f "deploy\cadangan\bo-lokal-sebelum-impor-<stempel>.sql"
%PSQL% -U postgres -d pmo -f "deploy\6b-selesaikan-lokal.sql"
```

Perintah kedua bukan pelengkap — tanpa menyetel ulang sequence, unggahan
Excel berikutnya gagal dengan `duplicate key`.

Cadangan `pmo-sebelum-impor-*.sql` adalah dump polos SELURUH basis data
berisi `CREATE TABLE` untuk kelima dashboard. Memuatnya di atas basis data
yang sudah ada hanya menghasilkan banjir `already exists`; harus
`dropdb`/`createdb` dulu. Basis data lokal Anda sudah pernah hilang sekali
karena ini — jangan pakai yang ini kecuali yang per-tabel tidak cukup.

---

## Catatan

- **`pg_dump --data-only` tidak membawa sequence.** Lubang yang sama ada
  di `1-export-lokal.bat` untuk arah sebaliknya: setelah memuat ke VPS,
  sequence di sana juga tidak pernah disetel ulang. Kalau nanti Anda
  mendorong data ke VPS, jalankan bagian `setval` dari
  `6b-selesaikan-lokal.sql` di sana juga.
- **Batch berstatus `draft` dan `dibatalkan` ikut terbawa.** Membuang
  sebagiannya akan meninggalkan baris fakta tanpa induk. Kalau tidak
  diinginkan, hapus di VPS **sebelum** menjalankan skrip.
- **Jangan jalankan `init_db.py`** untuk urusan ini. Skema Branch Ops
  diurus `ensure_schema()` saat aplikasi start.
