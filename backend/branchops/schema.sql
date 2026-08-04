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
                      CHECK (status_tbo IN ('Outstanding','Lengkap','Dikecualikan')),
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

INSERT INTO branchops_ref_values (kategori, nilai, urutan) VALUES
 ('jenis_pencairan','Sesuai Jatuh Tempo',1),
 ('jenis_pencairan','Dipercepat dari Jatuh Tempo',2),
 ('jenis_penarikan','Tunai',1),
 ('jenis_penarikan','Transfer',2),
 ('jenis_rekening','Perorangan',1),
 ('jenis_rekening','Perusahaan (Non Perorangan)',2),
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

-- Tabel branchops_users dibuat oleh SQLAlchemy di app.py, bukan berkas ini.
-- IF EXISTS dipakai supaya tidak gagal bila urutan startup berbeda.
ALTER TABLE IF EXISTS branchops_users
  ADD COLUMN IF NOT EXISTS region_class VARCHAR(60);

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

COMMIT;
