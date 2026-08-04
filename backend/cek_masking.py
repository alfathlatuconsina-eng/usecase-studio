# -*- coding: utf-8 -*-
"""
Cek penyamaran nama nasabah (Branch Ops) — dijalankan terhadap aplikasi
yang SEDANG BERJALAN di localhost:8000.

Cara pakai (dari folder backend/, aplikasi harus sudah jalan):

    py -3 cek_masking.py

Skrip akan menanyakan email dan sandi akun Branch Ops, lalu memanggil setiap
endpoint yang mengembalikan baris data dan memeriksa isinya satu per satu.

Yang diperiksa:
  1. Setiap field nama nasabah harus berisi "***" (atau kosong).
  2. Nama PEGAWAI harus TETAP terlihat — memastikan penyamaran tidak
     kebablasan ke kolom yang seharusnya tidak disamarkan.
  3. nama_file dan branch_name harus utuh — sama, memastikan tidak kebablasan.
  4. Ekspor CSV validasi (issues.csv) juga diperiksa, karena berisi isi sel
     Excel mentah yang bisa memuat nama nasabah.

Skrip ini HANYA MEMBACA. Tidak ada yang diubah di database.
Tidak memakai pustaka tambahan — hanya bawaan Python.
"""
from __future__ import annotations

import csv
import getpass
import importlib.util
import io
import json
import pathlib
import sys
import urllib.error
import urllib.request

BASE = "http://localhost:8000"

# ---------------------------------------------------------------------------
# Ambil daftar field langsung dari masking.py, supaya kalau daftarnya berubah
# skrip ini ikut berubah dan tidak jadi usang diam-diam.
# Dimuat lewat path berkas agar tidak menjalankan branchops/__init__.py.
# ---------------------------------------------------------------------------
_mask_path = pathlib.Path(__file__).parent / "branchops" / "masking.py"
_spec = importlib.util.spec_from_file_location("masking_check", _mask_path)
masking = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(masking)

NAMA_NASABAH = masking.NAMA_NASABAH      # wajib "***"
NAMA_PEGAWAI = masking.NAMA_PEGAWAI      # wajib TIDAK disamarkan
TANDA = masking.TANDA_SAMAR              # "***"

# Field yang bukan orang — harus utuh
BUKAN_ORANG = {"nama_file", "branch_name", "core_alias"}


