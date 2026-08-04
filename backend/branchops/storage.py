"""Menyimpan hasil parse ke database, dan menjalankan rekonsiliasi.

Alur commit:
    upload  -> batch status 'draft', staging + fact terisi
    commit  -> status 'committed', batch draft lama untuk periode sama dibatalkan
Batch draft tidak pernah ikut terhitung di dashboard.
"""
from __future__ import annotations

import hashlib

import psycopg2.extras

from . import db

# --------------------------------------------------------------------------
# kolom per tabel fakta (urutan menentukan urutan INSERT)
# --------------------------------------------------------------------------
COLS = {
    "it_break": ("branchops_it_break", [
        "baris_no", "branch_code", "cabang_core", "saldo", "tgl_penempatan", "tgl_jatuh_tempo",
        "tgl_break", "waktu_awal", "waktu_akhir", "durasi_detik", "rek_pendebetan", "rek_norm",
        "nama_pemilik", "nama_terpotong", "nominal", "penalti", "mata_uang", "rate",
        "rek_pencairan", "nama_pencairan", "via_perantara", "cs_id", "cs_nama", "flm1_nama",
        "teller_id", "teller_nama", "flm2_id", "flm2_nama", "sisa_hari", "umur_hari",
        "break_sejati", "luar_jam", "flags"]),
    "pencairan": ("branchops_pencairan", [
        "baris_no", "branch_code", "tgl_input", "no_deposito", "no_deposito_norm", "nama_pemilik",
        "tgl_penempatan", "tgl_bilyet", "tgl_pencairan", "tenor_hari", "nominal",
        "jenis_pencairan", "jenis_penarikan", "data_tbo", "arus_dana", "arus_keyakinan",
        "arus_manual", "nip_maker", "nip_checker", "nip_approver", "checker_eq_approver",
        "catatan", "is_duplikat", "dup_dikecualikan", "skor_lengkap", "flags"]),
    "tbo": ("branchops_tbo", [
        "baris_no", "branch_code", "tgl_input", "no_cif", "cif_gabungan", "no_rekening",
        "no_rekening_norm", "nama_pemilik", "tgl_penempatan", "tgl_jatuh_tempo", "nominal",
        "mata_uang", "jenis_rekening", "jenis_setoran", "jenis_produk", "tipe_pembukaan",
        "dokumen_tbo", "ada_tbo", "status_tbo", "nip_maker", "nip_checker", "nip_approver",
        "keterangan", "flags"]),
}

TGL_PERIODE = {"it_break": "tgl_break", "pencairan": "tgl_input", "tbo": "tgl_input"}


