"""Agregasi untuk keempat dashboard.

Semua fungsi hanya membaca batch berstatus 'committed'.
Filter yang didukung: tgl_awal, tgl_akhir, branch_code, branch_type.
"""
from __future__ import annotations

from . import db

_AKTIF = "JOIN branchops_batches b ON b.id=%s.batch_id AND b.status='committed'"


def _filter(alias, tgl_kol, f):
    """Bangun potongan WHERE + parameter dari dict filter."""
    w, p = [], []
    if f.get("tgl_awal"):
        w.append(f"{alias}.{tgl_kol} >= %s"); p.append(f["tgl_awal"])
    if f.get("tgl_akhir"):
        w.append(f"{alias}.{tgl_kol} <= %s"); p.append(f["tgl_akhir"])
    if f.get("branch_code"):
        w.append(f"{alias}.branch_code = %s"); p.append(f["branch_code"])
    if f.get("branch_type"):
        w.append("br.branch_type = %s"); p.append(f["branch_type"])
    return (" AND " + " AND ".join(w)) if w else "", p


def periode_tersedia():
    return db.q1("""
      SELECT min(p) AS awal, max(p) AS akhir FROM (
        SELECT periode_awal p FROM branchops_batches WHERE status='committed'
        UNION ALL
        SELECT periode_akhir FROM branchops_batches WHERE status='committed') s""") or {}


def daftar_cabang():
    return db.q("""SELECT br.branch_code, br.branch_name, br.branch_type, br.region
                   FROM branchops_branches br ORDER BY br.branch_name""")


# ==========================================================================
# DASHBOARD 1 - Break deposito dari IT
# ==========================================================================
def dash_it(f):
    wh, p = _filter("f", "tgl_break", f)
    base = f"FROM branchops_it_break f {_AKTIF % 'f'} JOIN branchops_branches br ON br.branch_code=f.branch_code WHERE 1=1{wh}"

    kpi = db.q1(f"""
      SELECT count(*) AS n,
             COALESCE(sum(f.nominal),0)  AS rp,
             COALESCE(sum(f.penalti),0)  AS penalti,
             count(*) FILTER (WHERE f.penalti>0)     AS n_penalti,
             count(*) FILTER (WHERE f.break_sejati)  AS sejati,
             count(*) FILTER (WHERE f.break_sejati AND f.penalti=0) AS sejati_tanpa_penalti,
             COALESCE(sum(f.nominal) FILTER (WHERE f.break_sejati AND f.penalti=0),0) AS rp_tanpa_penalti,
             count(*) FILTER (WHERE f.luar_jam)      AS luar_jam,
             count(*) FILTER (WHERE f.via_perantara) AS perantara,
             count(DISTINCT f.branch_code)           AS cabang,
             count(DISTINCT f.nama_pemilik)          AS nasabah,
             COALESCE(percentile_cont(0.5) WITHIN GROUP (ORDER BY f.durasi_detik),0) AS dur_median,
             COALESCE(max(f.durasi_detik),0)  AS dur_max,
             CASE WHEN sum(f.nominal)>0
                  THEN sum(f.rate*f.nominal)/sum(f.nominal) ELSE 0 END AS rate_avg,
             min(f.rate) AS rate_min, max(f.rate) AS rate_max
      {base}""", p)

    return {
        "kpi": kpi,
        "per_tgl": db.q(f"""SELECT f.tgl_break AS tgl, count(*) AS n, sum(f.nominal) AS rp
                            {base} GROUP BY 1 ORDER BY 1""", p),
        "per_cabang": db.q(f"""SELECT f.branch_code, br.branch_name, br.branch_type,
                                 count(*) AS n, sum(f.nominal) AS rp, sum(f.penalti) AS penalti
                               {base} GROUP BY 1,2,3 ORDER BY rp DESC""", p),
        "per_jam": db.q(f"""SELECT extract(hour FROM f.waktu_awal)::int AS jam, count(*) AS n
                            {base} GROUP BY 1 ORDER BY 1""", p),
        "per_rate": db.q(f"""SELECT round(f.rate*100,2) AS rate, count(*) AS n, sum(f.nominal) AS rp
                             {base} GROUP BY 1 ORDER BY 1""", p),
        "top_nasabah": db.q(f"""SELECT f.nama_pemilik AS nama, count(*) AS n, sum(f.nominal) AS rp,
                                  bool_or(f.nama_terpotong) AS terpotong
                                {base} GROUP BY 1 ORDER BY rp DESC LIMIT 10""", p),
        "rows": db.q(f"""SELECT f.id, f.branch_code, br.branch_name, f.tgl_break, f.waktu_awal,
                           f.nama_pemilik, f.nama_terpotong, f.nominal, f.penalti, f.rate,
                           f.break_sejati, f.sisa_hari, f.durasi_detik, f.luar_jam,
                           f.rek_norm, f.flags,
                           r.status AS rekon, r.selisih AS rekon_selisih
                         FROM branchops_it_break f {_AKTIF % 'f'}
                         JOIN branchops_branches br ON br.branch_code=f.branch_code
                         LEFT JOIN branchops_rekon r ON r.it_id=f.id
                         WHERE 1=1{wh} ORDER BY f.tgl_break, f.waktu_awal LIMIT 2000""", p),
    }


