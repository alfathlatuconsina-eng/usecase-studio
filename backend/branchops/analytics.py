"""Agregasi untuk keempat dashboard.

Semua fungsi hanya membaca batch berstatus 'committed'.
Filter yang didukung: tgl_awal, tgl_akhir, branch_code, branch_type.
"""
from __future__ import annotations

from . import db, scoping

_AKTIF = "JOIN branchops_batches b ON b.id=%s.batch_id AND b.status='committed'"


def _filter(alias, tgl_kol, f):
    """Bangun potongan WHERE + parameter dari dict filter.

    Kunci "_scope" berbeda sifatnya dari kunci lain. Kunci lain berasal dari
    parameter request (tanggal, kode cabang, tipe cabang) dan memang boleh
    diatur pengguna. "_scope" adalah jatah wilayah pengguna, diisi HANYA oleh
    _f() di __init__.py dari sesi login — tidak pernah dari request.args.

    Bawaannya "" (tidak melihat apa pun), bukan None (melihat semua). Jadi
    kalau suatu saat ada pemanggil baru yang lupa mengisi "_scope", akibatnya
    tabel kosong — bukan kebocoran data ke seluruh cabang."""
    w, p = [], []
    if f.get("tgl_awal"):
        w.append(f"{alias}.{tgl_kol} >= %s"); p.append(f["tgl_awal"])
    if f.get("tgl_akhir"):
        w.append(f"{alias}.{tgl_kol} <= %s"); p.append(f["tgl_akhir"])
    if f.get("branch_code"):
        w.append(f"{alias}.branch_code = %s"); p.append(f["branch_code"])
    if f.get("branch_type"):
        w.append("br.branch_type = %s"); p.append(f["branch_type"])
    sql = (" AND " + " AND ".join(w)) if w else ""

    swh, sp = scoping.klausa(f.get("_scope", ""), "br")
    return sql + swh, p + sp


# Kolom tanggal yang benar-benar dipakai menyaring tiap dashboard.
# Harus sama dengan yang diteruskan ke _filter() di dash_* (dan, untuk
# rekon, dengan WHERE yang disusun sendiri di dash_rekon).
_KOLOM_TGL = {
    "it_break":  ("branchops_it_break",  "tgl_break"),
    "pencairan": ("branchops_pencairan", "tgl_input"),
    "tbo":       ("branchops_tbo",       "tgl_input"),
}


def periode_tersedia(scope=""):
    """Rentang tanggal yang tersedia — GLOBAL dan per dashboard.

    Diubah Agustus 2026. Sebelumnya satu nilai global saja, diambil dari
    branchops_batches.periode_awal/akhir, dan dipakai bersama oleh keempat
    menu. Dua akibatnya buruk:

      1. Satu batch dengan tanggal keliru menggeser "Dari tanggal" di
         SEMUA menu. Contoh nyata: batch 27 (Data Break Deposito) berisi
         tgl_break 1984-05-24, dan gara-gara itu menu Pencairan dan TBO
         pun terbuka dari 1984 — padahal data paling awal keduanya 2025
         dan 2026.
      2. periode_awal adalah ringkasan yang dihitung saat unggah. Kalau
         ringkasan itu salah, tidak ada yang mengoreksinya.

    Sekarang rentang diambil langsung dari TABEL FAKTA, dari kolom yang
    memang dipakai menyaring dashboard bersangkutan — jadi "tanggal paling
    awal" berarti benar-benar baris paling awal yang akan tampil.

    Ikut dibatasi jatah, dengan alasan yang sama seperti ringkasan():
    rentang yang tidak dibatasi membocorkan bahwa wilayah lain punya data
    di periode yang tidak boleh dilihat pengguna ini.

    Bentuk kembaliannya menjaga "awal"/"akhir" di tingkat atas supaya
    pemakai lama (garis "Data termuat" di Beranda) tidak berubah arti."""
    swh, sp = scoping.klausa(scope, "br")

    bagian, par = [], []
    for jenis, (tabel, kol) in _KOLOM_TGL.items():
        bagian.append(f"""
          SELECT '{jenis}' AS jenis, min(f.{kol}) AS awal, max(f.{kol}) AS akhir
            FROM {tabel} f
            JOIN branchops_batches b ON b.id=f.batch_id AND b.status='committed'
            JOIN branchops_branches br ON br.branch_code=f.branch_code
           WHERE 1=1{swh}""")
        par += sp

    # Dashboard 4 menyaring branchops_rekon.tgl_acuan, dan tabel itu tidak
    # punya batch_id — barisnya hasil rekonsiliasi, bukan hasil unggah.
    # Karena itu tidak ikut pola di atas dan ditulis terpisah.
    bagian.append(f"""
      SELECT 'rekon', min(r.tgl_acuan), max(r.tgl_acuan)
        FROM branchops_rekon r
        LEFT JOIN branchops_branches br ON br.branch_code=r.branch_code
       WHERE 1=1{swh}""")
    par += sp

    baris = db.q(" UNION ALL ".join(bagian), par)
    per = {r["jenis"]: {"awal": r["awal"], "akhir": r["akhir"]} for r in baris}

    semua_awal = [r["awal"] for r in baris if r["awal"]]
    semua_akhir = [r["akhir"] for r in baris if r["akhir"]]
    return {
        "awal": min(semua_awal) if semua_awal else None,
        "akhir": max(semua_akhir) if semua_akhir else None,
        "per_jenis": per,
    }


