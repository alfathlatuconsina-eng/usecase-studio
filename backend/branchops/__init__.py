# -*- coding: utf-8 -*-
"""
Branch Operations and Transactions Monitoring — modul kelima platform.

Dipasang dari app.py:

    import branchops
    app.register_blueprint(branchops.create_blueprint(require))
    branchops.ensure_schema()

Seluruh tabel modul ini ber-prefix branchops_ di database pmo yang sama,
sehingga tidak menyentuh tabel dashboard lain. Autentikasi memakai JWT
platform (module="branchops") lewat dekorator require() milik app.py.
"""
from __future__ import annotations

import csv
import datetime
import io
import os
import pathlib
import re
import tempfile

from flask import Blueprint, jsonify, request, send_file

from . import analytics, db, ingest, masking, privileges, scoping, storage

MAX_UPLOAD_MB = int(os.environ.get("BRANCHOPS_MAX_UPLOAD_MB", "25"))


def ensure_schema():
    """Terapkan schema.sql (idempoten: CREATE TABLE IF NOT EXISTS)."""
    sql = (pathlib.Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    with db.conn() as c:
        with c.cursor() as k:
            k.execute(sql)


def _email():
    return getattr(request, "user", {}).get("email", "?")


# -------------------------------------------------------------------------- #
#  Kolom TBO yang boleh diubah lewat layar Edit  (Agustus 2026)
#
#  DAFTAR PUTIH, bukan daftar hitam. Kolom baru yang ditambahkan nanti
#  otomatis TIDAK bisa diedit sampai sengaja dimasukkan ke sini. Dengan
#  daftar hitam, kolom baru diam-diam ikut bisa diubah tanpa ada yang
#  pernah memutuskan begitu.
#
#  Yang TIDAK ada di sini, dan alasannya:
#    branch_code, tgl_input, no_cif, no_rekening, nama_pemilik,
#    tgl_penempatan  -> identitas baris. Kalau bisa diubah, satu baris
#    bisa berpindah cabang atau berganti nasabah, dan rekonsiliasi
#    terhadap data IT kehilangan dasarnya.
#
#    batch_id, baris_no, no_rekening_norm, flags, created_at,
#    cif_gabungan  -> milik proses unggah, bukan manusia. no_rekening_norm
#    khususnya: kunci rekonsiliasi, diturunkan dari no_rekening.
#
#  nama_pemilik juga tersamar "***" di setiap respons, jadi layar edit
#  tidak akan pernah tahu nilai aslinya untuk dikirim balik.
# -------------------------------------------------------------------------- #
def _tgl(v):
    """String ISO / kosong -> date / None. Menolak yang bukan tanggal."""
    if v in (None, "", "-"):
        return None
    if isinstance(v, datetime.date):
        return v
    return datetime.date.fromisoformat(str(v).strip()[:10])


def _teks_opsional(v, maks):
    if v in (None, ""):
        return None
    s = str(v).strip()
    if len(s) > maks:
        raise ValueError(f"maksimal {maks} karakter")
    return s or None


def _angka(v):
    if v in (None, "", "-"):
        return None
    n = float(str(v).replace(",", "").strip())
    if n < 0:
        raise ValueError("tidak boleh negatif")
    return n


def _pilihan(v, sah):
    s = (str(v).strip() if v is not None else "")
    if s not in sah:
        raise ValueError("harus salah satu dari " + ", ".join(sah))
    return s


def _pilihan_opsional(v, sah):
    """Seperti _pilihan, tetapi kosong berarti "belum diisi" - bukan galat.

    Dipakai kolom yang memang boleh tidak terisi (mis. sumber dana asal
    pada baris lama yang datang dari Excel sebelum kolom ini ada)."""
    if v in (None, ""):
        return None
    return _pilihan(v, sah)


def _bool(v):
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("1", "true", "ya", "y")


_TBO_EDITABLE = {
    "tgl_jatuh_tempo":      _tgl,
    "target_pemenuhan_tbo": _tgl,
    "tgl_tbo_lengkap":      _tgl,
    "nominal":              _angka,
    "mata_uang":            lambda v: _teks_opsional(v, 8),
    # Ketiganya mendapat KOTAK PILIHAN di layar pada 16 Agu 2026, tetapi di
    # sini SENGAJA tetap teks bebas, bukan _pilihan_opsional. Alasannya
    # konkret, bukan kemalasan:
    #
    #   34 dari 176 baris branchops_tbo memuat nilai di luar daftar mana pun
    #   - 'Transfer' dan 'Deposito' pada jenis_rekening, teks dokumen pada
    #   jenis_setoran - karena berkas unggahannya bergeser satu kolom (batch
    #   26 dan 62). optJaga() di layar mempertahankan nilai itu dan
    #   mengirimkannya kembali apa adanya, persis supaya menyimpan tidak
    #   menimpanya diam-diam. Kalau di sini dipasang daftar putih, setiap
    #   penyuntingan apa pun pada baris tersebut - sekadar membetulkan satu
    #   tanggal - akan ditolak 400 sampai seseorang mengganti kolom yang
    #   sebenarnya tidak sedang ia urus. Itu terbaca sebagai aplikasi rusak,
    #   bukan sebagai aturan.
    #
    # Preseden yang sama sudah dipakai 15 Agu untuk jenis_pencairan dan
    # jenis_penarikan di _PENCAIRAN_EDITABLE: kotak pilihan di layar, teks
    # bebas di API. Yang menegakkan keseragaman adalah parser (_SERAGAM,
    # yang berlaku pada SEMUA baris yang masuk) dan kotak pilihan, bukan
    # penolakan di sini.
    #
    # Kalau suatu saat 34 baris itu sudah dibereskan dan daftar putih memang
    # diinginkan, pakai _pilihan_opsional dan periksa dulu tidak ada lagi
    # nilai di luar daftar - kalau tidak, sebagian baris menjadi tidak bisa
    # disunting sama sekali.
    "jenis_rekening":       lambda v: _teks_opsional(v, 60),
    "jenis_setoran":        lambda v: _teks_opsional(v, 60),
    "jenis_produk":         lambda v: _teks_opsional(v, 60),
    "tipe_pembukaan":       lambda v: _pilihan(v, ("Baru", "Penempatan Kembali")),
    "dokumen_tbo":          lambda v: _teks_opsional(v, 4000),
    "ada_tbo":              _bool,
    "status_tbo":           lambda v: _pilihan(v, ("Outstanding", "Lengkap", "Tidak ada TBO")),
    "nip_maker":            lambda v: _teks_opsional(v, 20),
    "nip_checker":          lambda v: _teks_opsional(v, 20),
    "nip_approver":         lambda v: _teks_opsional(v, 20),
    "keterangan":           lambda v: _teks_opsional(v, 4000),
}


def _teks(v):
    """Nilai apa pun -> teks untuk jejak audit. date/None ikut terbaca."""
    return None if v is None else str(v)


# -------------------------------------------------------------------------- #
#  Kolom PENCAIRAN yang boleh diubah lewat layar Edit  (Agustus 2026)
#
#  Daftar putih, alasan yang sama seperti _TBO_EDITABLE.
#
#  Yang TIDAK ada di sini, dan alasannya:
#    branch_code, tgl_input, no_cif, no_rekening, nama_pemilik,
#    tgl_pencairan  -> identitas baris, sesuai permintaan.
#
#    no_deposito_norm  -> KUNCI REKONSILIASI terhadap data IT. Diturunkan
#    dari no_deposito, tidak pernah diketik. Kalau no_deposito diubah,
#    endpoint menghitung ulang norm-nya sendiri (lihat tbo/pencairan edit),
#    supaya keduanya tidak pernah berbeda.
#
#    is_duplikat, dup_dikecualikan, skor_lengkap, checker_eq_approver,
#    flags, batch_id, baris_no, created_at  -> milik proses unggah.
#    Menyuntingnya berarti berbohong tentang apa yang dikirim cabang.
# -------------------------------------------------------------------------- #
_PENCAIRAN_EDITABLE = {
    "no_deposito":          lambda v: _teks_opsional(v, 40),
    "tgl_penempatan":       _tgl,
    "tgl_bilyet":           _tgl,
    "tenor_hari":           lambda v: None if v in (None, "", "-") else int(str(v).strip()),
    "nominal":              _angka,
    "jenis_pencairan":      lambda v: _teks_opsional(v, 60),
    "jenis_penarikan":      lambda v: _teks_opsional(v, 60),
    "data_tbo":             lambda v: _teks_opsional(v, 4000),
    "target_pemenuhan_tbo": _tgl,
    "tgl_tbo_lengkap":      _tgl,
    "status_tbo":           lambda v: _pilihan(v, ("Outstanding", "Lengkap", "Tidak ada TBO")),
    "arus_dana":            lambda v: _pilihan(v, ("Arus Keluar", "Rollover / DOC",
                                                   "Penempatan Kembali")),
    "nip_maker":            lambda v: _teks_opsional(v, 20),
    "nip_checker":          lambda v: _teks_opsional(v, 20),
    "nip_approver":         lambda v: _teks_opsional(v, 20),
    "catatan":              lambda v: _teks_opsional(v, 4000),
    # --- Sumber dana asal + tujuan transfer (15 Agu 2026) ---------------
    # Tetap DAFTAR PUTIH, alasan yang sama seperti sisanya (aturan 7):
    # kolom yang ditambahkan nanti tidak bisa disunting sampai ada yang
    # sengaja menuliskannya di sini.
    "sumber_produk":        lambda v: _pilihan_opsional(v, ("Tabungan", "Deposito")),
    "sumber_no_rek":        lambda v: _teks_opsional(v, 60),
    "tujuan_bank":          lambda v: _teks_opsional(v, 120),
    "tujuan_no_rek":        lambda v: _teks_opsional(v, 60),
    # CATATAN PENYAMARAN: ini nama pemilik rekening di bank lain, jadi
    # sebetulnya nama nasabah juga. Ia sengaja TIDAK didaftarkan di
    # masking.py, karena gunanya justru untuk menelusuri ke mana dana
    # dikirim - kalau tersamar, petugas yang mengetiknya tidak akan pernah
    # bisa membacanya kembali untuk diperiksa atau dikoreksi. Keputusan
    # sadar, bukan kelalaian; kalau berubah, tambahkan "tujuan_nama" ke
    # NAMA_NASABAH di masking.py dan kolom ini menjadi sekali-tulis.
    "tujuan_nama":          lambda v: _teks_opsional(v, 160),
}

# Aturan yang SAMA dengan _TIDAK_ADA di ingest.py dan dengan blok backfill
# di schema.sql. Kalau salah satu diubah, ubah ketiganya — kalau tidak,
# layar Edit, parser dan laporan akan tidak sepakat baris mana yang
# dianggap punya TBO.
_TIDAK_ADA_TBO = re.compile(r"^\s*(tidak\s*ada|tdk\s*ada|tidak\s*ad|-)\s*$", re.I)


def _punya_tbo(nilai):
    return bool(nilai) and not _TIDAK_ADA_TBO.match(str(nilai))


def _out(payload):
    """Satu-satunya pintu keluar data modul ini.

    Semua respons JSON lewat sini, sehingga nama nasabah pasti tersamar
    sebelum meninggalkan server — untuk semua peran, admin sekalipun.
    Jangan memanggil jsonify() langsung untuk data baris — pakai fungsi ini."""
    if masking.should_mask():
        payload = masking.apply(payload)
    return jsonify(payload)


def _install_json_provider(app):
    """psycopg2 mengembalikan Decimal/date/time yang tidak dikenal encoder bawaan
    Flask. Provider ini hanya MEMPERLUAS default() — endpoint modul lain yang
    mengembalikan dict berisi tipe primitif tidak terpengaruh sama sekali."""
    import decimal
    from flask.json.provider import DefaultJSONProvider

    if getattr(app, "_branchops_json", False):
        return

    class _P(DefaultJSONProvider):
        @staticmethod
        def default(o):
            if isinstance(o, decimal.Decimal):
                return float(o)
            if isinstance(o, datetime.time):
                return o.strftime("%H:%M:%S")
            if isinstance(o, (datetime.date, datetime.datetime)):
                return o.isoformat()
            if isinstance(o, datetime.timedelta):
                return o.total_seconds()
            if isinstance(o, set):
                return sorted(o)
            return DefaultJSONProvider.default(o)

    app.json = _P(app)
    app._branchops_json = True


def create_blueprint(require):
    """require = dekorator auth dari app.py; token wajib bermodul 'branchops'."""
    bp = Blueprint("branchops", __name__, url_prefix="/api/branchops")
    bp.record_once(lambda state: _install_json_provider(state.app))

    # ---------------------------------------------------------------- #
    # data dashboard
    # ---------------------------------------------------------------- #
    def _f():
        """Filter dari request + jatah wilayah dari sesi login.

        Perhatikan bedanya: kunci-kunci pertama diambil dari request.args
        dan memang boleh diatur pengguna. "_scope" TIDAK — nilainya selalu
        dari scoping.scope_aktif(), yang membacanya dari basis data
        berdasarkan siapa yang sedang masuk.

        Kalau "_scope" pernah diambil dari request.args, pengguna cukup
        menambah ?_scope=... di URL untuk melihat wilayah lain."""
        return {"tgl_awal": request.args.get("tgl_awal") or None,
                "tgl_akhir": request.args.get("tgl_akhir") or None,
                "branch_code": request.args.get("branch_code") or None,
                "branch_type": request.args.get("branch_type") or None,
                "status": request.args.get("status") or None,
                # Penyaring "Status TBO" di menu Pencairan (Agustus 2026).
                # Kunci SENDIRI, bukan "status" di atas: kunci itu dipakai
                # dash_rekon() untuk status rekonsiliasi, dan keduanya lewat
                # dict filter yang sama. Satu nama untuk dua arti berarti
                # pilihan di menu Pencairan diam-diam ikut menyaring
                # Dashboard 4.
                # Nilai di luar daftar sengaja jadi None (= semua), bukan
                # galat: ini penyaring TAMPILAN, bukan penyaring hak akses -
                # jatah cabang tetap dijaga "_scope" di bawah.
                "tbo_status": (request.args.get("tbo_status")
                               if request.args.get("tbo_status") in ("punya", "tanpa")
                               else None),
                "_scope": scoping.scope_aktif()}

    @bp.get("/dash/<int:no>")
    @require()
    def dash(no):
        # CELAH LAMA, SEKARANG DITUTUP: dulu rute ini hanya @require(), tanpa
        # pemeriksaan per-dashboard. Siapa pun yang sudah masuk bisa menarik
        # keempat dashboard walau tabnya disembunyikan di layar.
        if not privileges.boleh(f"d{no}"):
            return jsonify(error="Dashboard ini tidak tersedia untuk akun Anda"), 403
        f = _f()
        if no == 1:
            data = analytics.dash_it(f)
        elif no == 2:
            data = analytics.dash_pencairan(f, request.args.get("dup") == "1")
        elif no == 3:
            data = analytics.dash_tbo(f)
        elif no == 4:
            data = analytics.dash_rekon(f)
        else:
            return jsonify(error="Dashboard tidak dikenal"), 404
        data["settings"] = db.get_settings()
        return _out(data)

    @bp.get("/summary")
    @require()
    def summary():
        """Beranda. Sengaja TIDAK memakai @require_menu.

        Beranda tidak bisa dicabut (privileges.MENU_ALWAYS), jadi tidak ada
        kunci menu yang masuk akal untuk menutup rute ini. Pembatasannya ada
        di dalam: ringkasan() hanya membaca sumber yang boleh dilihat peran
        pemanggil. Tanpa argumen kedua ini, rute ini mengembalikan baris
        branchops_tbo dan branchops_pencairan kepada peran yang hak d3 dan
        d2-nya sudah dicabut."""
        # status_tbo hanya menyaring ISI TABEL "Seluruh TBO yang masih
        # terbuka". Angka spanduk di atasnya tetap tentang Outstanding -
        # lihat gabung_kpi vs gabung_baris di analytics.ringkasan().
        # Nilainya tidak pernah masuk SQL apa adanya: ringkasan()
        # memetakannya lewat daftar putih _STATUS_BERANDA, dan apa pun di
        # luar daftar jatuh ke Outstanding, bukan ke "semua".
        # branch_code MENYEMPITKAN di dalam jatah, tidak pernah melebarkan:
        # klausa jatah tetap terpasang di setiap cabang UNION dan berdiri
        # lebih dulu. Kode di luar jatah menghasilkan nol baris - bukan
        # kebocoran. Karena itu ia boleh datang dari request.args, tidak
        # seperti "_scope" yang tidak boleh (lihat _f() di atas).
        return _out(analytics.ringkasan(scoping.scope_aktif(),
                                        privileges.allowed_menus(),
                                        request.args.get("status_tbo"),
                                        request.args.get("branch_code")))

    @bp.get("/cabang")
    @require()
    def cabang():
        return _out({"cabang": analytics.daftar_cabang(scoping.scope_aktif()),
                     "periode": analytics.periode_tersedia(scoping.scope_aktif())})

    # ---------------------------------------------------------------- #
    # master data: wilayah + penetapan wilayah cabang  (tab Master Data)
    # ---------------------------------------------------------------- #
    @bp.get("/masterdata")
    @require("admin")
    @privileges.require_menu("masterdata")
    def masterdata_get():
        """Isi tab Master Data: daftar wilayah + seluruh cabang.

        Daftar cabang di sini sengaja TIDAK dibatasi jatah wilayah — hanya
        admin yang bisa membuka layar ini, dan admin memang harus melihat
        semua cabang untuk bisa menugaskan wilayahnya."""
        return _out({
            "wilayah": scoping.daftar_kelas_lengkap(),
            "cabang": db.q("""SELECT branch_code, branch_name, branch_type,
                                     region_class, is_active
                                FROM branchops_branches
                            ORDER BY branch_code"""),
            "kelas_semua": scoping.KELAS_SEMUA,
        })

    @bp.post("/masterdata/wilayah")
    @require("admin")
    @privileges.require_menu("masterdata")
    def wilayah_tambah():
        try:
            nilai = scoping.tambah_kelas((request.get_json(silent=True) or {}).get("nilai"))
        except ValueError as e:
            return jsonify(error=str(e)), 400
        db.audit(_email(), "wilayah_ditambah", "branchops_ref_values", None, {"nilai": nilai})
        return jsonify(ok=True, nilai=nilai)

    @bp.put("/masterdata/wilayah/<path:nama>")
    @require("admin")
    @privileges.require_menu("masterdata")
    def wilayah_ubah(nama):
        body = request.get_json(silent=True) or {}
        try:
            if "aktif" in body:
                aktif = scoping.set_aktif_kelas(nama, body["aktif"])
                db.audit(_email(), "wilayah_status_diubah", "branchops_ref_values",
                         None, {"nilai": nama, "aktif": aktif})
                return jsonify(ok=True, nilai=nama, aktif=aktif)
            baru = scoping.ubah_nama_kelas(nama, body.get("nilai"))
        except ValueError as e:
            return jsonify(error=str(e)), 400
        db.audit(_email(), "wilayah_diganti_nama", "branchops_ref_values",
                 None, {"lama": nama, "baru": baru})
        return jsonify(ok=True, nilai=baru)

    @bp.delete("/masterdata/wilayah/<path:nama>")
    @require("admin")
    @privileges.require_menu("masterdata")
    def wilayah_hapus(nama):
        try:
            scoping.hapus_kelas(nama)
        except ValueError as e:
            return jsonify(error=str(e)), 400
        db.audit(_email(), "wilayah_dihapus", "branchops_ref_values", None, {"nilai": nama})
        return jsonify(ok=True, nilai=nama)

    @bp.put("/masterdata/cabang/<kode>")
    @require("admin")
    @privileges.require_menu("masterdata")
    def cabang_ubah(kode):
        """Ubah satu cabang dari layar Master Data, tanpa mengunggah ulang Excel.

        Menerima region_class dan/atau branch_type. Kunci yang TIDAK dikirim
        tidak diubah — layar mengirim satu kolom per perubahan, jadi mengubah
        Tipe tidak boleh diam-diam mengosongkan Wilayah."""
        body = request.get_json(silent=True) or {}
        hasil = {"ok": True, "branch_code": kode}
        try:
            if "region_class" in body:
                nilai = scoping.set_wilayah_cabang(kode, body.get("region_class"))
                db.audit(_email(), "wilayah_cabang_diubah", "branchops_branches",
                         None, {"branch_code": kode, "region_class": nilai})
                hasil["region_class"] = nilai
            if "branch_type" in body:
                tipe = scoping.set_tipe_cabang(kode, body.get("branch_type"))
                db.audit(_email(), "tipe_cabang_diubah", "branchops_branches",
                         None, {"branch_code": kode, "branch_type": tipe})
                hasil["branch_type"] = tipe
        except ValueError as e:
            return jsonify(error=str(e)), 400
        if len(hasil) == 2:            # hanya ok + branch_code = tidak ada isi
            return jsonify(error="Tidak ada yang diubah"), 400
        return jsonify(**hasil)

    @bp.get("/region-class")
    @require()
    def region_class_list():
        """Daftar Region Class yang ada di master cabang.

        Dipakai layar admin (tab Pengguna) untuk mengisi kotak pilihan, dan
        oleh layar mana pun yang perlu menampilkan jatah wilayah sendiri.
        Bukan data nasabah, jadi aman dibuka untuk semua yang sudah masuk."""
        return _out({"kelas": scoping.pilihan_kelas(),
                     "kelas_semua": scoping.KELAS_SEMUA,
                     "milik_saya": scoping.kelas_pengguna(),
                     "lihat_semua": scoping.boleh_semua()})

    # ---------------------------------------------------------------- #
    # unggah
    # ---------------------------------------------------------------- #
    @bp.get("/batches")
    @require()
    @privileges.require_menu("upload")
    def batches():
        return _out({"batches": db.q(
            """SELECT id, jenis, nama_file, status, baris_total, baris_valid,
                      baris_ditolak, baris_warning, periode_awal, periode_akhir,
                      uploaded_at, uploaded_by AS oleh,
                      -- lingkup cabang: NULL = se-bank. Menentukan batch lama
                      -- mana yang tergantikan saat dikomit (commit_batch).
                      branch_code
               FROM branchops_batches ORDER BY id DESC LIMIT 50"""),
            "master_n": (db.q1("SELECT count(*) AS n FROM branchops_branches")
                         or {}).get("n", 0)})

    @bp.post("/upload")
    @require("admin", "editor")
    @privileges.require_menu("upload")
    def upload():
        jenis = request.form.get("jenis")
        if jenis not in ingest.PARSERS:
            return jsonify(error="Jenis berkas tidak dikenal"), 400
        f = request.files.get("file")
        if not f or not f.filename.lower().endswith((".xlsx", ".xlsm")):
            return jsonify(error="Harap unggah berkas .xlsx"), 400
        data = f.read()
        if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
            return jsonify(error=f"Berkas melebihi batas {MAX_UPLOAD_MB} MB"), 413

        sha = storage.sha256_file(data)
        kembar = storage.cek_duplikat_file(jenis, sha)
        branches = db.get_branches()
        if not branches:
            return jsonify(error="Master cabang belum diisi. Gunakan kotak 'Master cabang' "
                                 "di bagian atas halaman ini lebih dahulu.",
                           butuh_master=True), 400

        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        try:
            tmp.write(data); tmp.close()
            try:
                res = ingest.PARSERS[jenis](tmp.name, branches, db.get_settings())
            except Exception as e:                        # noqa: BLE001
                return jsonify(error=f"Berkas tidak bisa dibaca: {e}. Pastikan nama sheet "
                                     "dan susunan kolom sesuai template."), 400
            # ---------------------------------------------------------- #
            # JATAH CABANG — berlaku untuk ketiga jenis berkas.
            #
            # Peran editor hanya boleh mengunggah data cabang yang menjadi
            # jatahnya ("Jatah (Cabang yang dilihat)" di layar Pengguna).
            # Admin tidak dibatasi.
            #
            # SELURUH BERKAS DITOLAK kalau memuat satu saja cabang di luar
            # jatah, bukan disaring per baris. Dua alasan:
            #
            #  1. Menyaring diam-diam membuat orang mengira seluruh
            #     kiriman masuk, padahal hanya sebagiannya. Angka di layar
            #     lalu terlihat pasti padahal tidak lengkap.
            #  2. Batch yang tersaring tetap memakai PERIODE dari seluruh
            #     isi berkas (ParseResult.periode() membaca semua baris,
            #     termasuk yang ditolak). Batch separuh isi dengan periode
            #     penuh itulah yang kemudian membatalkan batch cabang lain
            #     pada periode sama - lihat storage.commit_batch().
            #
            # Diperiksa SEBELUM simpan_batch(): berkas yang ditolak tidak
            # boleh meninggalkan jejak apa pun di batches/stg/issues, atau
            # tab Unggah akan penuh draft yang tak pernah bisa dikomit.
            luar = scoping.kode_di_luar_jatah(
                [r.get("branch_code") for r in res.rows])
            if luar:
                return jsonify(
                    error=("Berkas memuat cabang di luar jatah Anda. "
                           "Anda hanya boleh mengunggah data cabang yang "
                           "menjadi jatah Anda."),
                    cabang_luar=luar[:20],
                    cabang_luar_total=len(luar)), 403

            batch_id = storage.simpan_batch(res, f.filename, len(data), sha, _email())
        finally:
            os.unlink(tmp.name)

        db.audit(_email(), "upload", "branchops_batches", batch_id,
                 {"jenis": jenis, "file": f.filename, "baris": len(res.rows),
                  "ditolak": res.baris_ditolak})
        return _out({
            "batch_id": batch_id, "jenis": jenis, "nama_file": f.filename,
            "total": len(res.rows), "valid": res.baris_valid,
            "ditolak": res.baris_ditolak,
            "warning": len({i.baris_no for i in res.warnings}),
            "file_kembar": (f"Berkas dengan isi identik sudah pernah dikomit "
                            f"(batch #{kembar['id']})." if kembar else None),
            # nilai sel mentah bisa berisi nama nasabah -> disamarkan oleh _out
            "issues": [{"baris": i.baris_no, "severity": i.severity,
                        "kode": i.kode, "pesan": i.pesan,
                        "kolom": i.kolom, "nilai": i.nilai}
                       for i in res.issues[:500]],
            "issue_total": len(res.issues)})

    @bp.post("/batch/<int:bid>/commit")
    @require("admin", "editor")
    @privileges.require_menu("upload")
    def commit(bid):
        b = storage.commit_batch(bid, _email())
        storage.pelajari_alias_cabang()
        rk = storage.jalankan_rekonsiliasi()
        db.audit(_email(), "commit", "branchops_batches", bid, {"jenis": b["jenis"]})
        return jsonify(ok=True, batch=b["id"], rekonsiliasi=rk)

    @bp.post("/batch/<int:bid>/batal")
    @require("admin", "editor")
    @privileges.require_menu("upload")
    def batal(bid):
        storage.batalkan_batch(bid)
        storage.jalankan_rekonsiliasi()
        db.audit(_email(), "batch_dibatalkan", "branchops_batches", bid)
        return jsonify(ok=True)

    @bp.delete("/batch/<int:bid>")
    @require("admin")
    @privileges.require_menu("upload")
    def hapus(bid):
        storage.hapus_batch(bid)
        storage.jalankan_rekonsiliasi()
        db.audit(_email(), "batch_dihapus", "branchops_batches", bid)
        return jsonify(ok=True)

    @bp.get("/batch/<int:bid>/issues.csv")
    @require()
    @privileges.require_menu("upload")
    def issues_csv(bid):
        # Ikut dibatasi jatah wilayah. Baris masalah menyimpan branch_code,
        # jadi bisa disaring. Akibatnya editor wilayah A yang mengunggah
        # berkas nasional hanya melihat baris bermasalah cabang wilayahnya —
        # itu memang yang diinginkan. Baris tanpa branch_code (kesalahan
        # tingkat berkas) ikut tersaring; sengaja gagal-tertutup.
        swh, sp = scoping.klausa(scoping.scope_aktif(), "br")
        rows = db.q(f"""SELECT i.baris_no, i.severity, i.kode, i.kolom,
                               i.nilai, i.pesan
                        FROM branchops_issues i
                        LEFT JOIN branchops_branches br
                               ON br.branch_code = i.branch_code
                        WHERE i.batch_id=%s{swh}
                        ORDER BY i.severity, i.baris_no""", [bid] + sp)
        buf = io.StringIO()
        w = csv.writer(buf, delimiter=";")
        w.writerow(["Baris Excel", "Tingkat", "Kode", "Kolom", "Nilai", "Pesan"])
        samar = masking.should_mask()
        for r in rows:
            # kolom "Nilai" berisi isi sel Excel apa adanya — bisa nama nasabah
            nilai = (masking.mask_issue_value(r["kolom"], r["nilai"])
                     if samar else r["nilai"])
            w.writerow([r["baris_no"], r["severity"], r["kode"],
                        r["kolom"], nilai, r["pesan"]])
        return send_file(io.BytesIO(buf.getvalue().encode("utf-8-sig")),
                         mimetype="text/csv", as_attachment=True,
                         download_name=f"validasi-batch-{bid}.csv")

    # Master cabang = ADMIN SAJA. Diubah Agustus 2026, sebelumnya
    # @require("admin", "editor").
    #
    # DUA lapis, dan keduanya perlu: @require menutup peran editor apa pun
    # yang tersimpan di branchops_role_menus, dan require_menu("master")
    # tetap dipasang supaya admin yang belum diberi kunci itu juga tertahan.
    # Menghapus salah satunya membuat lapis yang tersisa jadi satu-satunya
    # pertahanan - dan itu persis pola yang dilarang di privileges.py:
    # hak menu MEMPERSEMPIT, tidak pernah menggantikan pemeriksaan peran.
    @bp.post("/master")
    @require("admin")
    @privileges.require_menu("master")
    def master():
        f = request.files.get("file")
        if not f:
            return jsonify(error="Berkas master tidak ditemukan"), 400
        tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        try:
            tmp.write(f.read()); tmp.close()
            rows = ingest.parse_master(tmp.name)
            n = storage.upsert_branches(rows)
            # Wilayah baru di kolom D langsung didaftarkan ke master wilayah.
            # Tanpa ini, kolom D boleh diisi nama baru tapi nama itu tidak
            # akan pernah muncul di kotak pilihan tab Pengguna — dua jalur
            # input (Excel dan layar Master Data) jadi bertengkar.
            kelas_baru = scoping.daftarkan_kelas(
                [r.get("region_class") for r in rows])
        except Exception as e:                            # noqa: BLE001
            return jsonify(error=f"Master cabang gagal dibaca: {e}"), 400
        finally:
            os.unlink(tmp.name)
        db.audit(_email(), "master_cabang_diperbarui",
                 detail={"jumlah": n, "wilayah_baru": kelas_baru})
        return jsonify(ok=True, jumlah=n, wilayah_baru=kelas_baru)

    # ---------------------------------------------------------------- #
    # Ambil SATU baris (Agustus 2026)
    #
    # Dipakai layar Edit ketika dibuka dari Beranda. Daftar di Beranda
    # menggabungkan dua tabel, jadi hanya membawa kolom yang sama-sama
    # ada; formulir Edit butuh baris utuh.
    #
    # Keduanya lewat _out(), jadi nama nasabah tetap tersamar, dan
    # keduanya memeriksa jatah - tanpa itu, siapa pun bisa membaca baris
    # cabang mana pun hanya dengan menebak id.
    # ---------------------------------------------------------------- #
    def _satu(tabel, rid, menu):
        row = db.q1(f"SELECT * FROM {tabel} WHERE id=%s", (rid,))
        if not row:
            return jsonify(error="Baris tidak ditemukan"), 404
        if not scoping.boleh_cabang(row.get("branch_code")):
            return jsonify(error="Baris ini di luar jatah cabang Anda"), 403
        return _out(row)

    @bp.get("/tbo/<int:tid>")
    @require()
    @privileges.require_menu("d3")
    def tbo_satu(tid):
        return _satu("branchops_tbo", tid, "d3")

    @bp.get("/pencairan/<int:pid>")
    @require()
    @privileges.require_menu("d2")
    def pencairan_satu(pid):
        return _satu("branchops_pencairan", pid, "d2")

    # ---------------------------------------------------------------- #
    # tindakan
    # ---------------------------------------------------------------- #
    @bp.patch("/tbo/<int:tid>")
    @require("admin", "editor")
    @privileges.require_menu("d3")
    def tbo(tid):
        body = request.get_json(silent=True) or {}
        status = body.get("status_tbo")
        if status not in ("Outstanding", "Lengkap", "Tidak ada TBO"):
            return jsonify(error="Status TBO tidak dikenal"), 400
        tgl = body.get("tgl_tbo_lengkap") or (datetime.date.today().isoformat()
                                              if status == "Lengkap" else None)
        db.execute("""UPDATE branchops_tbo SET status_tbo=%s, tgl_tbo_lengkap=%s,
                        tbo_updated_by=%s, tbo_updated_at=now() WHERE id=%s""",
                   (status, tgl, _email(), tid))
        db.audit(_email(), "tbo_status", "branchops_tbo", tid, {"status": status})
        return jsonify(ok=True, status_tbo=status, tgl_tbo_lengkap=tgl)

    # ---------------------------------------------------------------- #
    # Edit rincian TBO (Agustus 2026)
    #
    # ENAM kolom sengaja TIDAK bisa diubah lewat layar ini:
    #   branch_code, tgl_input, no_cif, no_rekening, nama_pemilik,
    #   tgl_penempatan
    # Keenamnya adalah identitas baris - dari mana asalnya dan rekening
    # siapa. Membiarkannya diubah berarti satu baris bisa diam-diam
    # berpindah cabang atau berganti nasabah, dan rekonsiliasi terhadap
    # data IT tidak lagi bisa dipercaya.
    #
    # Penjagaannya lewat DAFTAR PUTIH (_TBO_EDITABLE), bukan daftar hitam.
    # Kolom baru yang ditambahkan nanti otomatis TIDAK bisa diedit sampai
    # sengaja dimasukkan ke daftar - arah gagal yang benar. Daftar hitam
    # akan membiarkan kolom baru bisa diubah tanpa ada yang memutuskan.
    # ---------------------------------------------------------------- #
    @bp.put("/tbo/<int:tid>")
    @require("admin", "editor")
    @privileges.require_menu("d3")
    def tbo_edit(tid):
        body = request.get_json(silent=True) or {}

        lama = db.q1("SELECT * FROM branchops_tbo WHERE id=%s", (tid,))
        if not lama:
            return jsonify(error="Baris TBO tidak ditemukan"), 404

        # Penjatahan berlaku juga di sini. Tanpa ini, seorang editor bisa
        # mengubah baris cabang yang tidak boleh ia LIHAT, cukup dengan
        # menebak id-nya. Admin tetap boleh semua (scope_aktif mengurus).
        if not scoping.boleh_cabang(lama.get("branch_code")):
            return jsonify(error="Baris ini di luar jatah cabang Anda"), 403

        set_bagian, nilai, berubah = [], [], {}
        for kol, ubah in _TBO_EDITABLE.items():
            if kol not in body:
                continue                      # tidak dikirim = jangan disentuh
            try:
                baru = ubah(body[kol])
            except (ValueError, TypeError) as e:
                return jsonify(error=f"Nilai {kol} tidak sah: {e}"), 400
            if baru != lama.get(kol):
                set_bagian.append(f"{kol}=%s")
                nilai.append(baru)
                berubah[kol] = {"dari": _teks(lama.get(kol)), "jadi": _teks(baru)}

        if not set_bagian:
            return jsonify(ok=True, tidak_berubah=True)

        # status_tbo dan tgl_tbo_lengkap harus bergerak bersama, sama
        # seperti di endpoint PATCH di atas. Kalau status jadi Lengkap
        # tanpa tanggal, aging dan laporan kehilangan acuan.
        if "status_tbo" in berubah and "tgl_tbo_lengkap" not in berubah:
            if berubah["status_tbo"]["jadi"] == "Lengkap" and not lama.get("tgl_tbo_lengkap"):
                set_bagian.append("tgl_tbo_lengkap=%s")
                nilai.append(datetime.date.today())
            elif berubah["status_tbo"]["jadi"] != "Lengkap":
                set_bagian.append("tgl_tbo_lengkap=NULL")

        set_bagian += ["tbo_updated_by=%s", "tbo_updated_at=now()"]
        nilai += [_email(), tid]
        db.execute(f"UPDATE branchops_tbo SET {', '.join(set_bagian)} WHERE id=%s",
                   tuple(nilai))

        db.audit(_email(), "tbo_diedit", "branchops_tbo", tid, berubah)
        return _out({"ok": True, "berubah": list(berubah)})

    # ---------------------------------------------------------------- #
    # Edit rincian PENCAIRAN (Agustus 2026)
    #
    # HANYA baris yang kolom "Data TBO"-nya terisi. Baris pencairan biasa
    # tidak bisa disunting sama sekali lewat sini — angka pencairan adalah
    # apa yang dilaporkan cabang, dan mengubahnya berarti dashboard tidak
    # lagi mencerminkan laporan itu. Yang boleh disunting adalah
    # pelacakan TBO-nya, dan rincian yang menempel pada baris itu.
    #
    # Enam kolom identitas tetap terkunci: branch_code, tgl_input,
    # no_cif, no_rekening, nama_pemilik, tgl_pencairan.
    # ---------------------------------------------------------------- #
    @bp.put("/pencairan/<int:pid>")
    @require("admin", "editor")
    @privileges.require_menu("d2")
    def pencairan_edit(pid):
        body = request.get_json(silent=True) or {}

        lama = db.q1("SELECT * FROM branchops_pencairan WHERE id=%s", (pid,))
        if not lama:
            return jsonify(error="Baris pencairan tidak ditemukan"), 404

        if not scoping.boleh_cabang(lama.get("branch_code")):
            return jsonify(error="Baris ini di luar jatah cabang Anda"), 403

        # Syarat utama: harus punya Data TBO. Diperiksa terhadap nilai yang
        # TERSIMPAN, bukan yang dikirim — kalau tidak, siapa pun bisa
        # membuka baris mana saja hanya dengan menyertakan data_tbo di
        # badan permintaan.
        if not _punya_tbo(lama.get("data_tbo")):
            return jsonify(error="Baris ini tidak punya Data TBO, jadi tidak bisa disunting. "
                                 "Hanya pencairan yang membawa Data TBO yang dilacak di sini."), 400

        set_bagian, nilai, berubah = [], [], {}
        for kol, ubah in _PENCAIRAN_EDITABLE.items():
            if kol not in body:
                continue
            try:
                baru = ubah(body[kol])
            except (ValueError, TypeError) as e:
                return jsonify(error=f"Nilai {kol} tidak sah: {e}"), 400
            if baru != lama.get(kol):
                set_bagian.append(f"{kol}=%s")
                nilai.append(baru)
                berubah[kol] = {"dari": _teks(lama.get(kol)), "jadi": _teks(baru)}

        if not set_bagian:
            return jsonify(ok=True, tidak_berubah=True)

        # no_deposito_norm ikut dihitung ulang. Kolom itu kunci
        # rekonsiliasi terhadap data IT; membiarkannya menunjuk nomor lama
        # membuat baris ini cocok dengan break yang salah, diam-diam.
        if "no_deposito" in berubah:
            set_bagian.append("no_deposito_norm=%s")
            nilai.append(ingest.digits(berubah["no_deposito"]["jadi"]))

        # Mengubah arus_dana lewat layar berarti keputusan MANUSIA, bukan
        # tebakan parser. Menandainya penting: analytics memakai
        # arus_manual untuk membedakan mana yang sudah ditinjau orang.
        if "arus_dana" in berubah:
            set_bagian.append("arus_manual=TRUE")
            set_bagian.append("arus_keyakinan=%s")
            nilai.append("Tinggi")

        # status_tbo dan tgl_tbo_lengkap bergerak bersama, sama seperti TBO.
        if "status_tbo" in berubah and "tgl_tbo_lengkap" not in berubah:
            if berubah["status_tbo"]["jadi"] == "Lengkap" and not lama.get("tgl_tbo_lengkap"):
                set_bagian.append("tgl_tbo_lengkap=%s")
                nilai.append(datetime.date.today())
            elif berubah["status_tbo"]["jadi"] != "Lengkap":
                set_bagian.append("tgl_tbo_lengkap=NULL")

        set_bagian += ["tbo_updated_by=%s", "tbo_updated_at=now()"]
        nilai += [_email(), pid]
        db.execute(f"UPDATE branchops_pencairan SET {', '.join(set_bagian)} WHERE id=%s",
                   tuple(nilai))

        db.audit(_email(), "pencairan_diedit", "branchops_pencairan", pid, berubah)
        return _out({"ok": True, "berubah": list(berubah)})

    @bp.patch("/rekon/<int:rid>")
    @require("admin", "editor")
    @privileges.require_menu("d4")
    def rekon(rid):
        body = request.get_json(silent=True) or {}
        tl = body.get("tindak_lanjut")
        if tl not in ("Belum ditinjau", "Sedang ditelusuri",
                      "Selesai - wajar", "Selesai - dikoreksi"):
            return jsonify(error="Status tindak lanjut tidak dikenal"), 400
        db.execute("""UPDATE branchops_rekon SET tindak_lanjut=%s, catatan_tl=%s,
                        updated_by=%s, updated_at=now() WHERE id=%s""",
                   (tl, body.get("catatan_tl"), _email(), rid))
        db.audit(_email(), "rekon_tindak_lanjut", "branchops_rekon", rid,
                 {"tindak_lanjut": tl})
        return jsonify(ok=True)

    @bp.patch("/pencairan/<int:pid>/arus")
    @require("admin", "editor")
    @privileges.require_menu("d2")
    def arus(pid):
        body = request.get_json(silent=True) or {}
        a = body.get("arus_dana")
        if a not in ("Arus Keluar", "Rollover / DOC", "Penempatan Kembali"):
            return jsonify(error="Kategori arus dana tidak dikenal"), 400
        db.execute("""UPDATE branchops_pencairan SET arus_dana=%s, arus_manual=TRUE,
                        arus_keyakinan='Tinggi' WHERE id=%s""", (a, pid))
        db.audit(_email(), "arus_dikoreksi", "branchops_pencairan", pid, {"arus_dana": a})
        return jsonify(ok=True)

    @bp.post("/rekonsiliasi/jalankan")
    @require("admin", "editor")
    @privileges.require_menu("d4")
    def rekon_run():
        rk = storage.jalankan_rekonsiliasi()
        db.audit(_email(), "rekonsiliasi_dijalankan", detail=rk)
        return jsonify(ok=True, **rk)

    # ---------------------------------------------------------------- #
    # pengaturan & audit modul
    # ---------------------------------------------------------------- #
    @bp.get("/settings")
    @require()
    def settings_get():
        return jsonify(settings=db.q(
            "SELECT kunci, nilai, deskripsi FROM branchops_settings ORDER BY kunci"))

    @bp.put("/settings")
    @require("admin")
    @privileges.require_menu("settings")
    def settings_put():
        body = request.get_json(silent=True) or {}
        for k, v in body.items():
            db.set_setting(k, v, _email())
        db.audit(_email(), "pengaturan_diubah", detail=body)
        storage.jalankan_rekonsiliasi()
        return jsonify(ok=True)

    @bp.get("/audit")
    @require("admin")
    @privileges.require_menu("audit")
    def audit_list():
        return _out({"log": db.q(
            "SELECT * FROM branchops_audit ORDER BY ts DESC LIMIT 300")})

    # ---------------------------------------------------------------- #
    # hak menu per pengguna (layar admin)
    # ---------------------------------------------------------------- #
    @bp.get("/menus")
    @require("admin")
    @privileges.require_menu("users")
    def menus_get():
        """Daftar kunci menu + pengaturan tersimpan tiap PERAN.

        Peran yang tidak muncul di 'tersimpan' berarti belum diatur, dan
        mendapat semua menu yang masuk akal untuknya."""
        return jsonify(
            kunci=privileges.MENU_KEYS,
            label=privileges.MENU_LABEL,
            peran=list(privileges.PERAN),
            # selalu = menu yang tidak bisa dicabut dari peran mana pun.
            # Layar menampilkannya tercentang-mati; kalau daftar ini tidak
            # dikirim (backend versi lama), layar kembali ke perilaku lama.
            selalu=sorted(privileges.MENU_ALWAYS),
            # batas = menu yang BOLEH dicentang untuk peran itu
            batas_peran={p: privileges.menus_for_role(p) for p in privileges.PERAN},
            # bawaan = keadaan bila peran belum pernah diatur. Sejak Agustus
            # 2026 "master" hanya untuk admin, sehingga bawaan dan batas
            # kebetulan sama untuk editor dan viewer; keduanya tetap dikirim
            # terpisah karena artinya memang berbeda.
            bawaan_peran={p: privileges.menus_default_for_role(p) for p in privileges.PERAN},
            tersimpan=privileges.peta_menus())

    @bp.put("/menus/<role>")
    @require("admin")
    @privileges.require_menu("users")
    def menus_put(role):
        body = request.get_json(silent=True) or {}
        menus = body.get("menus")
        if not isinstance(menus, list):
            return jsonify(error="Kolom 'menus' harus berupa daftar"), 400
        try:
            tersimpan = privileges.set_menus(role, menus, _email())
        except ValueError as e:
            return jsonify(error=str(e)), 400
        db.audit(_email(), "hak_menu_diubah", "peran", role, {"menus": tersimpan})
        return jsonify(ok=True, role=role, menus=tersimpan)

    @bp.delete("/menus/<role>")
    @require("admin")
    @privileges.require_menu("users")
    def menus_del(role):
        """Kembalikan sebuah peran ke bawaan."""
        if role not in privileges.PERAN:
            return jsonify(error="Peran tidak dikenal"), 400
        privileges.hapus_menus(role)
        db.audit(_email(), "hak_menu_direset", "peran", role)
        return jsonify(ok=True, role=role)

    return bp
