-- =====================================================================
--  6b — SETELAH data VPS dimuat: perbaiki sequence, lalu periksa
--  Arah: VPS -> LOKAL
--
--  KENAPA sequence harus diperbaiki:
--  Berkas dump berisi id eksplisit (INSERT ... (id, ...)). Memasukkan id
--  secara langsung TIDAK menggerakkan sequence. Jadi sesudah pemuatan,
--  sequence masih menunjuk angka lama, dan unggahan Excel berikutnya
--  gagal dengan "duplicate key value violates unique constraint".
--  Gejalanya membingungkan karena datanya kelihatan baik-baik saja.
--
--  Catatan: 1-export-lokal.bat (arah lokal -> VPS) punya lubang yang
--  sama dan tidak pernah memperbaiki sequence di VPS.
-- =====================================================================

\set ON_ERROR_STOP on

BEGIN;

-- Bentuk tiga-argumen dipakai dengan sengaja. Kalau tabelnya kosong,
-- setval(seq, 1) saja membuat id pertama menjadi 2, bukan 1.
-- Argumen ketiga (is_called) memperbaiki itu.
--
-- branchops_branches, _role_menus dan _settings tidak punya sequence:
-- kuncinya branch_code / role / kunci, semuanya teks.
SELECT setval(pg_get_serial_sequence('branchops_ref_values', 'id'),
              COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM branchops_ref_values;

SELECT setval(pg_get_serial_sequence('branchops_batches', 'id'),
              COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM branchops_batches;

SELECT setval(pg_get_serial_sequence('branchops_stg', 'id'),
              COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM branchops_stg;

SELECT setval(pg_get_serial_sequence('branchops_issues', 'id'),
              COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM branchops_issues;

SELECT setval(pg_get_serial_sequence('branchops_it_break', 'id'),
              COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM branchops_it_break;

SELECT setval(pg_get_serial_sequence('branchops_pencairan', 'id'),
              COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM branchops_pencairan;

SELECT setval(pg_get_serial_sequence('branchops_tbo', 'id'),
              COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM branchops_tbo;

SELECT setval(pg_get_serial_sequence('branchops_rekon', 'id'),
              COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM branchops_rekon;

COMMIT;

-- =====================================================================
--  PEMERIKSAAN — baca angkanya, jangan hanya lihat "selesai"
-- =====================================================================

\echo ''
\echo '--- 1. Jumlah baris per tabel ---'
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
UNION ALL SELECT 'users (tidak disentuh)', count(*) FROM branchops_users
ORDER BY 1;

\echo ''
\echo '--- 2. Rentang tanggal yang masuk ---'
SELECT 'Data Break Deposito' AS data, min(tgl_break) AS dari, max(tgl_break) AS sampai
  FROM branchops_it_break
UNION ALL
SELECT 'Pencairan Deposito', min(tgl_input), max(tgl_input) FROM branchops_pencairan
UNION ALL
SELECT 'Data TBO',           min(tgl_input), max(tgl_input) FROM branchops_tbo;

\echo ''
\echo '--- 3. Baris yatim: batch atau cabang yang tidak ikut terbawa ---'
\echo '    HARUS 0 semua. Kalau tidak, dump dari VPS tidak lengkap.'
SELECT (SELECT count(*) FROM branchops_it_break f
         WHERE NOT EXISTS (SELECT 1 FROM branchops_batches b WHERE b.id = f.batch_id))
       AS it_break_tanpa_batch,
       (SELECT count(*) FROM branchops_pencairan f
         WHERE NOT EXISTS (SELECT 1 FROM branchops_batches b WHERE b.id = f.batch_id))
       AS pencairan_tanpa_batch,
       (SELECT count(*) FROM branchops_tbo f
         WHERE NOT EXISTS (SELECT 1 FROM branchops_batches b WHERE b.id = f.batch_id))
       AS tbo_tanpa_batch;

\echo ''
\echo '--- 4. Cabang yang ada di data tapi belum punya Wilayah ---'
\echo '    Cabang tanpa region_class hanya terlihat oleh admin.'
\echo '    Isi lewat tab Master Data kalau pengguna lain perlu melihatnya.'
SELECT b.branch_code, b.branch_name, b.branch_type
FROM   branchops_branches b
WHERE  b.region_class IS NULL
  AND  EXISTS (SELECT 1 FROM branchops_it_break  x WHERE x.branch_code = b.branch_code
               UNION ALL
               SELECT 1 FROM branchops_pencairan x WHERE x.branch_code = b.branch_code
               UNION ALL
               SELECT 1 FROM branchops_tbo       x WHERE x.branch_code = b.branch_code)
ORDER BY b.branch_code;

\echo ''
\echo '--- 5. PENGGUNA LOKAL YANG JATAHNYA JADI KOSONG ---'
\echo '    branchops_users tidak diganti, tapi master cabang diganti.'
\echo '    Nama yang muncul di sini tidak akan melihat baris apa pun.'
\echo '    Perbaiki lewat tab Pengguna. Kalau kosong, semua aman.'
SELECT u.email, u.role, u.region_class, u.branch_codes
FROM   branchops_users u
WHERE  u.role <> 'admin'
  AND  (
        (u.region_class IS NOT NULL
         AND u.region_class <> 'SEMUA'
         AND NOT EXISTS (SELECT 1 FROM branchops_branches b
                         WHERE b.region_class = u.region_class))
     OR (u.branch_codes IS NOT NULL
         AND NOT EXISTS (SELECT 1 FROM branchops_branches b
                         WHERE b.branch_code = ANY(u.branch_codes)))
     OR (u.region_class IS NULL AND u.branch_codes IS NULL)
       )
ORDER BY u.email;

\echo ''
\echo '--- 6. Sequence sudah di depan id tertinggi? ---'
\echo '    "sisa" harus >= 0 di semua baris.'
SELECT 'branchops_batches' AS tabel,
       (SELECT COALESCE(MAX(id), 0) FROM branchops_batches) AS id_tertinggi,
       (SELECT last_value FROM branchops_batches_id_seq)    AS sequence_di,
       (SELECT last_value FROM branchops_batches_id_seq)
         - (SELECT COALESCE(MAX(id), 0) FROM branchops_batches) AS sisa
UNION ALL
SELECT 'branchops_it_break',
       (SELECT COALESCE(MAX(id), 0) FROM branchops_it_break),
       (SELECT last_value FROM branchops_it_break_id_seq),
       (SELECT last_value FROM branchops_it_break_id_seq)
         - (SELECT COALESCE(MAX(id), 0) FROM branchops_it_break)
UNION ALL
SELECT 'branchops_pencairan',
       (SELECT COALESCE(MAX(id), 0) FROM branchops_pencairan),
       (SELECT last_value FROM branchops_pencairan_id_seq),
       (SELECT last_value FROM branchops_pencairan_id_seq)
         - (SELECT COALESCE(MAX(id), 0) FROM branchops_pencairan)
UNION ALL
SELECT 'branchops_tbo',
       (SELECT COALESCE(MAX(id), 0) FROM branchops_tbo),
       (SELECT last_value FROM branchops_tbo_id_seq),
       (SELECT last_value FROM branchops_tbo_id_seq)
         - (SELECT COALESCE(MAX(id), 0) FROM branchops_tbo)
UNION ALL
SELECT 'branchops_rekon',
       (SELECT COALESCE(MAX(id), 0) FROM branchops_rekon),
       (SELECT last_value FROM branchops_rekon_id_seq),
       (SELECT last_value FROM branchops_rekon_id_seq)
         - (SELECT COALESCE(MAX(id), 0) FROM branchops_rekon);

\echo ''
\echo '6b selesai.'
\echo ''
