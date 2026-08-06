-- =====================================================================
--  7 - Membatalkan (atau menghapus) satu batch Branch Ops, lewat SQL
--
--  CARA PAKAI - jalankan dari folder proyek:
--    psql -U postgres -d pmo -v ON_ERROR_STOP=1 -v BATCH=27 ^
--         -f deploy\7-batalkan-batch.sql
--
--  Lebih baik pakai tombol "Batal" di tab Unggah kalau bisa. Sejak
--  Agustus 2026 tombol itu muncul juga untuk batch berstatus committed.
--  Bedanya penting:
--
--    Lewat aplikasi : status berubah, rekonsiliasi dijalankan ulang
--                     OTOMATIS, dan tercatat di branchops_audit dengan
--                     email Anda.
--    Lewat SQL ini  : status berubah dan jejak audit ditulis manual di
--                     bawah, TAPI rekonsiliasi TIDAK ikut jalan. Anda
--                     harus menjalankannya sendiri sesudahnya - lihat
--                     catatan di akhir berkas.
-- =====================================================================

\set ON_ERROR_STOP on

\echo ''
\echo '--- Sebelum: batch yang akan disentuh ---'
SELECT id, jenis, status, nama_file, baris_total,
       periode_awal, periode_akhir, uploaded_by, uploaded_at
  FROM branchops_batches WHERE id = :BATCH;

\echo ''
\echo '--- Baris fakta yang menggantung pada batch ini ---'
SELECT 'it_break'  AS tabel, count(*) FROM branchops_it_break  WHERE batch_id = :BATCH
UNION ALL SELECT 'pencairan', count(*) FROM branchops_pencairan WHERE batch_id = :BATCH
UNION ALL SELECT 'tbo',       count(*) FROM branchops_tbo       WHERE batch_id = :BATCH
UNION ALL SELECT 'staging',   count(*) FROM branchops_stg       WHERE batch_id = :BATCH
UNION ALL SELECT 'issues',    count(*) FROM branchops_issues    WHERE batch_id = :BATCH
ORDER BY 1;

BEGIN;

-- ------------------------------------------------------------------ --
--  PILIHAN A - BATALKAN  (dipakai secara bawaan; bisa dikembalikan)
--
--  Baris TIDAK dihapus. Setiap query dashboard menyaring
--  status='committed' lewat _AKTIF di analytics.py, dan
--  periode_tersedia() juga hanya melihat batch committed. Jadi begitu
--  status berubah, barisnya hilang dari seluruh tampilan DAN dari
--  rentang tanggal bawaan - tanpa satu baris pun dibuang.
--
--  Bisa dikembalikan: commit_batch() menerima batch berstatus apa pun
--  selain 'committed', jadi "Komit lagi" di tab Unggah akan
--  mengaktifkannya kembali.
-- ------------------------------------------------------------------ --
UPDATE branchops_batches
   SET status = 'dibatalkan'
 WHERE id = :BATCH
   AND status <> 'dibatalkan';

-- Jejak audit ditulis tangan, karena jalur ini tidak lewat aplikasi.
-- Tanpa ini, batch berubah status tanpa ada yang tahu siapa dan kapan.
INSERT INTO branchops_audit (user_email, action, entity, entity_id, detail)
VALUES ('sql-langsung', 'batch_dibatalkan', 'branchops_batches', :'BATCH',
        jsonb_build_object(
          'cara', 'deploy/7-batalkan-batch.sql',
          'catatan', 'Dibatalkan lewat SQL langsung, bukan lewat aplikasi. '
                     'Rekonsiliasi BELUM dijalankan ulang.'));

-- ------------------------------------------------------------------ --
--  PILIHAN B - HAPUS PERMANEN  (TIDAK bisa dikembalikan)
--
--  Buang tanda komentar HANYA bila Anda memang ingin barisnya lenyap.
--  ON DELETE CASCADE ikut membersihkan branchops_stg, branchops_issues,
--  tabel fakta, dan branchops_rekon yang menunjuk baris fakta itu.
--
--  branchops_stg adalah SATU-SATUNYA salinan nilai mentah dari berkas
--  Excel - aplikasi menghapus berkas aslinya setelah diproses. Menghapus
--  batch berarti membuang bukti terakhir isi berkas itu.
-- ------------------------------------------------------------------ --
-- DELETE FROM branchops_batches WHERE id = :BATCH;

COMMIT;

\echo ''
\echo '--- Sesudah ---'
SELECT id, jenis, status, nama_file, baris_total FROM branchops_batches WHERE id = :BATCH;

\echo ''
\echo '--- Rentang tanggal bawaan sekarang (yang mengisi "Dari tanggal") ---'
SELECT min(p) AS awal, max(p) AS akhir FROM (
  SELECT periode_awal p FROM branchops_batches WHERE status='committed'
  UNION ALL
  SELECT periode_akhir FROM branchops_batches WHERE status='committed') s;

\echo ''
\echo '--- Tanggal paling awal yang masih terhitung, per tabel ---'
SELECT 'it_break' AS tabel, min(f.tgl_break) AS paling_awal
  FROM branchops_it_break f
  JOIN branchops_batches b ON b.id=f.batch_id AND b.status='committed'
UNION ALL
SELECT 'pencairan', min(f.tgl_input) FROM branchops_pencairan f
  JOIN branchops_batches b ON b.id=f.batch_id AND b.status='committed'
UNION ALL
SELECT 'tbo', min(f.tgl_input) FROM branchops_tbo f
  JOIN branchops_batches b ON b.id=f.batch_id AND b.status='committed'
ORDER BY 1;

\echo ''
\echo 'SELESAI.'
\echo ''
\echo 'BELUM SELESAI SEPENUHNYA - rekonsiliasi masih memakai hasil lama.'
\echo 'Baris rekon yang sumbernya sudah tidak aktif belum dibersihkan.'
\echo 'Jalankan ulang lewat aplikasi:  Dashboard 4 -> jalankan rekonsiliasi'
\echo 'atau  POST /api/branchops/rekonsiliasi/jalankan'
\echo ''
