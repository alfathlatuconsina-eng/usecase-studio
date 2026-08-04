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


def daftar_kelas():
    """Region Class yang benar-benar ada di master cabang.

    Sumbernya kolom region_class di branchops_branches, jadi daftarnya
    ikut berubah begitu master cabang diunggah ulang."""
    baris = db.q("""SELECT DISTINCT region_class AS k
                      FROM branchops_branches
                     WHERE region_class IS NOT NULL
                       AND region_class <> ''
                  ORDER BY region_class""")
    return [b["k"] for b in baris]


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
        raise ValueError(f"Region Class '{kelas}' tidak ada di master cabang")
    db.execute("UPDATE branchops_users SET region_class=%s WHERE id=%s",
               (kelas or None, uid))
    return kelas or None
