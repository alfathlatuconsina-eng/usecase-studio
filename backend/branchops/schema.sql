-- =====================================================================
-- Branch Operations and Transactions Monitoring
-- Skema PostgreSQL  |  usecase-scenario.xyz
--
-- Prinsip:
--   1. Data mentah tidak pernah diubah  -> tabel branchops_stg menyimpan apa adanya
--   2. Pembersihan menghasilkan baris baru di fact_*, bukan menimpa staging
--   3. Setiap perubahan tercatat di audit_log
-- =====================================================================

BEGIN;

-- Jejak audit modul Branch Operations (terpisah dari audit_log PMO)
CREATE TABLE IF NOT EXISTS branchops_audit (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_email  VARCHAR(255),
    action      VARCHAR(64) NOT NULL,
    entity      VARCHAR(64),
    entity_id   VARCHAR(64),
    detail      JSONB
);
CREATE INDEX IF NOT EXISTS ix_bo_audit_ts ON branchops_audit (ts DESC);

-- Asal permintaan (Agustus 2026). Diisi db.audit() untuk SETIAP aksi yang
-- tercatat, bukan hanya login, karena satu-satunya tempat yang menulis ke
-- tabel ini adalah fungsi itu.
--
--   ip         alamat IP pemanggil
--   perangkat  header User-Agent MENTAH, apa adanya
--
-- User-Agent sengaja disimpan UTUH dan tidak diringkas sebelum masuk, sesuai
-- prinsip 1 di kepala berkas ini: data mentah tidak pernah diubah. Layar
-- Audit-lah yang meringkasnya jadi "Chrome di Windows"; kalau ringkasan itu
-- suatu saat salah menebak, teks aslinya masih ada untuk diperiksa. Menyimpan
-- hasil ringkasan saja berarti membuang bukti demi tampilan.
--
-- Keduanya SELF-REPORTED dan bisa dipalsukan. Berguna untuk menjawab
-- "kira-kira dari mana ini dikerjakan", bukan sebagai bukti identitas.
ALTER TABLE branchops_audit ADD COLUMN IF NOT EXISTS ip        VARCHAR(64);
ALTER TABLE branchops_audit ADD COLUMN IF NOT EXISTS perangkat TEXT;

-- Untuk menyaring satu jenis aksi (mis. hanya 'masuk') tanpa memindai
-- seluruh tabel setelah jejaknya menumpuk.
CREATE INDEX IF NOT EXISTS ix_bo_audit_action ON branchops_audit (action, ts DESC);



