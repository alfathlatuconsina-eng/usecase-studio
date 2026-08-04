# -*- coding: utf-8 -*-
"""
Jatah wilayah per PENGGUNA (Region Class) — modul Branch Operations.

BEDANYA DENGAN privileges.py
----------------------------
privileges.py membatasi MENU MANA yang boleh dibuka, dan melekat pada PERAN.
Berkas ini membatasi BARIS DATA MANA yang boleh dilihat, dan melekat pada
PENGGUNA perorangan. Keduanya berjalan bersamaan dan tidak saling menggantikan:

    peran      -> boleh melakukan apa      (@require)
    hak menu   -> boleh membuka layar apa  (@privileges.require_menu)
    wilayah    -> boleh melihat baris apa  (berkas ini)

KENAPA DI BACKEND, DAN KENAPA BUKAN DARI REQUEST
------------------------------------------------
Batasan ini TIDAK BOLEH datang dari parameter request. Kalau datang dari sana,
pengguna cukup mengubah URL (?region_class=...) untuk melihat cabang lain.
Karena itu nilainya selalu dibaca dari sesi login + basis data, lalu
disuntikkan oleh _f() di __init__.py ke dalam dict filter dengan kunci
"_scope" yang TIDAK pernah dibaca dari request.args.

Sama seperti hak menu, nilainya juga TIDAK disimpan di JWT dan TIDAK di
localStorage — supaya pencabutan jatah wilayah berlaku pada request
berikutnya, bukan pada login berikutnya.

ATURAN
------
1. Peran 'admin' SELALU melihat semua cabang. Disengaja: admin yang tidak
   bisa melihat seluruh data tidak akan bisa memeriksa atau memperbaiki
   jatah wilayah pengguna lain.
2. Kelas khusus 'SEMUA' berarti melihat seluruh cabang. Ini yang diberikan
   kepada pengguna kantor pusat.
3. Pengguna yang jatah wilayahnya KOSONG tidak melihat baris apa pun.
   Gagal-tertutup: data hanya terlihat setelah sengaja diberikan.
   Pengguna yang sudah ada sebelum fitur ini dipasang otomatis diberi
   kelas 'SEMUA' oleh migrasi di schema.sql, jadi tidak ada yang terkunci.
4. Cabang yang region_class-nya masih kosong hanya terlihat oleh admin dan
   kelas 'SEMUA'. Ini disengaja: cabang yang belum dikelompokkan tidak boleh
   bocor ke pengguna wilayah mana pun hanya karena masternya belum lengkap.
"""
from __future__ import annotations

from flask import request

from . import db

# Kelas khusus: melihat seluruh cabang. Bukan nilai wilayah sungguhan,
# jadi jangan dipakai sebagai isi kolom region_class di Excel master.
KELAS_SEMUA = "SEMUA"


def _user():
    return getattr(request, "user", {}) or {}


def _role():
    return _user().get("role")


def _email():
    return _user().get("email")


def kelas_pengguna(email=None):
    """Region Class milik pengguna yang sedang masuk.

    Dibaca dari basis data setiap kali, BUKAN dari JWT — supaya perubahan
    jatah wilayah berlaku pada request berikutnya."""
    email = email or _email()
    if not email:
        return None
    baris = db.q("SELECT region_class FROM branchops_users WHERE email=%s",
                 (email,))
    if not baris:
        return None
    return (baris[0].get("region_class") or "").strip() or None


def boleh_semua(role=None, kelas=None):
    """True bila pengguna ini boleh melihat SEMUA cabang."""
    role = role if role is not None else _role()
    if role == "admin":
        return True
    kelas = kelas if kelas is not None else kelas_pengguna()
    return kelas == KELAS_SEMUA


def scope_aktif():
    """Nilai yang disuntikkan ke dict filter sebagai kunci "_scope".

    Mengembalikan salah satu dari:
        None          -> tanpa batasan, lihat semua cabang
        "<kelas>"     -> hanya cabang dengan region_class itu
        ""            -> tidak melihat apa pun (belum dijatah wilayah)

    Perhatikan bedanya None dan "" — keduanya "kosong" dalam arti Python,
    jadi pemeriksaannya harus pakai `is None`, bukan `if not scope`."""
    if boleh_semua():
        return None
    return kelas_pengguna() or ""


def klausa(scope, alias="br"):
    """Potongan WHERE + parameter untuk sebuah nilai scope.

    Dipakai analytics.py. Dipisah dari scope_aktif() supaya analytics.py
    tetap bisa diuji tanpa perlu ada request Flask yang aktif."""
    if scope is None:
        return "", []
    if scope == "":
        # Tidak dijatah wilayah -> tidak ada baris yang cocok.
        return " AND FALSE", []
    return f" AND {alias}.region_class = %s", [scope]


