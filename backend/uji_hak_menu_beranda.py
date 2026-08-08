# -*- coding: utf-8 -*-
"""Uji hak menu pada Beranda — TANPA basis data dan TANPA Flask.

Jalankan:  py -3 backend/uji_hak_menu_beranda.py

Kenapa ada berkas ini
---------------------
Dua hal di ringkasan() gagal secara DIAM-DIAM, bukan dengan galat:

1. Jumlah parameter. Setiap cabang UNION membawa satu {swh}, dan {swh}
   membawa parameter jatah wilayah. Kalau cabangnya berkurang tapi
   pengalinya tidak, psycopg menerima jumlah parameter yang salah — dan
   kalau kebetulan jumlahnya tetap cocok, parameternya justru masuk ke
   tempat yang keliru dan datanya salah tanpa satu pun pesan.

2. Nama kolom UNION. PostgreSQL memberi nama kolom dari cabang PERTAMA.
   Kalau cabang pencairan berdiri sendiri tanpa alias, g.sumber dan
   g.hari_terlambat lenyap dan barisnya kosong tanpa galat.

Keduanya tidak akan terlihat dengan membaca kode sepintas, jadi diperiksa
di sini. db dan scoping dipalsukan supaya tidak perlu PostgreSQL.
"""
from __future__ import annotations

import os
import re
import sys
import types

SINI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SINI)

# --- palsukan db dan scoping SEBELUM analytics diimpor --------------------
DIREKAM = []


def _rekam(sql, params=None):
    DIREKAM.append((sql, params))
    return sql


db_palsu = types.ModuleType("branchops.db")
db_palsu.q = lambda sql, params=None: (_rekam(sql, params), [])[1]
db_palsu.q1 = lambda sql, params=None: (_rekam(sql, params), {
    "it": 11, "pencairan": 22, "tbo": 33, "rekon_bermasalah": 44, "cabang": 55,
    "total": 0, "dari_tbo": 0, "dari_pencairan": 0, "lewat_target": 0,
    "tanpa_target": 0, "terlambat_max": 0, "rp": 0})[1]
db_palsu.get_settings = lambda: {}

# klausa() mengembalikan (potongan WHERE, daftar parameter). Dua parameter
# dipakai supaya kalau pengalinya salah, hasilnya beda jauh dan kentara.
scoping_palsu = types.ModuleType("branchops.scoping")
scoping_palsu.klausa = lambda scope, alias="br": (
    " AND {}.branch_code = ANY(%s) AND %s".format(alias), ["CAB", 1])

paket = types.ModuleType("branchops")
paket.__path__ = [os.path.join(SINI, "branchops")]
sys.modules.setdefault("branchops", paket)
sys.modules["branchops.db"] = db_palsu
sys.modules["branchops.scoping"] = scoping_palsu

from branchops import analytics                      # noqa: E402
from branchops import privileges                     # noqa: E402

analytics.db = db_palsu
analytics.scoping = scoping_palsu
analytics.periode_tersedia = lambda scope="": {"awal": None, "akhir": None}

GAGAL = []


def cek(nama, syarat, catatan=""):
    print(("  OK   " if syarat else "  GAGAL") + "  " + nama
          + (("   -> " + catatan) if (catatan and not syarat) else ""))
    if not syarat:
        GAGAL.append(nama)


# ==========================================================================
print("\n1. privileges — Beranda tidak bisa dicabut")
# ==========================================================================
privileges.db = db_palsu

# Peran diatur TANPA "home": allowed_menus harus mengembalikannya.
db_palsu.q = lambda sql, params=None: [{"menus": ["d1"]}]
hasil = privileges.allowed_menus("viewer")
cek("viewer diatur ['d1'] tetap dapat home", "home" in hasil, str(hasil))
cek("viewer diatur ['d1'] tidak dapat d2", "d2" not in hasil, str(hasil))
cek("viewer diatur ['d1'] tetap dapat d1", "d1" in hasil, str(hasil))

# Peran belum diatur: bawaan, dan tetap ada home.
db_palsu.q = lambda sql, params=None: []
bawaan = privileges.allowed_menus("viewer")
cek("viewer belum diatur dapat home", "home" in bawaan, str(bawaan))
cek("viewer belum diatur tidak dapat master",
    "master" not in bawaan, str(bawaan))

cek("admin dapat semua kunci",
    set(privileges.allowed_menus("admin")) == set(privileges.MENU_KEYS))

# set_menus menambahkan home walau layar tidak mengirimnya.
disimpan = {}
db_palsu.execute = lambda sql, params=None: disimpan.update({"p": params})
hasil = privileges.set_menus("viewer", ["d1"], "uji@uji")
cek("set_menus menyimpan home walau tidak dikirim", "home" in hasil, str(hasil))
cek("set_menus tidak menambah menu lain",
    set(hasil) == {"home", "d1"}, str(hasil))

try:
    privileges.set_menus("admin", ["d1"], "uji@uji")
    cek("set_menus menolak peran admin", False, "tidak menolak")
except ValueError:
    cek("set_menus menolak peran admin", True)