# ==========================================================================
# DASHBOARD 2 - Pencairan deposito dari cabang
# ==========================================================================
def dash_pencairan(f, sertakan_dup=False):
    wh, p = _filter("f", "tgl_input", f)
    dup = "" if sertakan_dup else " AND NOT f.dup_dikecualikan"
    base = (f"FROM branchops_pencairan f {_AKTIF % 'f'} "
            f"JOIN branchops_branches br ON br.branch_code=f.branch_code WHERE 1=1{wh}{dup}")

    kpi = db.q1(f"""
      SELECT count(*) AS n, COALESCE(sum(f.nominal),0) AS rp_bruto,
        COALESCE(sum(f.nominal) FILTER (WHERE f.arus_dana='Arus Keluar'),0)        AS rp_keluar,
        COALESCE(sum(f.nominal) FILTER (WHERE f.arus_dana='Rollover / DOC'),0)     AS rp_rollover,
        COALESCE(sum(f.nominal) FILTER (WHERE f.arus_dana='Penempatan Kembali'),0) AS rp_kembali,
        count(*) FILTER (WHERE f.arus_dana='Arus Keluar')        AS n_keluar,
        count(*) FILTER (WHERE f.arus_dana='Rollover / DOC')     AS n_rollover,
        count(*) FILTER (WHERE f.arus_dana='Penempatan Kembali') AS n_kembali,
        count(*) FILTER (WHERE f.jenis_pencairan='Sesuai Jatuh Tempo')          AS sjt,
        count(*) FILTER (WHERE f.jenis_pencairan='Dipercepat dari Jatuh Tempo') AS dipercepat,
        count(*) FILTER (WHERE cardinality(f.flags)=0)      AS bersih,
        count(*) FILTER (WHERE f.checker_eq_approver)       AS ck_eq_ap,
        count(*) FILTER (WHERE 'Tanpa maker/checker/approver' = ANY(f.flags)) AS tanpa_nip,
        count(DISTINCT f.branch_code)                       AS cabang,
        COALESCE(avg(f.skor_lengkap)*100,0)                 AS lengkap,
        COALESCE(percentile_cont(0.5) WITHIN GROUP (ORDER BY f.nominal),0) AS median
      {base}""", p)

    # cabang yang tidak mengirim laporan sama sekali pada periode terpilih
    wh2, p2 = _filter("f", "tgl_input", {k: v for k, v in f.items() if k != "branch_code"})
    tak_lapor = db.q(f"""
      SELECT br.branch_code, br.branch_name, br.branch_type,
             EXISTS (SELECT 1 FROM branchops_it_break i {_AKTIF % 'i'}
                     WHERE i.branch_code=br.branch_code) AS ada_di_it,
             -- pernah mengirim, tapi seluruh barisnya ditolak validasi
             EXISTS (SELECT 1 FROM branchops_issues v
                     JOIN branchops_batches b2 ON b2.id=v.batch_id
                        AND b2.status='committed' AND b2.jenis='pencairan'
                     WHERE v.branch_code=br.branch_code AND v.severity='error') AS kiriman_ditolak
      FROM branchops_branches br
      WHERE br.is_active AND NOT EXISTS (
        SELECT 1 FROM branchops_pencairan f {_AKTIF % 'f'}
        WHERE f.branch_code=br.branch_code {wh2})
      ORDER BY ada_di_it DESC, br.branch_code""", p2)

    return {
        "kpi": kpi,
        "tak_lapor": tak_lapor,
        "per_tgl": db.q(f"""SELECT f.tgl_input AS tgl, count(*) AS n, sum(f.nominal) AS rp,
                              COALESCE(sum(f.nominal) FILTER (WHERE f.arus_dana='Arus Keluar'),0) AS rp_keluar
                            {base} GROUP BY 1 ORDER BY 1""", p),
        "per_cabang": db.q(f"""SELECT f.branch_code, br.branch_name, br.branch_type, count(*) AS n,
                                 sum(f.nominal) AS rp,
                                 COALESCE(sum(f.nominal) FILTER (WHERE f.arus_dana='Arus Keluar'),0) AS rp_keluar,
                                 avg(f.skor_lengkap)*100 AS lengkap,
                                 count(*) FILTER (WHERE 'Tanpa maker/checker/approver' = ANY(f.flags)) AS tanpa_nip
                               {base} GROUP BY 1,2,3 ORDER BY rp DESC""", p),
        "per_arus": db.q(f"""SELECT f.arus_dana, count(*) AS n, sum(f.nominal) AS rp
                             {base} GROUP BY 1""", p),
        "rows": db.q(f"""SELECT f.id, f.branch_code, br.branch_name, f.tgl_input, f.tgl_pencairan,
                           f.no_deposito, f.nama_pemilik, f.nominal, f.tenor_hari,
                           f.jenis_pencairan, f.jenis_penarikan, f.arus_dana, f.arus_keyakinan,
                           f.arus_manual, f.checker_eq_approver, f.is_duplikat, f.dup_dikecualikan,
                           f.skor_lengkap, f.catatan, f.flags
                         {base} ORDER BY f.tgl_input, f.id LIMIT 2000""", p),
    }