def sha256_file(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def cek_duplikat_file(jenis, sha):
    return db.q1("""SELECT id, nama_file, uploaded_at, status FROM branchops_batches
                    WHERE jenis=%s AND sha256=%s AND status='committed'
                    ORDER BY id DESC LIMIT 1""", (jenis, sha))


# --------------------------------------------------------------------------
# simpan batch
# --------------------------------------------------------------------------
def simpan_batch(res, nama_file, ukuran, sha, user_email, catatan=None) -> int:
    tgl_kol = TGL_PERIODE[res.jenis]
    p_awal, p_akhir = res.periode(tgl_kol)

    with db.conn() as c:
        with c.cursor() as k:
            k.execute("""INSERT INTO branchops_batches
                   (jenis, nama_file, ukuran_byte, sha256, status, baris_total, baris_valid,
                    baris_ditolak, baris_warning, periode_awal, periode_akhir, uploaded_by, catatan)
                   VALUES (%s,%s,%s,%s,'draft',%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                      (res.jenis, nama_file, ukuran, sha, len(res.rows), res.baris_valid,
                       res.baris_ditolak, len({i.baris_no for i in res.warnings}),
                       p_awal, p_akhir, user_email, catatan))
            batch_id = k.fetchone()[0]

            # staging: seluruh baris apa adanya
            psycopg2.extras.execute_values(
                k, "INSERT INTO branchops_stg (batch_id, baris_no, payload) VALUES %s",
                [(batch_id, n, psycopg2.extras.Json(payload)) for n, payload in res.raw])

            # catatan validasi
            if res.issues:
                psycopg2.extras.execute_values(
                    k, """INSERT INTO branchops_issues
                          (batch_id, baris_no, severity, kode, pesan, kolom, nilai, branch_code)
                          VALUES %s""",
                    [(batch_id, i.baris_no, i.severity, i.kode, i.pesan, i.kolom, i.nilai,
                      i.branch_code) for i in res.issues])

            # fakta: hanya baris yang lolos hard error
            tabel, cols = COLS[res.jenis]
            baris = [r for r in res.rows if not r["_ditolak"]]
            if baris:
                psycopg2.extras.execute_values(
                    k,
                    f"INSERT INTO {tabel} (batch_id, {', '.join(cols)}) VALUES %s",
                    [tuple([batch_id] + [r.get(col) for col in cols]) for r in baris])
    return batch_id


def commit_batch(batch_id, user_email):
    """Jadikan batch aktif. Batch committed lain dengan jenis + periode sama dibatalkan."""
    b = db.q1("SELECT * FROM branchops_batches WHERE id=%s", (batch_id,))
    if not b:
        raise ValueError("Batch tidak ditemukan")
    if b["status"] == "committed":
        return b

    db.execute("""UPDATE branchops_batches SET status='dibatalkan'
                  WHERE jenis=%s AND status='committed' AND id<>%s
                    AND periode_awal=%s AND periode_akhir=%s""",
               (b["jenis"], batch_id, b["periode_awal"], b["periode_akhir"]))
    db.execute("""UPDATE branchops_batches SET status='committed', committed_by=%s, committed_at=now()
                  WHERE id=%s""", (user_email, batch_id))
    return db.q1("SELECT * FROM branchops_batches WHERE id=%s", (batch_id,))


def batalkan_batch(batch_id):
    db.execute("UPDATE branchops_batches SET status='dibatalkan' WHERE id=%s", (batch_id,))


def hapus_batch(batch_id):
    """Hapus permanen. Cascade membersihkan staging, issues, dan fakta."""
    db.execute("DELETE FROM branchops_batches WHERE id=%s", (batch_id,))


def upsert_branches(rows):
    """Simpan master cabang. Kode yang sudah ada diperbarui, bukan digandakan.

    region_class SENGAJA ditimpa apa adanya, termasuk bila kolomnya kosong di
    Excel. Alasannya: itulah cara admin mencabut wilayah sebuah cabang —
    kosongkan kolomnya lalu unggah ulang. Kalau nilai kosong diabaikan,
    wilayah lama akan menempel selamanya dan tidak bisa dihapus lewat aplikasi.

    Konsekuensi yang perlu diingat: mengunggah master TANPA kolom Region Class
    akan mengosongkan wilayah SEMUA cabang, dan pengguna non-admin langsung
    tidak melihat baris apa pun sampai masternya diunggah ulang dengan benar."""
    with db.conn() as c:
        with c.cursor() as k:
            psycopg2.extras.execute_values(
                k, """INSERT INTO branchops_branches (branch_code, branch_name, branch_type, region, core_alias, region_class)
                      VALUES %s
                      ON CONFLICT (branch_code) DO UPDATE SET
                        branch_name=EXCLUDED.branch_name,
                        branch_type=EXCLUDED.branch_type,
                        region=EXCLUDED.region,
                        region_class=EXCLUDED.region_class""",
                [(r["branch_code"], r["branch_name"], r["branch_type"],
                  r["region"], r.get("core_alias"), r.get("region_class"))
                 for r in rows])
    return len(rows)


def pelajari_alias_cabang():
    """
    Isi branchops_branches.core_alias dari data IT yang sudah masuk.
    Nama versi core banking ('CAB.JAKARTA-GREEN GARDEN') tidak akan pernah cocok
    dengan nama master, jadi dipetakan sekali lewat kode cabang.
    """
    return db.execute("""
        UPDATE branchops_branches b SET core_alias = s.alias
        FROM (SELECT DISTINCT ON (branch_code) branch_code, cabang_core AS alias
              FROM branchops_it_break WHERE cabang_core IS NOT NULL
              ORDER BY branch_code, id DESC) s
        WHERE b.branch_code = s.branch_code
          AND (b.core_alias IS DISTINCT FROM s.alias)""")


# --------------------------------------------------------------------------
# rekonsiliasi
# --------------------------------------------------------------------------
def jalankan_rekonsiliasi(toleransi=None):
    """
    Cocokkan branchops_it_break dengan branchops_pencairan lewat nomor rekening ternormalisasi.

    Hanya batch committed yang ikut. Pembanding di sisi cabang dibatasi pada
    'Dipercepat dari Jatuh Tempo', karena data IT memang hanya berisi break;
    pencairan sesuai jatuh tempo tidak akan pernah muncul di sana.

    Tindak lanjut yang sudah diisi manusia tidak ditimpa.
    """
    if toleransi is None:
        toleransi = db.get_settings().get("rekon_toleransi_rp", 1_000_000)

    db.execute("""
    WITH it AS (
      SELECT f.* FROM branchops_it_break f
      JOIN branchops_batches b ON b.id=f.batch_id AND b.status='committed'
      WHERE f.break_sejati AND f.rek_norm IS NOT NULL
    ), pc AS (
      SELECT DISTINCT ON (p.no_deposito_norm) p.*
      FROM branchops_pencairan p
      JOIN branchops_batches b ON b.id=p.batch_id AND b.status='committed'
      WHERE p.no_deposito_norm IS NOT NULL
        AND NOT p.dup_dikecualikan
        AND p.jenis_pencairan = 'Dipercepat dari Jatuh Tempo'
      ORDER BY p.no_deposito_norm, p.id
    ), gab AS (
      SELECT
        COALESCE(it.rek_norm, pc.no_deposito_norm)            AS rek_norm,
        it.id AS it_id, pc.id AS pencairan_id,
        COALESCE(it.branch_code, pc.branch_code)              AS branch_code,
        COALESCE(it.tgl_break, pc.tgl_pencairan)              AS tgl_acuan,
        it.nominal AS nominal_it, pc.nominal AS nominal_cabang,
        (it.nominal - pc.nominal)                             AS selisih,
        CASE
          WHEN pc.id IS NULL THEN 'Tidak dilaporkan cabang'
          WHEN it.id IS NULL THEN 'Tidak ada di data IT'
          WHEN pc.nominal IS NULL THEN 'Selisih material'
          WHEN abs(it.nominal - pc.nominal) <= %s THEN 'Cocok'
          ELSE 'Selisih material'
        END AS status
      FROM it FULL OUTER JOIN pc ON it.rek_norm = pc.no_deposito_norm
    )
    INSERT INTO branchops_rekon
      (rek_norm, it_id, pencairan_id, branch_code, tgl_acuan,
       nominal_it, nominal_cabang, selisih, status)
    SELECT rek_norm, it_id, pencairan_id, branch_code, tgl_acuan,
           nominal_it, nominal_cabang, selisih, status
    FROM gab
    ON CONFLICT (rek_norm, COALESCE(it_id,-1), COALESCE(pencairan_id,-1)) DO UPDATE
      SET nominal_it=EXCLUDED.nominal_it,
          nominal_cabang=EXCLUDED.nominal_cabang,
          selisih=EXCLUDED.selisih,
          status=EXCLUDED.status
    """, (toleransi,))

    # buang baris rekonsiliasi yang sumbernya sudah tidak aktif lagi
    db.execute("""DELETE FROM branchops_rekon r
                  WHERE (r.it_id IS NOT NULL AND NOT EXISTS (
                          SELECT 1 FROM branchops_it_break f
                          JOIN branchops_batches b ON b.id=f.batch_id AND b.status='committed'
                          WHERE f.id=r.it_id))
                     OR (r.pencairan_id IS NOT NULL AND NOT EXISTS (
                          SELECT 1 FROM branchops_pencairan p
                          JOIN branchops_batches b ON b.id=p.batch_id AND b.status='committed'
                          WHERE p.id=r.pencairan_id))""")

    return db.q1("""SELECT count(*) AS total,
                      count(*) FILTER (WHERE status='Cocok')                   AS cocok,
                      count(*) FILTER (WHERE status='Selisih material')        AS selisih,
                      count(*) FILTER (WHERE status='Tidak dilaporkan cabang') AS tak_lapor,
                      count(*) FILTER (WHERE status='Tidak ada di data IT')    AS cabang_only
                    FROM branchops_rekon""")
