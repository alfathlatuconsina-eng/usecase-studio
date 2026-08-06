-- ====================================================================
--  Langkah 3 (DI VPS) - akun pengguna Branch Ops
--  PILIH SATU PILIHAN SAJA. Jangan jalankan seluruh berkas ini.
-- ====================================================================
--  Jalankan dulu:  \i /tmp/bo-cadangan-pengguna.sql   (lihat runbook)
--
--  Ketiga pilihan di bawah TIDAK menyentuh dashboard lain. Akun PMO,
--  People Development, Service Quality dan E-Library ada di tabel
--  terpisah (users, people_users, quality_users, elibrary_users) dan
--  tidak ikut berubah apa pun yang Anda pilih di sini.
-- ====================================================================


-- --------------------------------------------------------------------
-- PILIHAN A - hanya struktur, akun dibuat baru di VPS  (paling aman)
-- --------------------------------------------------------------------
-- Tidak ada yang perlu dijalankan di sini sama sekali.
--
-- Kolom branch_codes dan CHECK ck_bo_users_satu_jatah dipasang otomatis
-- oleh ensure_schema() saat aplikasi start. Akun yang sudah ada di VPS
-- tetap utuh dan tetap bisa masuk seperti biasa.
--
-- Sesudah aplikasi hidup, buat/atur akun lewat layar Pengguna. Akun lama
-- yang belum punya jatah TIDAK terkunci: pengguna lama sudah diberi
-- kelas 'SEMUA' oleh migrasi region_class terdahulu.
--
-- Periksa hasilnya:
--   SELECT email, role, region_class, branch_codes FROM branchops_users;


-- --------------------------------------------------------------------
-- PILIHAN B - bawa penataan jatah, TAPI sandi diganti baru
-- --------------------------------------------------------------------
-- Untuk: Anda sudah menata peran dan jatah cabang di lokal dan tidak
-- ingin mengetiknya ulang, tapi sandi lokal tidak pantas dipakai di
-- produksi.
--
-- Cara pakai:
--   1. \i /tmp/bo-pengguna.sql   -- muat hasil ekspor ke tabel sementara
--      (lihat runbook: berkas itu dimuat ke bo_impor, bukan langsung
--       ke branchops_users)
--   2. jalankan blok di bawah
--   3. setel sandi tiap akun lewat layar Pengguna -> "Reset sandi"
--
-- Akun yang SUDAH ADA di VPS hanya diperbarui peran dan jatahnya.
-- Sandinya TIDAK disentuh, jadi orang yang sedang memakainya tidak
-- kehilangan akses. Akun BARU dibuat dengan sandi mustahil ditebak yang
-- harus di-reset sebelum bisa dipakai.
/*
BEGIN;

  -- akun yang sudah ada: perbarui peran + jatah, biarkan sandinya
  UPDATE branchops_users u
     SET role         = i.role,
         region_class = i.region_class,
         branch_codes = i.branch_codes
    FROM bo_impor i
   WHERE lower(u.email) = lower(i.email);

  -- akun baru: dibuat terkunci. '!' bukan hash bcrypt yang sah, jadi
  -- tidak ada sandi apa pun yang cocok sampai admin me-reset-nya.
  INSERT INTO branchops_users (email, pw_hash, role, region_class, branch_codes)
  SELECT lower(i.email), '!', i.role, i.region_class, i.branch_codes
    FROM bo_impor i
   WHERE NOT EXISTS (SELECT 1 FROM branchops_users u
                      WHERE lower(u.email) = lower(i.email));

  -- lihat hasilnya SEBELUM disimpan permanen
  SELECT email, role, region_class, branch_codes,
         CASE WHEN pw_hash = '!' THEN 'PERLU RESET SANDI' ELSE 'sandi lama dipakai' END AS sandi
    FROM branchops_users ORDER BY email;

COMMIT;   -- ganti jadi ROLLBACK; kalau hasilnya tidak sesuai
*/


-- --------------------------------------------------------------------
-- PILIHAN C - salin apa adanya, termasuk sandi
-- --------------------------------------------------------------------
-- Untuk: akun lokal memang akun produksi dan sandinya memang layak.
--
-- SEBELUM MENJALANKAN, pastikan dua hal:
--   - sandi akun lokal bukan sandi percobaan ("admin123" dan sejenisnya)
--   - Anda sudah tahu akun mana di VPS yang akan tertimpa
--
-- Perintah ini MENIMPA sandi akun yang emailnya sama. Orang yang selama
-- ini memakai akun itu di VPS akan langsung tidak bisa masuk dengan
-- sandi lamanya.
/*
BEGIN;

  -- lihat dulu siapa yang akan tertimpa
  SELECT u.email AS akun_vps_yang_tertimpa, u.role AS peran_sekarang
    FROM branchops_users u
    JOIN bo_impor i ON lower(i.email) = lower(u.email);

  INSERT INTO branchops_users (email, pw_hash, role, region_class, branch_codes)
  SELECT lower(i.email), i.pw_hash, i.role, i.region_class, i.branch_codes
    FROM bo_impor i
  ON CONFLICT (email) DO UPDATE
     SET pw_hash      = EXCLUDED.pw_hash,
         role         = EXCLUDED.role,
         region_class = EXCLUDED.region_class,
         branch_codes = EXCLUDED.branch_codes;

  SELECT email, role, region_class, branch_codes FROM branchops_users ORDER BY email;

COMMIT;   -- ganti jadi ROLLBACK; kalau hasilnya tidak sesuai
*/


-- --------------------------------------------------------------------
-- PEMERIKSAAN AKHIR - jalankan apa pun pilihan Anda
-- --------------------------------------------------------------------
-- 1. Tidak boleh ada akun yang memegang DUA jenis jatah sekaligus.
--    CHECK ck_bo_users_satu_jatah seharusnya sudah mencegahnya; query
--    ini memastikan tidak ada baris lama yang lolos sebelum CHECK ada.
--    Harus mengembalikan 0 baris.
SELECT email, region_class, branch_codes
  FROM branchops_users
 WHERE region_class IS NOT NULL AND branch_codes IS NOT NULL;

-- 2. Tidak boleh ada larik kosong. "Tidak dijatah" selalu NULL.
--    Harus mengembalikan 0 baris.
SELECT email FROM branchops_users WHERE branch_codes = '{}';

-- 3. Jatah cabang yang menunjuk cabang tidak ada di master.
--    Akun seperti ini tidak akan melihat baris apa pun (gagal-tertutup).
SELECT u.email, k AS kode_cabang_tidak_dikenal
  FROM branchops_users u, unnest(u.branch_codes) k
 WHERE NOT EXISTS (SELECT 1 FROM branchops_branches b WHERE b.branch_code = k);

-- 4. Ringkasan siapa melihat apa.
SELECT email, role,
       COALESCE(region_class,
                CASE WHEN branch_codes IS NULL THEN '(tanpa jatah - tidak melihat apa pun)'
                     ELSE cardinality(branch_codes) || ' cabang: ' ||
                          array_to_string(branch_codes, ', ') END) AS jatah
  FROM branchops_users ORDER BY role, email;
