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
        return _out(analytics.ringkasan(scoping.scope_aktif()))

    @bp.get("/cabang")
    @require()
    def cabang():
        return _out({"cabang": analytics.daftar_cabang(scoping.scope_aktif()),
                     "periode": analytics.periode_tersedia()})

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
    def cabang_set_wilayah(kode):
        """Ubah wilayah satu cabang, tanpa mengunggah ulang Excel."""
        try:
            nilai = scoping.set_wilayah_cabang(kode, (request.get_json(silent=True) or {}).get("region_class"))
        except ValueError as e:
            return jsonify(error=str(e)), 400
        db.audit(_email(), "wilayah_cabang_diubah", "branchops_branches",
                 None, {"branch_code": kode, "region_class": nilai})
        return jsonify(ok=True, branch_code=kode, region_class=nilai)

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
                      uploaded_at, uploaded_by AS oleh
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

    @bp.post("/master")
    @require("admin", "editor")
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
    # tindakan
    # ---------------------------------------------------------------- #
    @bp.patch("/tbo/<int:tid>")
    @require("admin", "editor")
    @privileges.require_menu("d3")
    def tbo(tid):
        body = request.get_json(silent=True) or {}
        status = body.get("status_tbo")
        if status not in ("Outstanding", "Lengkap", "Dikecualikan"):
            return jsonify(error="Status TBO tidak dikenal"), 400
        tgl = body.get("tgl_tbo_lengkap") or (datetime.date.today().isoformat()
                                              if status == "Lengkap" else None)
        db.execute("""UPDATE branchops_tbo SET status_tbo=%s, tgl_tbo_lengkap=%s,
                        tbo_updated_by=%s, tbo_updated_at=now() WHERE id=%s""",
                   (status, tgl, _email(), tid))
        db.audit(_email(), "tbo_status", "branchops_tbo", tid, {"status": status})
        return jsonify(ok=True, status_tbo=status, tgl_tbo_lengkap=tgl)

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
            # batas = menu yang BOLEH dicentang untuk peran itu
            batas_peran={p: privileges.menus_for_role(p) for p in privileges.PERAN},
            # bawaan = keadaan bila peran belum pernah diatur. Berbeda dari
            # batas: "master" boleh diberikan ke editor, tapi mati bawaannya.
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