# ==========================================================================
# DASHBOARD 3 - Pembukaan rekening TBO
# ==========================================================================
def dash_tbo(f):
    wh, p = _filter("f", "tgl_input", f)
    base = (f"FROM branchops_tbo f {_AKTIF % 'f'} "
            f"JOIN branchops_branches br ON br.branch_code=f.branch_code WHERE 1=1{wh}")

    kpi = db.q1(f"""
      SELECT count(*) AS n,
        COALESCE(sum(f.nominal) FILTER (WHERE f.mata_uang='IDR'),0) AS rp,
        count(*) FILTER (WHERE f.tipe_pembukaan='Baru')               AS baru,
        count(*) FILTER (WHERE f.tipe_pembukaan='Penempatan Kembali') AS kembali,
        count(*) FILTER (WHERE f.jenis_rekening='Perorangan')         AS perorangan,
        count(*) FILTER (WHERE f.jenis_rekening<>'Perorangan')        AS perusahaan,
        count(*) FILTER (WHERE f.ada_tbo)                             AS dengan_tbo,
        count(*) FILTER (WHERE f.status_tbo='Outstanding')            AS outstanding,
        count(*) FILTER (WHERE f.status_tbo='Lengkap')                AS lengkap,
        count(DISTINCT f.branch_code)                                 AS cabang,
        COALESCE(avg(CASE WHEN f.status_tbo='Outstanding'
                     THEN CURRENT_DATE - f.tgl_input END),0)          AS aging_rata,
        COALESCE(max(CASE WHEN f.status_tbo='Outstanding'
                     THEN CURRENT_DATE - f.tgl_input END),0)          AS aging_max
      {base}""", p)

    aging = db.q(f"""
      SELECT CASE
               WHEN CURRENT_DATE - f.tgl_input <= 7  THEN '0-7 hari'
               WHEN CURRENT_DATE - f.tgl_input <= 14 THEN '8-14 hari'
               WHEN CURRENT_DATE - f.tgl_input <= 30 THEN '15-30 hari'
               ELSE '>30 hari' END AS bucket,
             count(*) AS n, COALESCE(sum(f.nominal),0) AS rp
      {base} AND f.status_tbo='Outstanding' AND f.ada_tbo
      GROUP BY 1
      ORDER BY min(CURRENT_DATE - f.tgl_input)""", p)

    return {
        "kpi": kpi,
        "aging": aging,
        "per_cabang": db.q(f"""SELECT f.branch_code, br.branch_name, count(*) AS n,
                                 COALESCE(sum(f.nominal) FILTER (WHERE f.mata_uang='IDR'),0) AS rp,
                                 count(*) FILTER (WHERE f.status_tbo='Outstanding') AS outstanding
                               {base} GROUP BY 1,2 ORDER BY n DESC""", p),
        "per_produk": db.q(f"""SELECT COALESCE(f.jenis_produk,'(tidak dikenali)') AS produk,
                                 count(*) AS n {base} GROUP BY 1 ORDER BY n DESC""", p),
        "rows": db.q(f"""SELECT f.id, f.branch_code, br.branch_name, f.tgl_input, f.no_cif,
                           f.cif_gabungan, f.no_rekening, f.nama_pemilik, f.nominal, f.mata_uang,
                           f.jenis_rekening, f.jenis_produk, f.tipe_pembukaan, f.dokumen_tbo,
                           f.ada_tbo, f.status_tbo, f.tgl_tbo_lengkap,
                           CASE WHEN f.status_tbo='Outstanding'
                                THEN CURRENT_DATE - f.tgl_input END AS aging,
                           f.keterangan, f.flags
                         {base} ORDER BY f.status_tbo, f.tgl_input LIMIT 2000""", p),
    }