# --------------------------------------------------------------------- #
#  Daftar wilayah (master)
#
#  Rumahnya branchops_ref_values dengan kategori 'wilayah'. Tabel itu sudah
#  ada sejak awal (kategori, nilai, urutan, aktif) tapi belum pernah dipakai
#  kode mana pun, dan bentuknya persis yang dibutuhkan di sini.
#
#  Kenapa punya daftar sendiri, bukan sekadar DISTINCT dari master cabang:
#  supaya sebuah wilayah bisa DIBUAT LEBIH DULU, sebelum ada satu pun cabang
#  yang memakainya. Dengan DISTINCT, wilayah baru tidak akan pernah muncul
#  di layar sampai ada cabang yang terlanjur diberi nama itu.
# --------------------------------------------------------------------- #
KATEGORI = "wilayah"


def daftar_kelas():
    """Wilayah AKTIF — dipakai untuk memeriksa jatah pengguna."""
    baris = db.q("""SELECT nilai FROM branchops_ref_values
                     WHERE kategori=%s AND aktif
                  ORDER BY urutan, nilai""", (KATEGORI,))
    return [b["nilai"] for b in baris]


def daftar_kelas_lengkap():
    """Semua wilayah + berapa cabang dan pengguna yang memakainya.

    Dipakai layar Master Data. Jumlah pemakai ditampilkan supaya admin tahu
    akibatnya sebelum menonaktifkan atau menghapus."""
    return db.q("""
      SELECT r.nilai, r.urutan, r.aktif,
             (SELECT count(*) FROM branchops_branches b
               WHERE b.region_class = r.nilai) AS jml_cabang,
             (SELECT count(*) FROM branchops_users u
               WHERE u.region_class = r.nilai) AS jml_pengguna
        FROM branchops_ref_values r
       WHERE r.kategori=%s
    ORDER BY r.urutan, r.nilai""", (KATEGORI,))


def daftarkan_kelas(nilai_list):
    """Daftarkan wilayah baru yang muncul dari unggahan Excel master.

    Tanpa ini, kolom D boleh diisi wilayah baru tapi wilayah itu tidak akan
    pernah muncul di kotak pilihan — dua jalur input jadi bertengkar.
    Wilayah yang sudah ada tidak diubah (urutan dan status aktifnya dijaga)."""
    bersih = sorted({(n or "").strip() for n in nilai_list
                     if (n or "").strip() and (n or "").strip() != KELAS_SEMUA})
    if not bersih:
        return []
    baru = [n for n in bersih if n not in daftar_kelas_nama_semua()]
    for n in baru:
        db.execute("""INSERT INTO branchops_ref_values (kategori, nilai, urutan)
                      VALUES (%s,%s,0) ON CONFLICT (kategori, nilai) DO NOTHING""",
                   (KATEGORI, n))
    return baru


def daftar_kelas_nama_semua():
    """Nama wilayah termasuk yang nonaktif. Untuk memeriksa keberadaan."""
    return [b["nilai"] for b in db.q(
        "SELECT nilai FROM branchops_ref_values WHERE kategori=%s", (KATEGORI,))]


def tambah_kelas(nilai):
    nilai = (nilai or "").strip()
    if not nilai:
        raise ValueError("Nama wilayah tidak boleh kosong")
    if nilai == KELAS_SEMUA:
        raise ValueError(f"'{KELAS_SEMUA}' adalah kelas khusus sistem, "
                         f"tidak boleh dipakai sebagai nama wilayah")
    if nilai in daftar_kelas_nama_semua():
        raise ValueError(f"Wilayah '{nilai}' sudah ada")
    db.execute("""INSERT INTO branchops_ref_values (kategori, nilai, urutan)
                  VALUES (%s,%s,0)""", (KATEGORI, nilai))
    return nilai


