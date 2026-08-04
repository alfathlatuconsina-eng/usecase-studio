-- =====================================================================
--  Membuang kolom 'region' lama dari branchops_branches
--  Dijalankan MANUAL, sekali saja, SETELAH mencadangkan database.
-- =====================================================================
--
--  KENAPA DIPISAH DARI schema.sql
--  ------------------------------
--  schema.sql dijalankan otomatis oleh ensure_schema() setiap aplikasi
--  start. Kalau perintah DROP COLUMN ditaruh di sana, kolom akan terhapus
--  begitu Anda menekan run_local.bat - tanpa sempat mencadangkan apa pun.
--  Karena itu perintahnya ditaruh di berkas terpisah ini.
--
--  APA YANG HILANG
--  ---------------
--  Kolom 'region' berisi hasil tebakan wilayah dari digit pertama kode
--  cabang. Tebakan itu tidak pernah bekerja: branch_code() menambal kode
--  jadi 5 digit lebih dulu ("1303" -> "01303"), sehingga digit pertama
--  selalu "0". Akibatnya seluruh 44 cabang bernilai "Kantor Pusat",
--  termasuk JAMBI dan TARAKAN. Nilai itu juga tidak pernah ditampilkan
--  di layar mana pun.
--
--  Jadi yang hilang adalah 44 baris berisi kata "Kantor Pusat" yang salah.
--  Penggantinya kolom region_class, diisi manual dari kolom D berkas
--  master cabang.
--
--  CADANGKAN DULU
--  --------------
--    "C:\Program Files\PostgreSQL\18\bin\pg_dump.exe" -U postgres -h localhost pmo > cadangan-sebelum-drop-region.sql
--
--  LALU JALANKAN BERKAS INI
--  ------------------------
--    "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -d pmo -f hapus-kolom-region-lama.sql
--
--  Aplikasi sudah berhenti memakai kolom ini, jadi menjalankan berkas ini
--  boleh ditunda. Membiarkannya hanya menyisakan satu kolom menganggur.
-- =====================================================================

BEGIN;

-- Tunjukkan dulu apa yang akan hilang.
SELECT region AS nilai_yang_akan_hilang, count(*) AS jumlah_cabang
  FROM branchops_branches
 GROUP BY region;

ALTER TABLE branchops_branches DROP COLUMN IF EXISTS region;

COMMIT;

-- Pemeriksaan sesudahnya: kolom harus tinggal region_class.
SELECT column_name
  FROM information_schema.columns
 WHERE table_name = 'branchops_branches'
 ORDER BY ordinal_position;