# ==========================================================================
# DASHBOARD 4 - Rekonsiliasi
# ==========================================================================
def dash_rekon(f):
    w, p = [], []
    if f.get("tgl_awal"):
        w.append("r.tgl_acuan >= %s"); p.append(f["tgl_awal"])
    if f.get("tgl_akhir"):
        w.append("r.tgl_acuan <= %s"); p.append(f["tgl_akhir"])
    if f.get("branch_code"):
        w.append("r.branch_code = %s"); p.append(f["branch_code"])
    if f.get("status"):
        w.append("r.status = %s"); p.append(f["status"])
    wh = (" AND " + " AND ".join(w)) if w else ""
    base = f"FROM branchops_rekon r LEFT JOIN branchops_branches br ON br.branch_code=r.branch_code WHERE 1=1{wh}"

    return {
        "kpi": db.q1(f"""
          SELECT count(*) AS total,
            count(*) FILTER (WHERE r.status='Cocok')                   AS cocok,
            count(*) FILTER (WHERE r.status='Selisih material')        AS selisih,
            count(*) FILTER (WHERE r.status='Tidak dilaporkan cabang') AS tak_lapor,
            count(*) FILTER (WHERE r.status='Tidak ada di data IT')    AS cabang_only,
            COALESCE(sum(r.nominal_it) FILTER (WHERE r.status='Tidak dilaporkan cabang'),0) AS rp_tak_lapor,
            COALESCE(sum(abs(r.selisih)) FILTER (WHERE r.status='Selisih material'),0)      AS rp_selisih,
            count(*) FILTER (WHERE r.tindak_lanjut='Belum ditinjau')   AS belum_ditinjau
          {base}""", p),
        "per_cabang": db.q(f"""SELECT r.branch_code, br.branch_name, count(*) AS n,
                                 count(*) FILTER (WHERE r.status='Cocok') AS cocok,
                                 count(*) FILTER (WHERE r.status<>'Cocok') AS bermasalah,
                                 COALESCE(sum(abs(r.selisih)) FILTER (WHERE r.status='Selisih material'),0) AS rp_selisih
                               {base} GROUP BY 1,2 ORDER BY bermasalah DESC, n DESC""", p),
        "rows": db.q(f"""SELECT r.id, r.rek_norm, r.branch_code, br.branch_name, r.tgl_acuan,
                           r.nominal_it, r.nominal_cabang, r.selisih, r.status,
                           r.tindak_lanjut, r.catatan_tl,
                           i.nama_pemilik AS nasabah_it, p.nama_pemilik AS nasabah_cabang,
                           p.catatan AS catatan_cabang
                         FROM branchops_rekon r
                         LEFT JOIN branchops_branches br ON br.branch_code=r.branch_code
                         LEFT JOIN branchops_it_break i  ON i.id=r.it_id
                         LEFT JOIN branchops_pencairan p ON p.id=r.pencairan_id
                         WHERE 1=1{wh}
                         ORDER BY CASE r.status WHEN 'Selisih material' THEN 1
                                                WHEN 'Tidak dilaporkan cabang' THEN 2
                                                WHEN 'Tidak ada di data IT' THEN 3 ELSE 4 END,
                                  abs(COALESCE(r.selisih,0)) DESC NULLS LAST,
                                  r.nominal_it DESC NULLS LAST
                         LIMIT 2000""", p),
    }


# ==========================================================================
# beranda
# ==========================================================================
def ringkasan():
    return {
        "batch": db.q("""SELECT b.id, b.jenis, b.nama_file, b.status, b.baris_total, b.baris_valid,
                           b.baris_ditolak, b.baris_warning, b.periode_awal, b.periode_akhir,
                           b.uploaded_at, b.uploaded_by AS oleh
                         FROM branchops_batches b
                         ORDER BY b.id DESC LIMIT 10"""),
        "hitung": db.q1("""
          SELECT (SELECT count(*) FROM branchops_it_break f JOIN branchops_batches b ON b.id=f.batch_id
                    AND b.status='committed') AS it,
                 (SELECT count(*) FROM branchops_pencairan f JOIN branchops_batches b ON b.id=f.batch_id
                    AND b.status='committed') AS pencairan,
                 (SELECT count(*) FROM branchops_tbo f JOIN branchops_batches b ON b.id=f.batch_id
                    AND b.status='committed') AS tbo,
                 (SELECT count(*) FROM branchops_rekon WHERE status<>'Cocok') AS rekon_bermasalah,
                 (SELECT count(*) FROM branchops_branches WHERE is_active) AS cabang"""),
        "periode": periode_tersedia(),
    }