def ubah_nama_kelas(lama, baru):
    """Ganti nama wilayah, ikut memperbarui cabang dan pengguna yang memakainya.

    Ketiganya harus berubah bersamaan. Kalau hanya daftarnya yang diganti,
    cabang dan pengguna akan menunjuk nama yang tidak ada lagi, dan pengguna
    itu diam-diam tidak melihat baris apa pun."""
    baru = (baru or "").strip()
    if not baru:
        raise ValueError("Nama wilayah tidak boleh kosong")
    if baru == KELAS_SEMUA:
        raise ValueError(f"'{KELAS_SEMUA}' adalah kelas khusus sistem")
    if lama not in daftar_kelas_nama_semua():
        raise ValueError(f"Wilayah '{lama}' tidak ada")
    if baru != lama and baru in daftar_kelas_nama_semua():
        raise ValueError(f"Wilayah '{baru}' sudah ada")
    with db.conn() as c:
        with c.cursor() as k:
            k.execute("""UPDATE branchops_ref_values SET nilai=%s
                          WHERE kategori=%s AND nilai=%s""", (baru, KATEGORI, lama))
            k.execute("UPDATE branchops_branches SET region_class=%s WHERE region_class=%s",
                      (baru, lama))
            k.execute("UPDATE branchops_users SET region_class=%s WHERE region_class=%s",
                      (baru, lama))
    return baru


def pemakai_kelas(nilai):
    """(jumlah_cabang, jumlah_pengguna) yang memakai wilayah ini."""
    r = db.q1("""SELECT (SELECT count(*) FROM branchops_branches
                          WHERE region_class=%s) AS cabang,
                        (SELECT count(*) FROM branchops_users
                          WHERE region_class=%s) AS pengguna""", (nilai, nilai))
    return int(r["cabang"]), int(r["pengguna"])


def hapus_kelas(nilai):
    """Hapus wilayah. DITOLAK bila masih dipakai.

    Sengaja menolak, bukan menghapus beruntun. Menghapus wilayah yang masih
    dipakai akan membuat cabangnya tidak terlihat siapa pun dan penggunanya
    kehilangan seluruh akses — tanpa pesan apa pun di layar mereka."""
    if nilai not in daftar_kelas_nama_semua():
        raise ValueError(f"Wilayah '{nilai}' tidak ada")
    cabang, pengguna = pemakai_kelas(nilai)
    if cabang or pengguna:
        raise ValueError(
            f"Wilayah '{nilai}' masih dipakai {cabang} cabang dan "
            f"{pengguna} pengguna. Pindahkan dulu, atau nonaktifkan saja.")
    db.execute("DELETE FROM branchops_ref_values WHERE kategori=%s AND nilai=%s",
               (KATEGORI, nilai))
    return nilai


def set_aktif_kelas(nilai, aktif):
    """Nonaktifkan/aktifkan wilayah.

    Wilayah nonaktif hilang dari pilihan saat menjatah pengguna baru, TAPI
    pengguna yang terlanjur memakainya tetap melihat cabangnya. Ini disengaja:
    menonaktifkan adalah cara berhenti memakai tanpa mencabut akses siapa pun
    secara mendadak."""
    if nilai not in daftar_kelas_nama_semua():
        raise ValueError(f"Wilayah '{nilai}' tidak ada")
    db.execute("""UPDATE branchops_ref_values SET aktif=%s
                   WHERE kategori=%s AND nilai=%s""", (bool(aktif), KATEGORI, nilai))
    return bool(aktif)


def set_wilayah_cabang(branch_code, nilai):
    """Ubah wilayah SATU cabang, tanpa perlu mengunggah ulang Excel."""
    nilai = (nilai or "").strip()
    if nilai and nilai not in daftar_kelas_nama_semua():
        raise ValueError(f"Wilayah '{nilai}' tidak ada di master wilayah")
    n = db.execute("""UPDATE branchops_branches SET region_class=%s
                       WHERE branch_code=%s""", (nilai or None, branch_code))
    if not n:
        raise ValueError(f"Cabang '{branch_code}' tidak ada di master cabang")
    return nilai or None


def pilihan_kelas():
    """Daftar untuk layar admin: kelas dari master + kelas khusus SEMUA."""
    return [KELAS_SEMUA] + [k for k in daftar_kelas() if k != KELAS_SEMUA]


def set_kelas(uid, kelas):
    """Simpan jatah wilayah seorang pengguna. Mengembalikan nilai tersimpan.

    Nilai kosong disimpan sebagai NULL = tidak melihat apa pun.
    Nilai yang tidak dikenal ditolak, supaya salah ketik tidak diam-diam
    membuat pengguna kehilangan seluruh akses tanpa pesan apa pun."""
    kelas = (kelas or "").strip()
    if kelas and kelas != KELAS_SEMUA and kelas not in daftar_kelas():
        raise ValueError(f"Wilayah '{kelas}' tidak ada atau sedang nonaktif. "
                         f"Kelola daftarnya di tab Master Data.")
    db.execute("UPDATE branchops_users SET region_class=%s WHERE id=%s",
               (kelas or None, uid))
    return kelas or None