-- ------------------------------------------------------------------ --
-- MASTER
-- ------------------------------------------------------------------ --
CREATE TABLE IF NOT EXISTS branchops_branches (
    branch_code VARCHAR(5) PRIMARY KEY,          -- selalu 5 digit, zero-padded
    branch_name VARCHAR(120) NOT NULL,
    branch_type VARCHAR(10)  NOT NULL DEFAULT 'Lainnya'
                CHECK (branch_type IN ('KC', 'KCP', 'Pusat', 'Lainnya')),
    -- Kolom 'region' lama DIBUANG Agustus 2026. Isinya ditebak dari kode
    -- cabang dan selalu salah ("Kantor Pusat" untuk semua), serta tidak
    -- pernah ditampilkan. Penggantinya region_class di bawah.
    core_alias  VARCHAR(120),                    -- nama versi core banking
    is_active   BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS ix_bo_branch_alias ON branchops_branches (core_alias);

CREATE TABLE IF NOT EXISTS branchops_ref_values (
    id       SERIAL PRIMARY KEY,
    kategori VARCHAR(40) NOT NULL,
    nilai    VARCHAR(80) NOT NULL,
    urutan   SMALLINT NOT NULL DEFAULT 0,
    aktif    BOOLEAN  NOT NULL DEFAULT TRUE,
    UNIQUE (kategori, nilai)
);

-- ------------------------------------------------------------------ --
-- BATCH UPLOAD
-- ------------------------------------------------------------------ --
CREATE TABLE IF NOT EXISTS branchops_batches (
    id            SERIAL PRIMARY KEY,
    jenis         VARCHAR(24) NOT NULL
                  CHECK (jenis IN ('it_break', 'pencairan', 'tbo')),
    nama_file     VARCHAR(255) NOT NULL,
    ukuran_byte   BIGINT,
    sha256        VARCHAR(64),                   -- deteksi file sama diunggah dua kali
    status        VARCHAR(16) NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft', 'committed', 'dibatalkan')),
    baris_total   INTEGER NOT NULL DEFAULT 0,
    baris_valid   INTEGER NOT NULL DEFAULT 0,
    baris_ditolak INTEGER NOT NULL DEFAULT 0,
    baris_warning INTEGER NOT NULL DEFAULT 0,
    periode_awal  DATE,
    periode_akhir DATE,
    uploaded_by   VARCHAR(255),
    uploaded_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    committed_by  VARCHAR(255),
    committed_at  TIMESTAMPTZ,
    catatan       TEXT
);
CREATE INDEX IF NOT EXISTS ix_bo_batch_status ON branchops_batches (jenis, status);

-- Lingkup cabang sebuah batch (Agustus 2026).
--
--   NULL          batch se-bank: isinya lebih dari satu cabang, atau nol
--                 cabang. Ini yang dihasilkan unggahan admin.
--   '00123'       batch berisi TEPAT SATU cabang. Ini yang dihasilkan
--                 unggahan editor yang jatahnya satu cabang.
--
-- KENAPA ADA: commit_batch() membatalkan batch lama yang jenis DAN
-- periodenya sama. Aturan itu lahir ketika satu berkas mewakili seluruh
-- bank, jadi "periode sama" berarti "berkas pengganti". Sejak editor boleh
-- mengunggah data cabangnya sendiri, anggapan itu runtuh: cabang A dan
-- cabang B sama-sama melaporkan Senin-Jumat, jenis sama, periode sama -
-- dan komit milik B akan MEMBATALKAN batch milik A. Barisnya lenyap dari
-- seluruh dashboard tanpa satu pun galat.
--
-- Dengan kolom ini, pembatalan hanya mengenai batch dengan lingkup yang
-- SAMA. Unggahan se-bank (NULL) tetap saling menggantikan seperti dulu,
-- jadi perilaku lama tidak berubah.
ALTER TABLE branchops_batches ADD COLUMN IF NOT EXISTS branch_code VARCHAR(5);

CREATE TABLE IF NOT EXISTS branchops_issues (
    id         BIGSERIAL PRIMARY KEY,
    batch_id   INTEGER NOT NULL REFERENCES branchops_batches(id) ON DELETE CASCADE,
    baris_no   INTEGER,
    severity   VARCHAR(10) NOT NULL CHECK (severity IN ('error', 'warning')),
    kode       VARCHAR(60) NOT NULL,
    pesan      TEXT NOT NULL,
    kolom      VARCHAR(60),
    nilai      TEXT,
    branch_code VARCHAR(5)          -- agar bisa dibedakan: tidak mengirim vs kiriman ditolak
);
CREATE INDEX IF NOT EXISTS ix_bo_issue_batch ON branchops_issues (batch_id, severity);
CREATE INDEX IF NOT EXISTS ix_bo_issue_branch ON branchops_issues (branch_code);

-- ------------------------------------------------------------------ --
-- STAGING (apa adanya)
-- ------------------------------------------------------------------ --
CREATE TABLE IF NOT EXISTS branchops_stg (
    id        BIGSERIAL PRIMARY KEY,
    batch_id  INTEGER NOT NULL REFERENCES branchops_batches(id) ON DELETE CASCADE,
    baris_no  INTEGER NOT NULL,
    payload   JSONB   NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_bo_stg_batch ON branchops_stg (batch_id);

-- ------------------------------------------------------------------ --
-- FAKTA 1 - Break deposito dari IT Group
-- ------------------------------------------------------------------ --
CREATE TABLE IF NOT EXISTS branchops_it_break (
    id                BIGSERIAL PRIMARY KEY,
    batch_id          INTEGER NOT NULL REFERENCES branchops_batches(id) ON DELETE CASCADE,
    baris_no          INTEGER,
    branch_code       VARCHAR(5) REFERENCES branchops_branches(branch_code),
    cabang_core       VARCHAR(120),
    saldo             NUMERIC(20,2),
    tgl_penempatan    DATE,
    tgl_jatuh_tempo   DATE,
    tgl_break         DATE NOT NULL,
    waktu_awal        TIME,
    waktu_akhir       TIME,
    durasi_detik      INTEGER,
    rek_pendebetan    VARCHAR(32),
    rek_norm          VARCHAR(32),               -- digit saja -> kunci rekonsiliasi
    nama_pemilik      VARCHAR(120),
    nama_terpotong    BOOLEAN NOT NULL DEFAULT FALSE,
    nominal           NUMERIC(20,2) NOT NULL,
    penalti           NUMERIC(20,2) NOT NULL DEFAULT 0,
    mata_uang         VARCHAR(8) DEFAULT 'IDR',
    rate              NUMERIC(8,5),
    rek_pencairan     VARCHAR(32),
    nama_pencairan    VARCHAR(120),
    via_perantara     BOOLEAN NOT NULL DEFAULT FALSE,
    cs_id             VARCHAR(32),
    cs_nama           VARCHAR(120),
    flm1_nama         VARCHAR(120),
    teller_id         VARCHAR(32),
    teller_nama       VARCHAR(120),
    flm2_id           VARCHAR(32),
    flm2_nama         VARCHAR(120),
    sisa_hari         INTEGER,
    umur_hari         INTEGER,
    break_sejati      BOOLEAN NOT NULL DEFAULT FALSE,
    luar_jam          BOOLEAN NOT NULL DEFAULT FALSE,
    flags             TEXT[] NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_bo_it_tgl    ON branchops_it_break (tgl_break);
CREATE INDEX IF NOT EXISTS ix_bo_it_branch ON branchops_it_break (branch_code);
CREATE INDEX IF NOT EXISTS ix_bo_it_rek    ON branchops_it_break (rek_norm);
CREATE INDEX IF NOT EXISTS ix_bo_it_batch  ON branchops_it_break (batch_id);

-- ------------------------------------------------------------------ --
-- FAKTA 2 - Pencairan deposito dari cabang
-- ------------------------------------------------------------------ --
CREATE TABLE IF NOT EXISTS branchops_pencairan (
    id                BIGSERIAL PRIMARY KEY,
    batch_id          INTEGER NOT NULL REFERENCES branchops_batches(id) ON DELETE CASCADE,
    baris_no          INTEGER,
    branch_code       VARCHAR(5) REFERENCES branchops_branches(branch_code),
    tgl_input         DATE NOT NULL,
    no_deposito       VARCHAR(40),
    no_deposito_norm  VARCHAR(32),
    nama_pemilik      VARCHAR(160),
    tgl_penempatan    DATE,
    tgl_bilyet        DATE,
    tgl_pencairan     DATE,
    tenor_hari        INTEGER,
    nominal           NUMERIC(20,2),
    jenis_pencairan   VARCHAR(60),
    jenis_penarikan   VARCHAR(60),
    data_tbo          TEXT,
    -- klasifikasi turunan, ditandai eksplisit sebagai hasil olahan
    arus_dana         VARCHAR(24) NOT NULL DEFAULT 'Arus Keluar'
                      CHECK (arus_dana IN ('Arus Keluar','Rollover / DOC','Penempatan Kembali')),
    arus_keyakinan    VARCHAR(10) NOT NULL DEFAULT 'Sedang',
    arus_manual       BOOLEAN NOT NULL DEFAULT FALSE,
    nip_maker         VARCHAR(20),
    nip_checker       VARCHAR(20),
    nip_approver      VARCHAR(20),
    checker_eq_approver BOOLEAN NOT NULL DEFAULT FALSE,
    catatan           TEXT,
    is_duplikat       BOOLEAN NOT NULL DEFAULT FALSE,
    dup_dikecualikan  BOOLEAN NOT NULL DEFAULT FALSE,
    skor_lengkap      NUMERIC(5,3) NOT NULL DEFAULT 1,
    flags             TEXT[] NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_bo_pc_tgl    ON branchops_pencairan (tgl_input);
CREATE INDEX IF NOT EXISTS ix_bo_pc_branch ON branchops_pencairan (branch_code);
CREATE INDEX IF NOT EXISTS ix_bo_pc_norm   ON branchops_pencairan (no_deposito_norm);
CREATE INDEX IF NOT EXISTS ix_bo_pc_batch  ON branchops_pencairan (batch_id);

-- ------------------------------------------------------------------ --
-- FAKTA 3 - Pembukaan rekening dengan TBO
--   Status TBO dilacak DI SINI, bukan di Excel: cabang tidak punya
--   kolomnya, dan yang tahu dokumen sudah lengkap memang kantor pusat.
-- ------------------------------------------------------------------ --
CREATE TABLE IF NOT EXISTS branchops_tbo (
    id                BIGSERIAL PRIMARY KEY,
    batch_id          INTEGER NOT NULL REFERENCES branchops_batches(id) ON DELETE CASCADE,
    baris_no          INTEGER,
    branch_code       VARCHAR(5) REFERENCES branchops_branches(branch_code),
    tgl_input         DATE NOT NULL,
    no_cif            VARCHAR(60),
    cif_gabungan      BOOLEAN NOT NULL DEFAULT FALSE,
    no_rekening       VARCHAR(40),
    no_rekening_norm  VARCHAR(32),
    nama_pemilik      VARCHAR(160),
    tgl_penempatan    DATE,
    tgl_jatuh_tempo   DATE,
    nominal           NUMERIC(20,2),
    mata_uang         VARCHAR(8) NOT NULL DEFAULT 'IDR',
    jenis_rekening    VARCHAR(60),
    jenis_setoran     VARCHAR(60),
    jenis_produk      VARCHAR(60),
    tipe_pembukaan    VARCHAR(30) NOT NULL DEFAULT 'Baru'
                      CHECK (tipe_pembukaan IN ('Baru','Penempatan Kembali')),
    dokumen_tbo       TEXT,
    ada_tbo           BOOLEAN NOT NULL DEFAULT TRUE,
    -- pelacakan TBO, diisi lewat aplikasi bukan dari Excel
    status_tbo        VARCHAR(16) NOT NULL DEFAULT 'Outstanding'
                      -- 'Tidak ada TBO' menggantikan 'Dikecualikan'
                      -- 16 Agu 2026 (aturan 27). Baris lama dipindahkan
                      -- oleh blok 'status_tbo_baku_migrasi' di bawah,
                      -- yang juga membongkar dan memasang ulang CHECK
                      -- ini - definisi di sini hanya berlaku untuk basis
                      -- data yang masih kosong.
                      CHECK (status_tbo IN ('Outstanding','Lengkap','Tidak ada TBO')),
    tgl_tbo_lengkap   DATE,
    tbo_updated_by    VARCHAR(255),
    tbo_updated_at    TIMESTAMPTZ,
    nip_maker         VARCHAR(20),
    nip_checker       VARCHAR(20),
    nip_approver      VARCHAR(20),
    keterangan        TEXT,
    flags             TEXT[] NOT NULL DEFAULT '{}',
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_bo_tbo_tgl    ON branchops_tbo (tgl_input);
CREATE INDEX IF NOT EXISTS ix_bo_tbo_branch ON branchops_tbo (branch_code);
CREATE INDEX IF NOT EXISTS ix_bo_tbo_status ON branchops_tbo (status_tbo);
CREATE INDEX IF NOT EXISTS ix_bo_tbo_batch  ON branchops_tbo (batch_id);

-- ------------------------------------------------------------------ --
-- REKONSILIASI
-- ------------------------------------------------------------------ --
CREATE TABLE IF NOT EXISTS branchops_rekon (
    id             BIGSERIAL PRIMARY KEY,
    rek_norm       VARCHAR(32) NOT NULL,
    it_id          BIGINT REFERENCES branchops_it_break(id)  ON DELETE CASCADE,
    pencairan_id   BIGINT REFERENCES branchops_pencairan(id) ON DELETE CASCADE,
    branch_code    VARCHAR(5) REFERENCES branchops_branches(branch_code),
    tgl_acuan      DATE,
    nominal_it     NUMERIC(20,2),
    nominal_cabang NUMERIC(20,2),
    selisih        NUMERIC(20,2),
    status         VARCHAR(32) NOT NULL
                   CHECK (status IN ('Cocok','Selisih material',
                                     'Tidak dilaporkan cabang','Tidak ada di data IT')),
    tindak_lanjut  VARCHAR(24) NOT NULL DEFAULT 'Belum ditinjau'
                   CHECK (tindak_lanjut IN ('Belum ditinjau','Sedang ditelusuri',
                                            'Selesai - wajar','Selesai - dikoreksi')),
    catatan_tl     TEXT,
    updated_by     VARCHAR(255),
    updated_at     TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_bo_rekon_key
  ON branchops_rekon (rek_norm, COALESCE(it_id,-1), COALESCE(pencairan_id,-1));
CREATE INDEX IF NOT EXISTS ix_bo_rec_status ON branchops_rekon (status, tindak_lanjut);

-- ------------------------------------------------------------------ --
-- HAK MENU PER PERAN
--   Menentukan menu/tab mana yang boleh dilihat DAN diakses tiap PERAN
--   (admin / editor / viewer), bukan per pengguna. Jadi seluruh pengguna
--   berperan viewer punya hak menu yang sama.
--   Ditegakkan di BACKEND (privileges.py), bukan sekadar disembunyikan di JS.
--
--   Tidak ada baris untuk sebuah peran = belum diatur = peran itu dapat
--   semua menu yang memang masuk akal untuknya (privileges.menus_for_role).
--
--   Baris untuk 'admin' boleh saja ada, tapi diabaikan: admin selalu
--   mendapat semua menu, supaya admin terakhir tidak mengunci dirinya.
-- ------------------------------------------------------------------ --
CREATE TABLE IF NOT EXISTS branchops_role_menus (
    role       VARCHAR(20) PRIMARY KEY,
    menus      TEXT[]  NOT NULL DEFAULT '{}',
    updated_by VARCHAR(255),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------ --
-- PENGATURAN
-- ------------------------------------------------------------------ --
CREATE TABLE IF NOT EXISTS branchops_settings (
    kunci      VARCHAR(60) PRIMARY KEY,
    nilai      TEXT NOT NULL,
    deskripsi  TEXT,
    updated_by VARCHAR(255),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO branchops_settings (kunci, nilai, deskripsi) VALUES
 ('rekon_toleransi_rp','1000000',
  'Selisih nominal (Rp) yang masih dianggap wajar saat rekonsiliasi IT vs cabang. Selisih di bawah nilai ini umumnya berasal dari bunga berjalan dan penalti. BELUM ditetapkan resmi - harap dikonfirmasi.'),
 ('rollover_tenor_hari','1',
  'Tenor maksimum (hari) yang diklasifikasikan sebagai Rollover / Deposito On Call.'),
 ('jam_operasional_mulai','8','Jam mulai operasional untuk penandaan transaksi di luar jam.'),
 ('jam_operasional_selesai','16','Jam selesai operasional untuk penandaan transaksi di luar jam.')
ON CONFLICT (kunci) DO NOTHING;

-- Dua pengaturan di bawah menentukan seberapa ketat berkas cabang diperiksa.
-- Nilai awal sengaja longgar karena data cabang diinput manual tanpa validasi.
INSERT INTO branchops_settings (kunci, nilai, deskripsi) VALUES
 ('validasi_nip','0',
  'Periksa kelengkapan dan format NIP maker/checker/approver. 1 = periksa, 0 = abaikan. Nilai NIP tetap tersimpan apa adanya; yang dimatikan hanya penandaannya.'),
 ('validasi_duplikat','abaikan',
  'Perlakuan baris kembar (nomor deposito + nominal + tanggal pencairan sama). abaikan = semua baris masuk dan dihitung; peringatan = masuk tapi ditandai dan dikecualikan dari agregat; tolak = baris kembar tidak masuk.')
ON CONFLICT (kunci) DO NOTHING;

-- Keluar otomatis saat layar dibiarkan menganggur (Agustus 2026).
--
-- Nilainya MENIT, dan 0 berarti fitur ini dimatikan.
--
-- Yang perlu diketahui sebelum menaikkan harapan atas pengaturan ini:
-- ini menghapus token dari peramban, jadi gunanya menutup layar yang
-- ditinggal terbuka. Ia BUKAN pembatalan sesi di server. Token JWT tetap
-- sah sampai kedaluwarsanya sendiri (JWT_HOURS = 12 jam di app.py), jadi
-- salinan token yang sudah terlanjur diambil orang lain tetap berlaku.
-- Memperpendek itu berarti mengubah JWT_HOURS, dan JWT_HOURS dipakai
-- KELIMA dashboard - jangan diubah diam-diam dari sini.
INSERT INTO branchops_settings (kunci, nilai, deskripsi) VALUES
 ('idle_timeout_menit','1',
  'Keluar otomatis setelah layar dibiarkan menganggur selama sekian MENIT. 0 = dimatikan. Hitungan berhenti sementara selama berkas sedang diunggah dan selama kotak pilih berkas terbuka, supaya orang tidak terlempar keluar di tengah unggahan. Catatan: ini menghapus token di peramban, bukan membatalkan sesi di server.')
ON CONFLICT (kunci) DO NOTHING;

INSERT INTO branchops_ref_values (kategori, nilai, urutan) VALUES
 ('jenis_pencairan','Sesuai Jatuh Tempo',1),
 ('jenis_pencairan','Dipercepat (Break)',2),
 ('jenis_penarikan','Tunai',1),
 ('jenis_penarikan','Transfer',2),
 ('jenis_penarikan','Pemindah-bukuan',3),
 ('jenis_rekening','Perorangan',1),
 -- Ejaan diubah 16 Agu 2026, keputusan pemilik. Baris lama dihapus dan
 -- 84 baris data ikut dipindahkan oleh blok 'jenis_rekening_baku_migrasi'
 -- di bawah. Benih ini hanya berlaku untuk basis data yang masih kosong.
 ('jenis_rekening','Non Perorangan (Perusahaan)',2),
 -- jenis_setoran (branchops_tbo) belum pernah punya benih sampai 16 Agu
 -- 2026. Daftarnya kini sama persis dengan jenis_penarikan di atas -
 -- lihat catatan pembalikan keputusan di blok migrasi ejaan.
 ('jenis_setoran','Tunai',1),
 ('jenis_setoran','Transfer',2),
 ('jenis_setoran','Pemindah-bukuan',3),
 -- LIMA nilai, dan itu memang lebih banyak daripada TIGA yang ditawarkan
 -- kotak pilihan di layar Ubah TBO. Bukan kelalaian: jenis_produk tidak
 -- pernah diketik orang, melainkan DITURUNKAN parse_tbo dari kolom
 -- Keterangan lewat _PRODUK di ingest.py, dan _PRODUK masih bisa
 -- menghasilkan kelimanya. Daftar layar dipersempit atas keputusan
 -- pemilik 16 Agu 2026; daftar di sini tetap menggambarkan apa yang
 -- betul-betul bisa masuk. Lihat aturan 26 di CLAUDE.md.
 ('jenis_produk','Deposito',1),
 ('jenis_produk','Deposito On Call',2),
 ('jenis_produk','Giro',3),
 ('jenis_produk','Tabungan',4),
 ('jenis_produk','Bundling',5),
 ('mata_uang','IDR',1),('mata_uang','USD',2),('mata_uang','EUR',3),('mata_uang','SGD',4)
ON CONFLICT (kategori, nilai) DO NOTHING;


-- =====================================================================
--  MIGRASI Agustus 2026 - Region Class (jatah wilayah per pengguna)
-- =====================================================================
--  Region Class menentukan cabang mana yang boleh DILIHAT seorang
--  pengguna. Nilainya diisi dari berkas Excel master cabang.
--
--  Kolom 'region' yang lama TIDAK diubah. Kolom itu tetap terisi
--  otomatis dari digit pertama kode cabang dan masih dipakai tampilan.
--  region_class adalah kolom terpisah yang diisi manual.
--
--  Blok di bawah aman dijalankan berulang - ensure_schema() memanggil
--  berkas ini setiap aplikasi start.
-- ---------------------------------------------------------------------

ALTER TABLE branchops_branches
  ADD COLUMN IF NOT EXISTS region_class VARCHAR(60);

CREATE INDEX IF NOT EXISTS ix_branches_region_class
  ON branchops_branches (region_class);

-- ---------------------------------------------------------------------
--  Target Pemenuhan TBO (Agustus 2026)
--
--  Tenggat kapan dokumen TBO seharusnya sudah lengkap. Diisi dari kolom
--  paling kanan berkas Excel unggahan, atau lewat layar Edit TBO.
--
--  "Jumlah Hari Terlambat" SENGAJA TIDAK disimpan sebagai kolom. Nilainya
--  berubah setiap hari, dan aplikasi ini tidak punya penjadwal yang bisa
--  menghitung ulang tiap malam - kolom tersimpan akan salah mulai besok.
--  Jadi dihitung saat dibaca, di analytics.dash_tbo().
-- ---------------------------------------------------------------------
ALTER TABLE branchops_tbo
  ADD COLUMN IF NOT EXISTS target_pemenuhan_tbo DATE;

CREATE INDEX IF NOT EXISTS ix_bo_tbo_target
  ON branchops_tbo (target_pemenuhan_tbo);

-- ---------------------------------------------------------------------
--  Pelacakan TBO pada PENCAIRAN (Agustus 2026)
--
--  Sebagian baris pencairan membawa kolom "Data TBO" dari cabang. Baris
--  itu perlu dilacak seperti pembukaan rekening ber-TBO: punya tenggat,
--  punya status, dan bisa disunting.
--
--  no_cif dan no_rekening SENGAJA boleh kosong. Keduanya kolom tambahan
--  di ujung kanan berkas Excel, dan berkas lama tidak memilikinya sama
--  sekali - menjadikannya wajib akan menolak seluruh unggahan lama.
--
--  Sama seperti di branchops_tbo, "Jumlah Hari Terlambat" TIDAK disimpan.
--  Nilainya berubah tiap hari dan tidak ada penjadwal yang menghitung
--  ulang; jadi dihitung saat dibaca, di analytics.py.
-- ---------------------------------------------------------------------
ALTER TABLE branchops_pencairan
  ADD COLUMN IF NOT EXISTS no_cif               VARCHAR(60),
  ADD COLUMN IF NOT EXISTS no_rekening          VARCHAR(40),
  ADD COLUMN IF NOT EXISTS target_pemenuhan_tbo DATE,
  ADD COLUMN IF NOT EXISTS tgl_tbo_lengkap      DATE,
  ADD COLUMN IF NOT EXISTS tbo_updated_by       VARCHAR(255),
  ADD COLUMN IF NOT EXISTS tbo_updated_at       TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS status_tbo           VARCHAR(16)
      NOT NULL DEFAULT 'Outstanding';

-- CHECK dipasang terpisah dan dijaga, karena ADD CONSTRAINT tidak punya
-- IF NOT EXISTS - menjalankannya dua kali akan gagal.
DO $pc_status$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                  WHERE conname = 'ck_bo_pencairan_status_tbo') THEN
    -- 'Tidak ada TBO' sejak 16 Agu 2026, lihat aturan 27. Basis data
    -- yang sudah punya CHECK versi lama TIDAK lewat sini - blok
    -- 'status_tbo_baku_migrasi' di bawah yang membongkar dan memasang
    -- ulang keduanya.
    ALTER TABLE branchops_pencairan
      ADD CONSTRAINT ck_bo_pencairan_status_tbo
      CHECK (status_tbo IN ('Outstanding', 'Lengkap', 'Tidak ada TBO'));
  END IF;
END
$pc_status$;

CREATE INDEX IF NOT EXISTS ix_bo_pc_target ON branchops_pencairan (target_pemenuhan_tbo);
CREATE INDEX IF NOT EXISTS ix_bo_pc_status ON branchops_pencairan (status_tbo);

-- =====================================================================
--  MIGRASI 16 Agu 2026 - 'Dikecualikan' menjadi 'Tidak ada TBO'
-- =====================================================================
--  Keputusan pemilik. Istilah 'Dikecualikan' tidak memberi tahu APA yang
--  dikecualikan; 'Tidak ada TBO' menyatakan keadaannya langsung.
--
--  KENA DUA TABEL, dan itu bukan pilihan melainkan keharusan:
--  branchops_tbo DAN branchops_pencairan memakai kolom status_tbo yang
--  sama dengan tiga nilai yang sama, dan _STATUS_BERANDA di analytics.py
--  adalah SATU penyaring yang dipasang ke KEDUA lengan UNION di Beranda.
--  Memindahkan satu tabel saja membuat kotak pilihan "Status TBO" di
--  Beranda cocok dengan baris TBO tetapi tidak dengan baris Pencairan -
--  tanpa galat, hanya baris yang hilang dari daftar.
--
--  KENAPA INI LEBIH AMAN daripada rename jenis_pencairan pada 15 Agu:
--  tidak ada satu pun KPI, grafik, atau rekonsiliasi yang menyaring pada
--  'Dikecualikan'. Semuanya menyaring pada 'Outstanding', yang tidak
--  berubah. Satu-satunya pembanding fungsional adalah _STATUS_BERANDA.
--
--  YANG MEMBUATNYA TETAP HARUS HATI-HATI: ada DUA CHECK constraint yang
--  masih memuat daftar lama. UPDATE akan DITOLAK selama keduanya masih
--  terpasang, jadi urutannya mengikat - buang CHECK, baru UPDATE, baru
--  pasang lagi. Membalik urutannya bukan menghasilkan data yang salah,
--  melainkan migrasi yang gagal di tengah.
--
--  Nama constraint-nya DICARI, bukan ditulis tetap. Yang di
--  branchops_tbo bernama otomatis ('branchops_tbo_status_tbo_check',
--  karena CHECK-nya menyatu di CREATE TABLE) sedangkan yang di
--  branchops_pencairan diberi nama sendiri. Mencarinya lewat definisi
--  membuat blok ini tetap benar walau basis data lain menamainya lain.
--
--  VARCHAR(16) - 'Tidak ada TBO' 13 karakter, muat. Kalau suatu saat
--  istilahnya diganti lagi dengan yang lebih panjang, kolomnya harus
--  ikut dilebarkan lebih dulu.
DO $status_tbo_baku$
DECLARE r RECORD;
BEGIN
  IF NOT EXISTS (SELECT 1 FROM branchops_settings
                 WHERE kunci = 'status_tbo_baku_migrasi') THEN

    -- 1. Buang SEMUA CHECK yang masih menyebut ejaan lama, di tabel mana
    --    pun. Tanpa langkah ini UPDATE di bawah ditolak constraint.
    FOR r IN SELECT conrelid::regclass AS tabel, conname
               FROM pg_constraint
              WHERE contype = 'c'
                AND pg_get_constraintdef(oid) LIKE '%Dikecualikan%'
    LOOP
      EXECUTE format('ALTER TABLE %s DROP CONSTRAINT %I', r.tabel, r.conname);
      RAISE NOTICE 'CHECK lama dibuang: %.%', r.tabel, r.conname;
    END LOOP;

    -- 2. Pindahkan datanya, kedua tabel.
    IF to_regclass('public.branchops_tbo') IS NOT NULL THEN
      UPDATE branchops_tbo
         SET status_tbo = 'Tidak ada TBO'
       WHERE status_tbo = 'Dikecualikan';
    END IF;
    IF to_regclass('public.branchops_pencairan') IS NOT NULL THEN
      UPDATE branchops_pencairan
         SET status_tbo = 'Tidak ada TBO'
       WHERE status_tbo = 'Dikecualikan';
    END IF;

    -- 3. Pasang lagi CHECK-nya dengan daftar baru. Nama yang dipakai
    --    SAMA PERSIS dengan nama otomatis PostgreSQL untuk yang di
    --    branchops_tbo, supaya basis data hasil migrasi dan basis data
    --    yang dibuat dari nol berakhir dengan nama constraint identik.
    IF to_regclass('public.branchops_tbo') IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM pg_constraint
                        WHERE conname = 'branchops_tbo_status_tbo_check') THEN
      ALTER TABLE branchops_tbo
        ADD CONSTRAINT branchops_tbo_status_tbo_check
        CHECK (status_tbo IN ('Outstanding','Lengkap','Tidak ada TBO'));
    END IF;
    IF to_regclass('public.branchops_pencairan') IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM pg_constraint
                        WHERE conname = 'ck_bo_pencairan_status_tbo') THEN
      ALTER TABLE branchops_pencairan
        ADD CONSTRAINT ck_bo_pencairan_status_tbo
        CHECK (status_tbo IN ('Outstanding','Lengkap','Tidak ada TBO'));
    END IF;

    INSERT INTO branchops_settings (kunci, nilai, deskripsi) VALUES
     ('status_tbo_baku_migrasi', '1',
      'Penanda bahwa status_tbo pada branchops_tbo dan branchops_pencairan '
      'sudah dipindahkan dari Dikecualikan ke Tidak ada TBO, 16 Agu 2026, '
      'berikut kedua CHECK constraint-nya. JANGAN dihapus - menghapusnya '
      'membuat blok ini membongkar-pasang constraint setiap aplikasi start.')
    ON CONFLICT (kunci) DO NOTHING;
  END IF;
END
$status_tbo_baku$;

-- SEKALI SAJA: baris lama semuanya dapat 'Outstanding' dari DEFAULT di
-- atas, termasuk baris yang tidak punya Data TBO sama sekali. Baris itu
-- seharusnya 'Tidak ada TBO' - kalau dibiarkan, laporan "TBO pencairan
-- yang masih terbuka" akan menghitung ribuan baris yang memang tidak
-- pernah punya TBO.
--
-- Nilainya dulu 'Dikecualikan'; berganti 16 Agu 2026, aturan 27. Kalau
-- basis data ini sudah pernah menjalankan blok tersebut, penjaganya
-- sudah terpasang dan blok ini dilewati - jadi nilai baru di bawah hanya
-- berlaku untuk basis data yang belum pernah dimigrasikan sama sekali.
--
-- Penjaga di branchops_settings WAJIB ada. Tanpa itu blok ini jalan lagi
-- setiap aplikasi start, dan keputusan editor yang mengubah status
-- kembali ke 'Outstanding' akan diam-diam ditimpa tiap kali server hidup.
DO $pc_backfill$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM branchops_settings
                  WHERE kunci = 'pencairan_status_tbo_migrasi') THEN

    UPDATE branchops_pencairan
       SET status_tbo = 'Tidak ada TBO'
     WHERE data_tbo IS NULL
        OR btrim(data_tbo) = ''
        -- Aturan yang SAMA dengan _TIDAK_ADA di ingest.py. Kalau salah
        -- satu diubah, ubah keduanya, atau layar Edit dan laporan akan
        -- tidak sepakat baris mana yang punya TBO.
        OR btrim(lower(data_tbo)) ~ '^(tidak\s*ada|tdk\s*ada|tidak\s*ad|-)$';

    INSERT INTO branchops_settings (kunci, nilai, deskripsi) VALUES
      ('pencairan_status_tbo_migrasi', '1',
       'Penanda bahwa status_tbo pada branchops_pencairan sudah diisi '
       'sekali untuk baris lama. JANGAN dihapus - menghapusnya membuat '
       'migrasi berjalan lagi dan menimpa status yang sudah disunting.')
    ON CONFLICT (kunci) DO NOTHING;
  END IF;
END
$pc_backfill$;

-- =====================================================================
--  MIGRASI 15 Agu 2026 - penyeragaman ejaan nilai baku
-- =====================================================================
--  Dua kolom berganti ejaan baku:
--    jenis_pencairan : 'Dipercepat dari Jatuh Tempo' -> 'Dipercepat (Break)'
--    jenis_penarikan : 'Pemindahbukuan'              -> 'Pemindah-bukuan'
--
--  KENAPA HARUS DIMIGRASIKAN, bukan dibiarkan dua ejaan hidup bersama:
--  string lama itu disaring persis di dua tempat - KPI 'dipercepat' di
--  analytics.py dan penyaring sisi cabang pada rekonsiliasi di
--  storage.py - plus konstanta JDIP di branchops.html yang menggerakkan
--  dua grafik harian dan tabel Rincian. Baris yang tertinggal pada ejaan
--  lama berhenti terhitung di semua tempat itu tanpa satu pun galat.
--
--  jenis_setoran pada branchops_tbo SENGAJA TIDAK ikut: keputusan pemilik
--  15 Agu 2026, kolom itu tetap 'Pemindahbukuan' tanpa tanda hubung,
--  mengikuti ejaan yang sudah ada di datanya. Kedua kolom ada di tabel
--  berbeda dan tidak pernah dibandingkan kode mana pun.
--
--  ^^^ KEPUTUSAN ITU DIBALIK 16 Agu 2026. Alinea di atas dibiarkan supaya
--  jelas apa yang berubah. jenis_setoran pada branchops_tbo kini memakai
--  'Pemindah-bukuan' juga, jadi kedua tabel akhirnya mengeja sama.
--  Membaliknya gratis karena dihitung dari cadangan 15 Agu, NOL baris
--  branchops_tbo memakai ejaan mana pun - isinya 117 'Transfer', 2
--  'Tunai', 26 kosong, sisanya nilai kolom sebelah. Jadi tidak ada UPDATE
--  yang perlu dijalankan untuk kolom ini; yang berubah hanya daftar
--  pilihan di layar, benih ref_values, dropdown template Excel dan
--  _SERAGAM di ingest.py.
--
--  Penjaga 'ejaan_baku_migrasi' WAJIB ada. Tanpa itu blok ini jalan lagi
--  setiap aplikasi start - tidak merusak apa-apa hari ini, tetapi menjadi
--  perintah UPDATE tanpa alasan pada setiap restart, dan menyulitkan
--  membedakan mana yang diubah migrasi dan mana yang diubah orang.
DO $ejaan_baku$
BEGIN
  IF to_regclass('public.branchops_pencairan') IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM branchops_settings
                     WHERE kunci = 'ejaan_baku_migrasi') THEN

    UPDATE branchops_pencairan
       SET jenis_pencairan = 'Dipercepat (Break)'
     WHERE jenis_pencairan = 'Dipercepat dari Jatuh Tempo';

    UPDATE branchops_pencairan
       SET jenis_penarikan = 'Pemindah-bukuan'
     WHERE jenis_penarikan = 'Pemindahbukuan';

    DELETE FROM branchops_ref_values
     WHERE kategori = 'jenis_pencairan'
       AND nilai    = 'Dipercepat dari Jatuh Tempo';

    INSERT INTO branchops_settings (kunci, nilai, deskripsi) VALUES
     ('ejaan_baku_migrasi', '1',
      'Penanda bahwa baris lama sudah diseragamkan ke ejaan baku 15 Agu '
      '2026 (Dipercepat (Break) dan Pemindah-bukuan). JANGAN dihapus - '
      'menghapusnya membuat UPDATE ini berjalan lagi setiap aplikasi start.')
    ON CONFLICT (kunci) DO NOTHING;
  END IF;
END
$ejaan_baku$;

-- =====================================================================
--  MIGRASI 16 Agu 2026 - ejaan baku jenis_rekening pada branchops_tbo
-- =====================================================================
--  'Perusahaan (Non Perorangan)'  ->  'Non Perorangan (Perusahaan)'
--
--  Urutan katanya dibalik atas keputusan pemilik 16 Agu 2026, bersamaan
--  dengan dipasangnya kotak pilihan di layar Ubah TBO (aturan 26).
--  Terhitung 84 baris dari 176 pada cadangan 15 Agu.
--
--  KENAPA nilainya ikut dipindahkan, bukan sekadar labelnya diperhalus:
--  optJaga() di branchops.html memang bisa menampilkan label berbeda dari
--  nilai tersimpan, dan itu pilihan yang ditawarkan. Pemilik memilih
--  memindahkan nilainya supaya kolom ini benar-benar hanya punya satu
--  ejaan di basis data - itulah tujuan seluruh perubahan ini.
--
--  KONSEKUENSINYA, dan ini yang membuat blok ini tidak berdiri sendiri:
--  begitu nilai tersimpan berubah, berkas Excel LAMA yang masih memuat
--  ejaan lama akan memasukkannya kembali pada unggahan berikutnya. Karena
--  itu _SERAGAM di ingest.py mendapat pemetaannya, DAN parse_tbo kini
--  benar-benar memanggil seragam() untuk kolom ini - sebelum 16 Agu 2026
--  ia tidak memanggilnya sama sekali, sehingga pemetaan apa pun tidak
--  akan berpengaruh. Pelajaran yang sama dengan aturan 24.
--
--  Berbeda dengan jenis_pencairan pada migrasi 15 Agu, TIDAK ADA
--  penyaring, KPI, grafik atau rekonsiliasi yang menyaring persis pada
--  string ini - jenis_rekening hanya ditampilkan dan dikelompokkan
--  apa adanya (aggGroups di branchops.html). Jadi baris yang tertinggal
--  pada ejaan lama akan terlihat sebagai kelompok terpisah, bukan hilang
--  diam-diam. Tetap dimigrasikan supaya laporannya tidak terbelah dua.
--
--  34 baris yang jenis_rekening-nya berisi 'Transfer' atau 'Deposito'
--  SENGAJA TIDAK disentuh blok ini. Itu bukan salah ejaan, melainkan
--  nilai kolom sebelah yang masuk karena berkas unggahannya bergeser satu
--  kolom (batch 26 dan 62, aturan 8). Menebak isi yang benar dari sini
--  berarti mengarang data; perbaikannya adalah mengunggah ulang berkas
--  yang benar, dan sampai itu terjadi nilai lamanya tetap terlihat.
--
--  Penjaga 'jenis_rekening_baku_migrasi' WAJIB ada, alasan sama seperti
--  blok di atas: tanpa itu UPDATE ini berjalan lagi setiap aplikasi start.

DO $jenis_rekening_baku$
BEGIN
  IF to_regclass('public.branchops_tbo') IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM branchops_settings
                     WHERE kunci = 'jenis_rekening_baku_migrasi') THEN

    UPDATE branchops_tbo
       SET jenis_rekening = 'Non Perorangan (Perusahaan)'
     WHERE jenis_rekening = 'Perusahaan (Non Perorangan)';

    DELETE FROM branchops_ref_values
     WHERE kategori = 'jenis_rekening'
       AND nilai    = 'Perusahaan (Non Perorangan)';

    INSERT INTO branchops_settings (kunci, nilai, deskripsi) VALUES
     ('jenis_rekening_baku_migrasi', '1',
      'Penanda bahwa jenis_rekening pada branchops_tbo sudah dipindahkan '
      'ke ejaan baku 16 Agu 2026 (Non Perorangan (Perusahaan)). JANGAN '
      'dihapus - menghapusnya membuat UPDATE ini berjalan lagi setiap '
      'aplikasi start.')
    ON CONFLICT (kunci) DO NOTHING;
  END IF;
END
$jenis_rekening_baku$;

-- Sumber dana asal dan tujuan transfer (15 Agu 2026), diisi lewat layar
-- Ubah di menu Pencairan - bukan dari Excel. Berkas unggahan TIDAK berubah,
-- jadi baris yang baru diunggah memulai dengan kelima kolom ini kosong.
-- Kalau nanti ingin ikut dari Excel, aturan 8 berlaku: tambahkan di UJUNG
-- KANAN sheet (kolom bebas berikutnya untuk pencairan adalah kolom 21 /
-- r[20]) dan jadikan opsional, jangan disisipkan di tengah.
--
-- sumber_produk sengaja TANPA CHECK. Daftar pilihannya ditegakkan di
-- _PENCAIRAN_EDITABLE (satu tempat, lapisan API). CHECK di sini berarti
-- daftar yang sama harus dijaga di dua tempat, dan kalau kolom ini suatu
-- saat ikut datang dari Excel, satu nilai tak terduga akan menolak seluruh
-- barisnya - bukan sekadar mengosongkan satu sel.
ALTER TABLE IF EXISTS branchops_pencairan
  ADD COLUMN IF NOT EXISTS sumber_produk  VARCHAR(20),
  ADD COLUMN IF NOT EXISTS sumber_no_rek  VARCHAR(60),
  ADD COLUMN IF NOT EXISTS tujuan_bank    VARCHAR(120),
  ADD COLUMN IF NOT EXISTS tujuan_no_rek  VARCHAR(60),
  ADD COLUMN IF NOT EXISTS tujuan_nama    VARCHAR(160);

-- Tabel branchops_users dibuat oleh SQLAlchemy di app.py, bukan berkas ini.
-- IF EXISTS dipakai supaya tidak gagal bila urutan startup berbeda.
ALTER TABLE IF EXISTS branchops_users
  ADD COLUMN IF NOT EXISTS region_class VARCHAR(60);

-- Wajib ganti sandi pada login pertama (15 Agu 2026). Bawaannya TRUE, jadi
-- setiap akun BARU - termasuk yang dibuat langsung lewat SQL - mewarisi
-- kewajiban itu tanpa penulisnya perlu ingat.
ALTER TABLE IF EXISTS branchops_users
  ADD COLUMN IF NOT EXISTS harus_ganti_sandi BOOLEAN NOT NULL DEFAULT TRUE;

-- SEKALI SAJA: pengguna yang SUDAH ADA sebelum fitur ini dipasang
-- dibebaskan. Tanpa blok ini, ADD COLUMN ... DEFAULT TRUE di atas memaksa
-- SETIAP akun lama - termasuk admin - mengganti sandinya pada login
-- berikutnya, padahal yang diminta hanya berlaku bagi pengguna baru.
--
-- Penjaga 'wajib_ganti_sandi_migrasi' WAJIB ada, pola yang sama dengan
-- region_class_migrasi dan pencairan_status_tbo_migrasi di berkas ini.
-- Tanpa penjaga itu blok ini jalan lagi setiap aplikasi start, dan setiap
-- akun BARU yang belum sempat login akan diam-diam dibebaskan dari
-- kewajiban ganti sandi - yang persis membatalkan fiturnya.
DO $wajib_ganti_sandi$
BEGIN
  IF to_regclass('public.branchops_users') IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM branchops_settings
                     WHERE kunci = 'wajib_ganti_sandi_migrasi') THEN

    UPDATE branchops_users SET harus_ganti_sandi = FALSE;

    INSERT INTO branchops_settings (kunci, nilai, deskripsi) VALUES
     ('wajib_ganti_sandi_migrasi', '1',
      'Penanda bahwa pengguna yang sudah ada saat fitur wajib-ganti-sandi '
      'dipasang telah dibebaskan sekali. JANGAN dihapus - menghapusnya '
      'membuat blok ini jalan lagi saat aplikasi restart dan membebaskan '
      'akun baru yang belum sempat login.')
    ON CONFLICT (kunci) DO NOTHING;
  END IF;
END
$wajib_ganti_sandi$;

-- SEKALI SAJA: pengguna yang sudah ada sebelum fitur ini dipasang diberi
-- kelas 'SEMUA' supaya pemasangan tidak mengunci siapa pun.
--
-- Penjaga 'region_class_migrasi' penting. Tanpa itu, blok ini akan jalan
-- lagi setiap aplikasi restart, dan setiap pengguna BARU yang belum
-- dijatah wilayah akan diam-diam diberi akses ke semua cabang.
-- Daftar wilayah tinggal di branchops_ref_values (kategori 'wilayah').
-- Isi awalnya diambil dari region_class yang sudah ada di master cabang,
-- supaya memasang layar Master Data tidak dimulai dari daftar kosong
-- padahal cabangnya sudah berwilayah.
INSERT INTO branchops_ref_values (kategori, nilai, urutan)
SELECT 'wilayah', b.region_class, 0
  FROM (SELECT DISTINCT region_class FROM branchops_branches
         WHERE region_class IS NOT NULL AND region_class <> '') b
ON CONFLICT (kategori, nilai) DO NOTHING;

DO $migrasi$
BEGIN
  IF to_regclass('public.branchops_users') IS NOT NULL
     AND NOT EXISTS (SELECT 1 FROM branchops_settings
                     WHERE kunci = 'region_class_migrasi') THEN

    UPDATE branchops_users SET region_class = 'SEMUA'
     WHERE region_class IS NULL;

    INSERT INTO branchops_settings (kunci, nilai, deskripsi) VALUES
     ('region_class_migrasi', '1',
      'Penanda bahwa pengguna lama sudah diberi kelas SEMUA saat fitur Region Class dipasang. JANGAN dihapus - menghapusnya membuat semua pengguna tanpa jatah wilayah mendapat akses penuh saat aplikasi restart.')
    ON CONFLICT (kunci) DO NOTHING;

  END IF;
END
$migrasi$;


-- =====================================================================
--  MIGRASI Agustus 2026 - jatah CABANG (beberapa cabang per pengguna)
-- =====================================================================
--  Lapisan kedua di samping region_class. Sebagian pengguna tidak
--  memegang satu wilayah penuh, melainkan sekumpulan kecil cabang -
--  misalnya beberapa cabang dalam satu kota.
--
--  SALING MENIADAKAN dengan region_class: seorang pengguna memegang
--  SATU jenis jatah saja, bukan dua. Aturan itu ditegakkan oleh CHECK di
--  bawah, bukan hanya oleh kode Python. Alasannya: kalau hanya kode yang
--  menjaganya, satu endpoint baru yang lupa memeriksa sudah cukup untuk
--  menyimpan baris bermakna ganda, dan yang mana yang berlaku menjadi
--  bergantung pada urutan pemeriksaan di scoping.py.
--
--  RIWAYAT. Versi pertama memakai kolom tunggal branch_code (tepat satu
--  cabang). Blok di bawah memindahkan isinya menjadi larik satu unsur
--  lalu MEMBUANG kolom lama, supaya tidak tertinggal kolom mati yang
--  disangka fitur setengah jadi. Urutannya penting: CHECK lama menyebut
--  branch_code, jadi ia harus dibuang lebih dulu daripada kolomnya.
--
--  "Tidak dijatah" SELALU ditulis NULL, tidak pernah larik kosong '{}'.
--  Dua cara menulis hal yang sama akan membuat setiap pembacaan harus
--  memeriksa dua bentuk, dan cepat atau lambat ada satu yang lupa.
--  cardinality(...) > 0 di CHECK yang menegakkannya.
--
--  Sengaja TANPA foreign key ke branchops_branches, mengikuti pola
--  region_class yang juga diperiksa di Python. Akibat yang perlu diingat:
--  bila sebuah cabang hilang dari master, pengguna yang tertambat padanya
--  tidak melihat baris cabang itu - gagal-tertutup, bukan gagal-terbuka.
-- ---------------------------------------------------------------------

ALTER TABLE IF EXISTS branchops_users
  ADD COLUMN IF NOT EXISTS branch_codes TEXT[];

DO $jatah$
BEGIN
  IF to_regclass('public.branchops_users') IS NULL THEN
    RETURN;
  END IF;

  -- Pindahkan jatah lama (satu cabang) lalu buang kolomnya. Seluruhnya
  -- dijaga IF EXISTS, jadi aman dijalankan berulang: sesudah kolom lama
  -- hilang, blok ini tidak melakukan apa-apa lagi.
  IF EXISTS (SELECT 1 FROM information_schema.columns
              WHERE table_name = 'branchops_users'
                AND column_name = 'branch_code') THEN

    UPDATE branchops_users
       SET branch_codes = ARRAY[branch_code]
     WHERE branch_code IS NOT NULL
       AND branch_codes IS NULL;

    ALTER TABLE branchops_users DROP CONSTRAINT IF EXISTS ck_bo_users_satu_jatah;
    ALTER TABLE branchops_users DROP COLUMN branch_code;
  END IF;

  IF NOT EXISTS (SELECT 1 FROM pg_constraint
                  WHERE conname = 'ck_bo_users_satu_jatah') THEN

    ALTER TABLE branchops_users
      ADD CONSTRAINT ck_bo_users_satu_jatah
      CHECK ((region_class IS NULL OR branch_codes IS NULL)
         AND (branch_codes IS NULL OR cardinality(branch_codes) > 0));

  END IF;
END
$jatah$;

COMMIT;