def daftar_cabang(scope=""):
    """Daftar cabang untuk isi kotak filter di layar.

    Ikut dibatasi jatah wilayah. Kalau tidak, pengguna wilayah A masih
    melihat nama seluruh cabang di daftar pilihan — dan bisa menebak
    keberadaan cabang yang seharusnya tidak ia ketahui."""
    swh, sp = scoping.klausa(scope, "br")
    return db.q(f"""SELECT br.branch_code, br.branch_name, br.branch_type,
                           br.region_class
                    FROM branchops_branches br WHERE 1=1{swh}
                    ORDER BY br.branch_name""", sp)


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
# Sebagian baris pencairan membawa kolom "Data TBO" dari cabang. Baris itu
# dilacak seperti pembukaan rekening ber-TBO: punya tenggat dan status.
#
# _PUNYA_TBO harus SEPAKAT dengan tiga tempat lain, atau layar Edit,
# parser dan laporan akan berbeda pendapat tentang baris mana yang punya
# TBO: _TIDAK_ADA di ingest.py, _TIDAK_ADA_TBO di __init__.py, dan blok
# backfill di schema.sql. Empat salinan aturan yang sama memang tidak
# ideal — tapi masing-masing hidup di lapisan berbeda (SQL, parser, API),
# dan menyatukannya berarti memanggil Python dari dalam query.
_PUNYA_TBO = r"""
        (f.data_tbo IS NOT NULL
         AND btrim(f.data_tbo) <> ''
         AND btrim(lower(f.data_tbo)) !~ '^(tidak\s*ada|tdk\s*ada|tidak\s*ad|-)$')"""

# Aturan hari terlambat sama dengan TBO: tanpa target -> NULL; sudah
# selesai -> NULL; target di depan -> 0; lewat -> selisih positif.
# Bedanya hanya satu, dan itu penting: baris yang TIDAK punya Data TBO
# tidak pernah terlambat, berapa pun tanggal targetnya.
_HARI_TERLAMBAT_PC = f"""
        CASE WHEN f.target_pemenuhan_tbo IS NOT NULL
              AND f.status_tbo = 'Outstanding'
              AND {_PUNYA_TBO}
             THEN GREATEST(CURRENT_DATE - f.target_pemenuhan_tbo, 0)
        END"""