class Hasil:
    def __init__(self):
        self.bocor = []       # nama nasabah yang TIDAK tersamar
        self.kebablasan = []  # field yang tersamar padahal tidak seharusnya
        self.dicek = 0        # berapa nilai nama nasabah yang benar-benar diperiksa
        self.pegawai = 0      # berapa nama pegawai yang terlihat utuh

    def periksa(self, obj, jalur=""):
        """Telusuri respons JSON dan catat setiap pelanggaran."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                sub = f"{jalur}.{k}" if jalur else k
                if k in NAMA_NASABAH:
                    if v is None or (isinstance(v, str) and not v.strip()):
                        pass                      # kosong memang boleh kosong
                    elif v != TANDA:
                        self.bocor.append((sub, v))
                    else:
                        self.dicek += 1
                elif k in NAMA_PEGAWAI:
                    if v == TANDA:
                        self.kebablasan.append((sub, v))
                    elif v:
                        self.pegawai += 1
                elif k in BUKAN_ORANG and v == TANDA:
                    self.kebablasan.append((sub, v))
                else:
                    self.periksa(v, sub)
        elif isinstance(obj, list):
            for i, x in enumerate(obj):
                self.periksa(x, f"{jalur}[{i}]")


def minta(url, token=None, mentah=False):
    req = urllib.request.Request(BASE + url)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
            return data if mentah else json.loads(data.decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"_http_error": e.code, "_pesan": e.read().decode("utf-8", "replace")[:200]}
    except urllib.error.URLError as e:
        print(f"\n  GAGAL menghubungi {BASE} — apakah aplikasi sudah jalan?")
        print(f"  ({e.reason})")
        sys.exit(1)


def login(email, sandi):
    body = json.dumps({"email": email, "password": sandi}).encode()
    req = urllib.request.Request(BASE + "/api/branchops/login", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError:
        print("\n  GAGAL masuk: email atau sandi salah.")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"\n  GAGAL menghubungi {BASE} — apakah aplikasi sudah jalan? ({e.reason})")
        sys.exit(1)


def main():
    print()
    print("=" * 62)
    print("  CEK PENYAMARAN NAMA NASABAH — Branch Ops")
    print("=" * 62)
    print(f"  Sasaran : {BASE}  (hanya dibaca)")
    print()

    email = input("  Email akun Branch Ops : ").strip()
    sandi = getpass.getpass("  Sandi                 : ")

    sesi = login(email, sandi)
    token, peran = sesi["token"], sesi.get("role", "?")
    print(f"\n  Masuk sebagai {sesi.get('email')} (peran: {peran})")
    if peran == "admin":
        print("  Catatan: admin pun harus melihat '***' — tidak ada pengecualian.")

    h = Hasil()
    titik = [("/api/branchops/summary", "Beranda"),
             ("/api/branchops/cabang", "Daftar cabang"),
             ("/api/branchops/batches", "Riwayat unggahan"),
             ("/api/branchops/dash/1", "Dashboard 1 — Break Deposito"),
             ("/api/branchops/dash/2", "Dashboard 2 — Pencairan"),
             ("/api/branchops/dash/3", "Dashboard 3 — TBO"),
             ("/api/branchops/dash/4", "Dashboard 4 — Rekonsiliasi"),
             ("/api/branchops/settings", "Pengaturan")]
    if peran == "admin":
        titik.append(("/api/branchops/audit", "Jejak audit"))

    print("\n  Memeriksa endpoint:")
    for url, nama in titik:
        d = minta(url, token)
        if isinstance(d, dict) and "_http_error" in d:
            print(f"    - {nama:34} dilewati (HTTP {d['_http_error']})")
            continue
        sebelum = len(h.bocor) + len(h.kebablasan)
        h.periksa(d)
        sesudah = len(h.bocor) + len(h.kebablasan)
        print(f"    - {nama:34} {'MASALAH' if sesudah > sebelum else 'ok'}")

    # ---- ekspor CSV validasi: isi sel Excel mentah ----
    print("\n  Memeriksa ekspor CSV validasi:")
    batches = minta("/api/branchops/batches", token)
    daftar = (batches or {}).get("batches") or []
    if not daftar:
        print("    - belum ada batch unggahan, bagian ini dilewati")
    else:
        for b in daftar[:3]:
            mentah = minta(f"/api/branchops/batch/{b['id']}/issues.csv", token, mentah=True)
            if isinstance(mentah, dict):
                print(f"    - batch #{b['id']:<4} dilewati (HTTP {mentah.get('_http_error')})")
                continue
            teks = mentah.decode("utf-8-sig", "replace")
            baris = list(csv.reader(io.StringIO(teks), delimiter=";"))
            temuan = 0
            for r in baris[1:]:
                if len(r) >= 5 and "nama" in (r[3] or "").lower():
                    if r[4] and r[4] != TANDA:
                        h.bocor.append((f"issues.csv#{b['id']} kolom {r[3]}", r[4]))
                        temuan += 1
                    elif r[4]:
                        h.dicek += 1
            print(f"    - batch #{b['id']:<4} {'MASALAH' if temuan else 'ok'}")

    # ---------------------------------------------------------------- hasil
    print("\n" + "=" * 62)
    if h.bocor:
        print("  GAGAL — ada nama nasabah yang TIDAK tersamar:")
        for jalur, nilai in h.bocor[:25]:
            print(f"    {jalur}  =  {nilai!r}")
        if len(h.bocor) > 25:
            print(f"    ... dan {len(h.bocor) - 25} lagi")
        print("\n  Beri tahu Claude daftar di atas untuk diperbaiki.")
    elif h.dicek == 0:
        print("  BELUM TERUJI — tidak ada satu pun nama nasabah yang diperiksa.")
        print("  Kemungkinan besar database Branch Ops lokal masih kosong,")
        print("  jadi tidak ada data untuk diuji. Ini BUKAN berarti lulus.")
        print("  Unggah satu berkas Excel lebih dahulu, lalu jalankan lagi.")
    else:
        print(f"  LULUS — {h.dicek} nilai nama nasabah diperiksa, semuanya '***'.")

    if h.kebablasan:
        print("\n  PERINGATAN — penyamaran kebablasan (ini seharusnya TIDAK tersamar):")
        for jalur, nilai in h.kebablasan[:15]:
            print(f"    {jalur}  =  {nilai!r}")
    elif h.pegawai:
        print(f"  Nama pegawai tetap terlihat: {h.pegawai} nilai (memang disengaja).")

    print("=" * 62)
    print()


if __name__ == "__main__":
    main()
