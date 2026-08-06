-- ====================================================================
--  Langkah 4 (DI VPS) - selaraskan data acuan Branch Ops   [revisi 3]
-- ====================================================================
--  HANYA UPDATE dan INSERT ... ON CONFLICT DO NOTHING.
--
--  REVISI 3: memperbaiki pembuatan berkas ini, bukan isinya. Versi 1
--  dan 2 memecah nilai VALUES pada setiap koma tanpa memperhatikan
--  tanda kutip, sehingga larik '{home,d1,...}' terpotong di tengah dan
--  menghasilkan INSERT dengan kutip tak tertutup. PostgreSQL lalu
--  menelan baris-baris berikutnya sampai menemukan penutupnya, dan
--  melaporkan error di baris yang sebenarnya tidak bersalah.
--  REVISI 2: laporan dipindah keluar transaksi.
-- ====================================================================

\set ON_ERROR_STOP on

BEGIN;

-- 1. Daftar wilayah
INSERT INTO branchops_ref_values (kategori, nilai, urutan, aktif) VALUES ('wilayah', 'Regional 1', 0, true) ON CONFLICT (kategori, nilai) DO NOTHING;
INSERT INTO branchops_ref_values (kategori, nilai, urutan, aktif) VALUES ('wilayah', 'Regional 2', 0, true) ON CONFLICT (kategori, nilai) DO NOTHING;
INSERT INTO branchops_ref_values (kategori, nilai, urutan, aktif) VALUES ('wilayah', 'Kantor Pusat', 0, true) ON CONFLICT (kategori, nilai) DO NOTHING;

-- 2. Wilayah + tipe per cabang (44 cabang)
UPDATE branchops_branches SET region_class='Kantor Pusat', branch_type='Pusat' WHERE branch_code='00001';
UPDATE branchops_branches SET region_class='Kantor Pusat', branch_type='Pusat' WHERE branch_code='00002';
UPDATE branchops_branches SET region_class='Kantor Pusat', branch_type='Pusat' WHERE branch_code='00003';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KCP' WHERE branch_code='01001';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KCP' WHERE branch_code='01003';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KCP' WHERE branch_code='01004';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KCP' WHERE branch_code='01006';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KCP' WHERE branch_code='01008';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KC' WHERE branch_code='01100';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KCP' WHERE branch_code='01101';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KCP' WHERE branch_code='01102';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KCP' WHERE branch_code='01106';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KCP' WHERE branch_code='01202';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KC' WHERE branch_code='01204';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KC' WHERE branch_code='01206';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KCP' WHERE branch_code='01208';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KCP' WHERE branch_code='01301';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KCP' WHERE branch_code='01303';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KCP' WHERE branch_code='01401';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KCP' WHERE branch_code='01402';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KCP' WHERE branch_code='01403';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KCP' WHERE branch_code='01407';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KCP' WHERE branch_code='01408';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KC' WHERE branch_code='02001';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KCP' WHERE branch_code='02901';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KC' WHERE branch_code='03001';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KCP' WHERE branch_code='03002';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KC' WHERE branch_code='03050';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KCP' WHERE branch_code='03054';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KC' WHERE branch_code='03101';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KC' WHERE branch_code='03121';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KC' WHERE branch_code='03141';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KC' WHERE branch_code='04002';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KCP' WHERE branch_code='04004';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KC' WHERE branch_code='04101';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KCP' WHERE branch_code='04102';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KC' WHERE branch_code='04121';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KC' WHERE branch_code='04181';
UPDATE branchops_branches SET region_class='Regional 2', branch_type='KC' WHERE branch_code='04271';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KCP' WHERE branch_code='04291';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KC' WHERE branch_code='04231';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KC' WHERE branch_code='04251';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KC' WHERE branch_code='04161';
UPDATE branchops_branches SET region_class='Regional 1', branch_type='KC' WHERE branch_code='04141';

-- 3. Hak menu per peran
INSERT INTO branchops_role_menus (role, menus) VALUES ('editor', '{home,d1,d2,d3,d4,upload}') ON CONFLICT (role) DO NOTHING;

COMMIT;

-- ==== Laporan (di luar transaksi) ====
SELECT branch_code, branch_name, branch_type FROM branchops_branches
 WHERE region_class IS NULL ORDER BY branch_code;
SELECT region_class, count(*) AS jml_cabang FROM branchops_branches
 GROUP BY region_class ORDER BY region_class;
