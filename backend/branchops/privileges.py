# -*- coding: utf-8 -*-
"""
Hak menu per PERAN — modul Branch Operations.

KENAPA DI BACKEND
-----------------
Menyembunyikan tab di JavaScript TIDAK cukup: siapa pun yang sudah masuk bisa
memanggil /api/branchops/dash/3 langsung dari tab Network atau curl, walaupun
tabnya tidak kelihatan. Karena itu setiap rute yang terdampak diperiksa di
sini, di sisi server.

ATURAN
------
1. Hak menu melekat pada PERAN, bukan pada pengguna perorangan. Seluruh
   pengguna berperan 'viewer' memakai satu pengaturan yang sama.
2. Hak menu hanya bisa MEMPERSEMPIT, tidak pernah memperluas.
   Pemeriksaan peran (@require) tetap jalan lebih dulu dan tidak dilemahkan.
   Memberi menu "upload" kepada viewer tetap tidak membuatnya bisa mengunggah.
3. Peran 'admin' SELALU mendapat semua menu. Ini disengaja: tanpa itu, seorang
   admin bisa mencabut menu "users" dari peran admin, lalu tidak ada lagi
   yang bisa memperbaikinya lewat aplikasi.
4. Peran yang BELUM diatur mendapat semua menu yang masuk akal untuknya,
   sehingga memasang fitur ini tidak tiba-tiba mengunci siapa pun.
"""
from __future__ import annotations

from functools import wraps

from flask import jsonify, request

from . import db

# Kunci menu = nilai data-tab di branchops.html. Harus sama persis.
# "master" bukan tab tersendiri, melainkan kotak "Langkah 0 — Master cabang"
# di dalam tab Unggah. Dijadikan kunci terpisah supaya haknya bisa diatur
# terpisah dari hak mengunggah berkas transaksi biasa.
MENU_KEYS = ["home", "d1", "d2", "d3", "d4",
             "upload", "master", "masterdata", "users", "settings", "audit"]

# Label untuk layar admin (agar backend jadi satu sumber kebenaran)
MENU_LABEL = {
    "home":     "Beranda",
    "d1":       "Break Deposito",
    "d2":       "Pencairan",
    "d3":       "TBO",
    "d4":       "Rekonsiliasi",
    "upload":   "Unggah",
    "master":   "Master Cabang",
    "masterdata": "Master Data",
    "users":    "Pengguna",
    "settings": "Pengaturan",
    "audit":    "Audit",
}

# Menu yang memang hanya masuk akal untuk peran tertentu. Dipakai untuk
# menghitung bawaan "semua yang perannya izinkan".
MENU_MIN_ROLE = {
    "upload":   ("admin", "editor"),
    "master":   ("admin", "editor"),
    # Master Data mengatur daftar wilayah, dan wilayah menentukan siapa
    # melihat cabang mana. Mengubahnya = mengubah hak lihat orang lain,
    # jadi admin saja - setara dengan layar Pengguna.
    "masterdata": ("admin",),
    "users":    ("admin",),
    "settings": ("admin",),
    "audit":    ("admin",),
}

# Menu yang BOLEH diberikan kepada sebuah peran, tapi TIDAK aktif secara
# bawaan. Master cabang menentukan cabang mana yang dikenali seluruh modul;
# salah unggah membuat seluruh baris transaksi ditolak. Jadi bawaannya hanya
# admin, dan admin bisa memberikannya ke editor lewat layar Hak Menu.
MENU_DEFAULT_OFF = {"master"}


def menus_for_role(role):
    """Menu maksimum yang BOLEH dimiliki sebuah peran (batas atas).

    Ini batas, bukan bawaan. Lihat menus_default_for_role() untuk bawaan."""
    return [m for m in MENU_KEYS
            if role in MENU_MIN_ROLE.get(m, ("admin", "editor", "viewer"))]


def menus_default_for_role(role):
    """Bawaan untuk peran yang belum pernah diatur.

    Sama dengan batas atas, dikurangi menu yang sengaja mati secara bawaan.
    Admin dikecualikan: admin selalu mendapat semuanya."""
    if role == "admin":
        return list(MENU_KEYS)
    return [m for m in menus_for_role(role) if m not in MENU_DEFAULT_OFF]


PERAN = ("admin", "editor", "viewer")


def _role():
    return getattr(request, "user", {}).get("role")


def allowed_menus(role=None):
    """Daftar menu yang benar-benar boleh diakses oleh sebuah PERAN.

    Admin selalu dapat semua. Peran yang belum punya baris di
    branchops_role_menus dianggap 'belum diatur' -> dapat semua yang
    masuk akal untuknya."""
    if role is None:
        role = _role()

    if role == "admin":
        return list(MENU_KEYS)

    batas = menus_for_role(role)

    baris = db.q("SELECT menus FROM branchops_role_menus WHERE role=%s", (role,))
    if not baris:
        return menus_default_for_role(role)   # belum diatur -> bawaan

    tersimpan = baris[0]["menus"] or []
    # Irisan: hak tersimpan TIDAK boleh melebihi batas peran.
    return [m for m in batas if m in tersimpan]


def set_menus(role, menus, oleh):
    """Simpan hak menu sebuah peran. Nilai tak dikenal dibuang.

    Peran 'admin' ditolak: admin selalu dapat semua menu, dan mengizinkan
    penyuntingan di sini hanya akan menimbulkan kesan keliru bahwa admin
    bisa dibatasi."""
    if role not in PERAN:
        raise ValueError("peran tidak dikenal")
    if role == "admin":
        raise ValueError("peran admin selalu mendapat semua menu")
    bersih = [m for m in MENU_KEYS if m in (menus or [])]
    db.execute(
        """INSERT INTO branchops_role_menus (role, menus, updated_by, updated_at)
           VALUES (%s, %s, %s, now())
           ON CONFLICT (role) DO UPDATE
             SET menus=EXCLUDED.menus,
                 updated_by=EXCLUDED.updated_by,
                 updated_at=now()""",
        (role, bersih, oleh))
    return bersih


def hapus_menus(role):
    """Kembalikan sebuah peran ke bawaan dengan menghapus barisnya."""
    db.execute("DELETE FROM branchops_role_menus WHERE role=%s", (role,))


def peta_menus():
    """Seluruh pengaturan tersimpan, untuk layar admin: {peran: [menu,...]}."""
    return {r["role"]: (r["menus"] or [])
            for r in db.q("SELECT role, menus FROM branchops_role_menus")}


def boleh(menu_key):
    """True kalau pengguna saat ini boleh mengakses menu tersebut."""
    return menu_key in allowed_menus()


def require_menu(menu_key):
    """Dekorator: dipasang SETELAH @require(...), bukan menggantikannya.

    Urutannya penting:
        @bp.get("/x")
        @require("admin", "editor")     <- peran diperiksa dulu
        @require_menu("upload")         <- baru hak menu
    """
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **k):
            if not boleh(menu_key):
                return jsonify(error="Menu ini tidak tersedia untuk akun Anda"), 403
            return fn(*a, **k)
        return wrapper
    return deco