# ==========================================================================
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
        -- Jumlah SEBENARNYA baris ber-Data TBO, tanpa dibatasi LIMIT.
        -- Dipakai layar untuk tahu apakah daftar rows_tbo terpotong: kalau
        -- rows_tbo.length kurang dari n_tbo, ada yang tidak tertampil dan
        -- layar harus mengatakannya, bukan menyebut angka yang terlihat
        -- pasti padahal sebagian.
        --
        -- JANGAN menulis tanda persen-s di komentar mana pun di dalam query.
        -- psycopg menghitung penanda parameter di SELURUH teks, termasuk di
        -- dalam komentar SQL, jadi satu saja di sini membuat jumlah penanda
        -- tidak lagi sama dengan jumlah parameter dan query gagal saat
        -- dijalankan. _PUNYA_TBO sendiri tidak memuat penanda parameter.
        count(*) FILTER (WHERE {_PUNYA_TBO})                AS n_tbo,
        count(DISTINCT f.branch_code)                       AS cabang,
        COALESCE(avg(f.skor_lengkap)*100,0)                 AS lengkap,
        COALESCE(percentile_cont(0.5) WITHIN GROUP (ORDER BY f.nominal),0) AS median
      {base}""", p)

    # cabang yang tidak mengirim laporan sama sekali pada periode terpilih
    #
    # Jatah wilayah/cabang HARUS menempel pada daftar cabang di query LUAR,
    # bukan ikut masuk ke dalam NOT EXISTS. Kalau ikut masuk, artinya
    # terbalik: untuk cabang di luar jatah, anak query tidak menemukan apa
    # pun, NOT EXISTS jadi benar, dan cabang itu justru MUNCUL di daftar
    # "tidak melapor". Itulah yang terjadi sampai Agustus 2026 — pengguna
    # wilayah A melihat seluruh nama cabang wilayah lain, dan semuanya
    # tertulis tidak melapor.
    #
    # Karena itu "_scope" sengaja dimatikan (None, bukan dihapus) untuk
    # potongan dalam. Menghapusnya tidak cukup: bawaan _filter() adalah ""
    # = "tidak melihat apa pun", yang membuat anak query tidak pernah cocok
    # dan SEMUA cabang terdaftar tidak melapor.
    f_dalam = {k: v for k, v in f.items() if k != "branch_code"}
    f_dalam["_scope"] = None
    wh2, p2 = _filter("f", "tgl_input", f_dalam)
    swh2, sp2 = scoping.klausa(f.get("_scope", ""), "br")
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
      WHERE br.is_active{swh2} AND NOT EXISTS (
        SELECT 1 FROM branchops_pencairan f {_AKTIF % 'f'}
        WHERE f.branch_code=br.branch_code {wh2})
      ORDER BY ada_di_it DESC, br.branch_code""", sp2 + p2)

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
                           f.no_cif, f.no_rekening,
                           f.tgl_penempatan, f.tgl_bilyet,
                           f.jenis_pencairan, f.jenis_penarikan, f.arus_dana, f.arus_keyakinan,
                           f.arus_manual, f.checker_eq_approver, f.is_duplikat, f.dup_dikecualikan,
                           f.skor_lengkap, f.catatan, f.flags,
                           f.data_tbo, f.target_pemenuhan_tbo, f.status_tbo, f.tgl_tbo_lengkap,
                           f.nip_maker, f.nip_checker, f.nip_approver,
                           {_HARI_TERLAMBAT_PC} AS hari_terlambat,
                           -- Satu tempat memutuskan baris mana yang "punya TBO",
                           -- supaya layar tidak menebak sendiri dengan aturan
                           -- yang lambat laun berbeda dari parser dan schema.
                           {_PUNYA_TBO} AS punya_tbo
                         {base} ORDER BY f.tgl_input, f.id LIMIT 2000""", p),
        # Baris ber-Data TBO, DISARING DI SINI dan bukan di layar.
        #
        # Kenapa query terpisah, bukan menyaring "rows" di JavaScript:
        # "rows" dipotong LIMIT 2000. Menyaring sesudah pemotongan berarti
        # layar hanya melihat baris ber-TBO yang kebetulan masuk 2000
        # pencairan paling awal menurut tgl_input. Kalau penyaring tanggal
        # mengenai lebih dari 2000 baris, baris ber-TBO sesudahnya HILANG
        # tanpa tanda apa pun - dan layar tetap menyebut angka yang pasti.
        # Dengan disaring lebih dulu, LIMIT berlaku atas baris ber-TBO,
        # bukan atas seluruh pencairan.
        #
        # "rows" TIDAK diubah: KPI harian, grafik jenis pencairan dan tabel
        # Rincian di layar dihitung darinya, dan semuanya harus tetap
        # menghitung SELURUH pencairan, bukan yang ber-TBO saja.
        "rows_tbo": db.q(f"""SELECT f.id, f.branch_code, br.branch_name, f.tgl_input, f.tgl_pencairan,
                           f.no_deposito, f.nama_pemilik, f.nominal, f.tenor_hari,
                           f.no_cif, f.no_rekening,
                           f.tgl_penempatan, f.tgl_bilyet,
                           f.jenis_pencairan, f.jenis_penarikan, f.arus_dana, f.arus_keyakinan,
                           f.arus_manual, f.checker_eq_approver, f.is_duplikat, f.dup_dikecualikan,
                           f.skor_lengkap, f.catatan, f.flags,
                           f.data_tbo, f.target_pemenuhan_tbo, f.status_tbo, f.tgl_tbo_lengkap,
                           f.nip_maker, f.nip_checker, f.nip_approver,
                           {_HARI_TERLAMBAT_PC} AS hari_terlambat,
                           TRUE AS punya_tbo
                         {base} AND {_PUNYA_TBO}
                         ORDER BY f.tgl_input, f.id LIMIT 2000""", p),
    }


# ==========================================================================
# DASHBOARD 3 - Pembukaan rekening TBO
# ==========================================================================
# Jumlah Hari Terlambat - SATU tempat, dipakai ulang di KPI dan detail.
#
# Aturannya, sesuai keputusan Agustus 2026:
#   - target kosong                  -> NULL (tampil "-"), bukan 0.
#     0 akan terbaca "tepat waktu", padahal artinya "belum ada tenggat".
#   - status Lengkap / Dikecualikan  -> NULL. TBO yang sudah selesai tidak
#     boleh terus menghitung keterlambatan hanya karena tanggalnya lewat.
#   - target masih di depan          -> 0, bukan angka minus.
#   - target sudah lewat             -> selisih hari, selalu positif.
#
# GREATEST(...,0) yang menjaga poin ketiga. Tanpa itu, rata-rata
# keterlambatan ikut ditarik turun oleh baris yang belum jatuh tempo.
_HARI_TERLAMBAT = """
        CASE WHEN f.target_pemenuhan_tbo IS NOT NULL
              AND f.status_tbo = 'Outstanding'
             THEN GREATEST(CURRENT_DATE - f.target_pemenuhan_tbo, 0)
        END"""


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
                     THEN CURRENT_DATE - f.tgl_input END),0)          AS aging_max,
        count(*) FILTER (WHERE f.target_pemenuhan_tbo IS NOT NULL)    AS ada_target,
        count(*) FILTER (WHERE {_HARI_TERLAMBAT} > 0)                 AS terlambat,
        COALESCE(max({_HARI_TERLAMBAT}), 0)                           AS terlambat_max,
        COALESCE(round(avg({_HARI_TERLAMBAT})
                       FILTER (WHERE {_HARI_TERLAMBAT} > 0)), 0)      AS terlambat_rata
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
                           f.jenis_rekening, f.jenis_setoran, f.jenis_produk, f.tipe_pembukaan,
                           f.dokumen_tbo, f.ada_tbo, f.status_tbo, f.tgl_tbo_lengkap,
                           f.tgl_penempatan, f.tgl_jatuh_tempo,
                           f.nip_maker, f.nip_checker, f.nip_approver,
                           f.target_pemenuhan_tbo,
                           {_HARI_TERLAMBAT} AS hari_terlambat,
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

    # Jatah wilayah/cabang. Dashboard ini menyusun WHERE-nya sendiri, tidak
    # lewat _filter(), sehingga sampai Agustus 2026 SATU-SATUNYA dashboard
    # yang tidak ikut dibatasi jatah — pengguna wilayah A melihat seluruh
    # baris rekonsiliasi. Ditambahkan di sini supaya keempat dashboard
    # berperilaku sama.
    #
    # Ketiga query di bawah memakai {wh} dan p pada posisi yang sama, jadi
    # cukup ditempelkan sekali di sini. Urutan penting: potongan scope
    # ditulis paling belakang, maka parameternya juga paling belakang.
    #
    # br disambung dengan LEFT JOIN, jadi baris rekonsiliasi yang kode
    # cabangnya tidak ada di master cabang punya br.region_class NULL dan
    # ikut tersaring — gagal-tertutup, sama seperti issues.csv.
    swh, sp = scoping.klausa(f.get("_scope", ""), "br")
    wh += swh
    p += sp

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
def ringkasan(scope="", menus=None):
    """Angka untuk tab Beranda.

    Ikut dibatasi jatah wilayah — kalau tidak, pengguna wilayah A melihat
    tabel kosong di dashboard tapi angka nasional di Beranda, yang
    membocorkan besaran data wilayah lain.

    DAN ikut dibatasi HAK MENU (Agustus 2026). `menus` adalah daftar hak
    menu pemanggil, apa adanya dari privileges.allowed_menus().

    Kenapa di sini dan bukan cukup dengan @require_menu di rutenya:
    Beranda selalu boleh dibuka (privileges.MENU_ALWAYS), jadi tidak ada
    satu kunci menu pun yang bisa menutup rute /summary secara utuh. Yang
    harus menyempit adalah ISINYA. Sebelum ini, /summary mengembalikan
    sampai 2000 baris asli dari branchops_tbo dan branchops_pencairan
    kepada siapa pun yang sudah masuk — termasuk peran yang hak d2 dan
    d3-nya sudah dicabut. Menyembunyikan kartunya di JavaScript tidak
    menutup itu: barisnya tetap terkirim dan terlihat di tab Network.

    menus=None berarti "tanpa batas menu". Dipakai pemanggil internal yang
    memang tidak mewakili seorang pengguna. JANGAN memanggilnya begitu
    dari sebuah rute HTTP.

    Jatah wilayah dan hak menu berjalan BERSAMA, bukan menggantikan satu
    sama lain: jatah memilih BARIS mana, hak menu memilih SUMBER mana."""
    swh, sp = scoping.klausa(scope, "br")

    def boleh(k):
        return menus is None or k in menus

    # TBO yang masih terbuka - menggantikan daftar "Unggahan terakhir" di
    # Beranda (Agustus 2026). Daftar unggahan sudah ada di tab Unggah;
    # yang perlu terlihat begitu dashboard dibuka adalah pekerjaan yang
    # belum selesai, bukan riwayat berkas.
    #
    # DUA SUMBER digabung (Agustus 2026): pembukaan rekening ber-TBO
    # (branchops_tbo) dan pencairan yang membawa Data TBO
    # (branchops_pencairan). Keduanya "TBO yang menggantung" bagi orang
    # yang mengejarnya, jadi memisahkannya di dua layar hanya membuat
    # satu daftar selalu terlupakan.
    #
    # Kolom "sumber" WAJIB ikut: layar memakainya untuk memilih endpoint
    # mana yang dipanggil saat tombol Ubah / Tandai lengkap ditekan.
    # Tanpa itu, id 7 dari dua tabel berbeda tidak bisa dibedakan.
    #
    # Query terpisah, TIDAK digabung ke "hitung" di bawah. Blok itu
    # memakai sp * 5 karena {swh} muncul lima kali; menambah {swh} ke
    # sana berarti harus ingat mengubah pengalinya juga, dan kalau lupa
    # parameternya bergeser diam-diam.
    #
    # branchops_pencairan TIDAK punya kolom mata_uang - seluruh baris
    # pencairan rupiah. 'IDR' ditulis tetap supaya bentuk kedua cabang
    # UNION sama persis; UNION menuntut jumlah dan tipe kolom identik.
    # SETIAP cabang UNION menulis nama kolomnya sendiri secara LENGKAP.
    # Biasanya PostgreSQL mengambil nama kolom dari cabang PERTAMA saja,
    # jadi dulu cabang pencairan boleh tanpa alias. Sejak hak menu bisa
    # membuang salah satu cabang, cabang mana pun bisa menjadi yang
    # pertama — kalau pencairan berdiri sendiri tanpa alias, kolomnya
    # bernama "?column?" dan g.sumber, g.mata_uang, g.dokumen serta
    # g.hari_terlambat lenyap tanpa satu pun galat sampai baris dibaca.
    lengan_tbo = f"""
      SELECT 'tbo'::text AS sumber, f.id AS id, f.branch_code AS branch_code,
             br.branch_name AS branch_name,
             f.tgl_input AS tgl_input, f.no_rekening AS no_rekening,
             f.nama_pemilik AS nama_pemilik, f.nominal AS nominal,
             f.mata_uang AS mata_uang, f.dokumen_tbo AS dokumen,
             f.target_pemenuhan_tbo AS target_pemenuhan_tbo,
             f.status_tbo AS status_tbo,
             {_HARI_TERLAMBAT} AS hari_terlambat,
             CURRENT_DATE - f.tgl_input AS aging
        FROM branchops_tbo f
        JOIN branchops_batches b ON b.id=f.batch_id AND b.status='committed'
        JOIN branchops_branches br ON br.branch_code=f.branch_code
       WHERE f.status_tbo='Outstanding' AND f.ada_tbo{swh}"""

    lengan_pencairan = f"""
      SELECT 'pencairan'::text AS sumber, f.id AS id,
             f.branch_code AS branch_code, br.branch_name AS branch_name,
             f.tgl_input AS tgl_input, f.no_rekening AS no_rekening,
             f.nama_pemilik AS nama_pemilik, f.nominal AS nominal,
             'IDR'::varchar AS mata_uang, f.data_tbo AS dokumen,
             f.target_pemenuhan_tbo AS target_pemenuhan_tbo,
             f.status_tbo AS status_tbo,
             {_HARI_TERLAMBAT_PC} AS hari_terlambat,
             CURRENT_DATE - f.tgl_input AS aging
        FROM branchops_pencairan f
        JOIN branchops_batches b ON b.id=f.batch_id AND b.status='committed'
        JOIN branchops_branches br ON br.branch_code=f.branch_code
       WHERE f.status_tbo='Outstanding' AND {_PUNYA_TBO}{swh}"""

    # Cabang UNION dipilih menurut hak menu: baris branchops_tbo milik
    # Dashboard 3, baris branchops_pencairan milik Dashboard 2. Peran yang
    # tidak berhak atas dashboardnya tidak boleh menerima barisnya lewat
    # pintu belakang Beranda.
    lengan = []
    if boleh("d3"):
        lengan.append(lengan_tbo)
    if boleh("d2"):
        lengan.append(lengan_pencairan)

    # {swh} muncul SEKALI di tiap cabang, jadi pengalinya = jumlah cabang
    # yang benar-benar dipakai. Dulu angka 2 ditulis tetap; sekarang
    # jumlahnya berubah-ubah, dan menghitungnya dari len() adalah satu-
    # satunya cara agar parameter tidak bergeser diam-diam.
    gabung_tbo = "\n      UNION ALL\n".join(lengan)
    sp_gab = sp * len(lengan)

    if not lengan:
        # Tidak berhak atas d2 maupun d3: tidak ada yang perlu ditanyakan
        # ke basis data. Bentuk yang dikembalikan tetap sama supaya layar
        # tidak perlu tahu bedanya — "tidak ada TBO terbuka" dan "tidak
        # boleh melihat TBO" sama-sama berarti tidak ada yang ditampilkan.
        tbo_kpi = {"total": 0, "dari_tbo": 0, "dari_pencairan": 0,
                   "lewat_target": 0, "tanpa_target": 0, "terlambat_max": 0,
                   "rp": 0, "cabang": 0}
        tbo_rows = []
    else:
        tbo_kpi = db.q1(f"""
      SELECT count(*) AS total,
             count(*) FILTER (WHERE g.sumber='tbo')            AS dari_tbo,
             count(*) FILTER (WHERE g.sumber='pencairan')      AS dari_pencairan,
             count(*) FILTER (WHERE g.hari_terlambat > 0)      AS lewat_target,
             count(*) FILTER (WHERE g.target_pemenuhan_tbo IS NULL) AS tanpa_target,
             COALESCE(max(g.hari_terlambat), 0)                AS terlambat_max,
             COALESCE(sum(g.nominal) FILTER (WHERE g.mata_uang='IDR'),0) AS rp,
             count(DISTINCT g.branch_code)                     AS cabang
      FROM ({gabung_tbo}) g""", sp_gab)

        # Yang paling terlambat lebih dulu; yang belum punya target
        # menyusul, diurutkan dari yang paling lama menggantung.
        # NULLS LAST penting: tanpa itu baris tanpa target justru
        # nangkring di puncak daftar dan menutupi yang benar-benar telat.
        #
        # LIMIT 2000 mengikuti batas yang sama dengan keempat dashboard.
        # "Tampilkan semua" dipenuhi dalam praktik; batas ini ada supaya
        # satu wilayah dengan puluhan ribu baris terbuka tidak membekukan
        # peramban. Layar memberi tahu bila daftarnya terpotong.
        tbo_rows = db.q(f"""
              SELECT * FROM ({gabung_tbo}) g
              ORDER BY g.hari_terlambat DESC NULLS LAST, g.tgl_input ASC
              LIMIT 2000""", sp_gab)

    hitung = db.q1(f"""
          SELECT (SELECT count(*) FROM branchops_it_break f
                    JOIN branchops_batches b ON b.id=f.batch_id AND b.status='committed'
                    JOIN branchops_branches br ON br.branch_code=f.branch_code
                   WHERE 1=1{swh}) AS it,
                 (SELECT count(*) FROM branchops_pencairan f
                    JOIN branchops_batches b ON b.id=f.batch_id AND b.status='committed'
                    JOIN branchops_branches br ON br.branch_code=f.branch_code
                   WHERE 1=1{swh}) AS pencairan,
                 (SELECT count(*) FROM branchops_tbo f
                    JOIN branchops_batches b ON b.id=f.batch_id AND b.status='committed'
                    JOIN branchops_branches br ON br.branch_code=f.branch_code
                   WHERE 1=1{swh}) AS tbo,
                 (SELECT count(*) FROM branchops_rekon r
                    LEFT JOIN branchops_branches br ON br.branch_code=r.branch_code
                   WHERE r.status<>'Cocok'{swh}) AS rekon_bermasalah,
                 (SELECT count(*) FROM branchops_branches br
                   WHERE br.is_active{swh}) AS cabang""",
                   sp * 5)

    # Angka kartu menu dibuang untuk dashboard yang tidak boleh dibuka.
    # Dihitung dulu, baru dibuang: query-nya satu blok dengan pengali
    # sp * 5 yang terikat pada lima {swh} di dalamnya. Membangunnya
    # sepotong-sepotong berarti pengali itu harus ikut dihitung ulang tiap
    # kali, dan itulah cara parameter bergeser tanpa ketahuan. Angkanya
    # tidak pernah meninggalkan proses ini, jadi tidak ada yang bocor.
    #
    # 'cabang' TIDAK ikut dibuang: Beranda memakainya untuk spanduk
    # "Master cabang belum diisi", yang harus tetap muncul bagi siapa pun.
    for kunci, menu in (("it", "d1"), ("pencairan", "d2"),
                        ("tbo", "d3"), ("rekon_bermasalah", "d4")):
        if not boleh(menu):
            hitung[kunci] = None

    return {
        "tbo_terbuka": {"kpi": tbo_kpi, "rows": tbo_rows},
        "hitung": hitung,
        # Daftar menu ikut dikirim supaya layar membangun kartunya dari
        # jawaban yang sama dengan yang menyaring angkanya. Kalau layar
        # memakai daftar lain (misalnya sisa /me yang sudah basi), kartu
        # dan angka bisa berbeda pendapat.
        "menus": None if menus is None else list(menus),
        "periode": periode_tersedia(scope),
    }