# ==========================================================================
print("\n2. ringkasan — jumlah parameter cocok dengan jumlah %s")
# ==========================================================================
db_palsu.q = lambda sql, params=None: (_rekam(sql, params), [])[1]

KASUS = [
    ("d2 + d3 (dua cabang)", ["home", "d1", "d2", "d3", "d4"], 2),
    ("hanya d3           ", ["home", "d3"], 1),
    ("hanya d2           ", ["home", "d2"], 1),
    ("tanpa d2 dan d3    ", ["home", "d1"], 0),
    ("menus=None         ", None, 2),
]

for nama, menus, n_lengan in KASUS:
    DIREKAM.clear()
    hasil = analytics.ringkasan("", menus)

    for sql, params in DIREKAM:
        n_ph = sql.count("%s")
        n_par = len(params or [])
        cek("%s  %d %%s = %d parameter" % (nama, n_ph, n_par),
            n_ph == n_par,
            "placeholder %d, parameter %d" % (n_ph, n_par))

    gab = [s for s, _ in DIREKAM if "UNION ALL" in s or " g" in s]
    n_union = max([s.count("UNION ALL") for s, _ in DIREKAM] or [0])
    cek("%s  cabang UNION = %d" % (nama, n_lengan),
        (n_union + 1 if n_lengan else 0) == n_lengan or n_lengan == 0
        or n_union == n_lengan - 1,
        "UNION ALL muncul %d kali" % n_union)

    # Tanpa lengan: daftar TBO terbuka tidak boleh ditanyakan sama sekali.
    #
    # Yang diperiksa adalah query DAFTAR-nya, bukan sekadar kemunculan nama
    # tabel. Blok "hitung" memang tetap menghitung branchops_tbo lalu
    # membuang angkanya (lihat komentar di ringkasan()): satu query dengan
    # pengali sp * 5 yang terikat pada lima {swh} di dalamnya, dan
    # memecahnya justru mengundang pengali yang salah. Angkanya tidak
    # pernah keluar dari proses, jadi yang harus dibuktikan di sini adalah
    # tidak adanya query yang MENGAMBIL BARIS TBO terbuka.
    if n_lengan == 0:
        cek("%s  daftar TBO terbuka tidak ditanyakan" % nama,
            not any("Outstanding" in s for s, _ in DIREKAM))
        cek("%s  kpi total = 0" % nama, hasil["tbo_terbuka"]["kpi"]["total"] == 0)
        cek("%s  rows kosong" % nama, hasil["tbo_terbuka"]["rows"] == [])

# ==========================================================================
print("\n3. ringkasan — cabang UNION yang berdiri sendiri punya nama kolom")
# ==========================================================================
# Kolom yang dibaca layar dari g.*, harus ada sebagai alias di TIAP cabang.
WAJIB = ["sumber", "id", "branch_code", "branch_name", "tgl_input",
         "no_rekening", "nama_pemilik", "nominal", "mata_uang", "dokumen",
         "target_pemenuhan_tbo", "status_tbo", "hari_terlambat", "aging"]

for nama, menus in (("hanya d3", ["home", "d3"]), ("hanya d2", ["home", "d2"])):
    DIREKAM.clear()
    analytics.ringkasan("", menus)
    sql = next((s for s, _ in DIREKAM if "branchops_" in s and " AS sumber" in s), "")
    kepala = sql.split("FROM branchops_")[0] if sql else ""
    hilang = [k for k in WAJIB if not re.search(r"\bAS\s+" + k + r"\b", kepala)]
    cek("%s  semua %d kolom punya alias" % (nama, len(WAJIB)),
        not hilang, "tidak beralias: " + ", ".join(hilang))

# ==========================================================================
print("\n4. ringkasan — angka kartu dibuang untuk menu yang tidak berhak")
# ==========================================================================
db_palsu.q1 = lambda sql, params=None: (_rekam(sql, params), {
    "it": 11, "pencairan": 22, "tbo": 33, "rekon_bermasalah": 44, "cabang": 55,
    "total": 0, "dari_tbo": 0, "dari_pencairan": 0, "lewat_target": 0,
    "tanpa_target": 0, "terlambat_max": 0, "rp": 0})[1]

h = analytics.ringkasan("", ["home", "d1"])["hitung"]
cek("d1 saja: it tetap terisi", h["it"] == 11, str(h))
cek("d1 saja: pencairan None", h["pencairan"] is None, str(h))
cek("d1 saja: tbo None", h["tbo"] is None, str(h))
cek("d1 saja: rekon None", h["rekon_bermasalah"] is None, str(h))
cek("d1 saja: cabang TETAP terisi (spanduk master cabang)",
    h["cabang"] == 55, str(h))

h = analytics.ringkasan("", None)["hitung"]
cek("menus=None: semua angka utuh",
    all(h[k] is not None for k in
        ("it", "pencairan", "tbo", "rekon_bermasalah", "cabang")), str(h))

# ==========================================================================
print("\n" + "=" * 62)
if GAGAL:
    print("GAGAL %d uji:" % len(GAGAL))
    for g in GAGAL:
        print("   - " + g)
    sys.exit(1)
print("SELURUH UJI LULUS")
print("=" * 62)
