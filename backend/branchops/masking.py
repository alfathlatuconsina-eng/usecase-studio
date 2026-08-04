# -*- coding: utf-8 -*-
"""
Penyamaran nama nasabah (customer name masking) — modul Branch Operations.

KENAPA DI BACKEND, BUKAN DI JAVASCRIPT
--------------------------------------
Kalau nama hanya disamarkan di halaman HTML, nama aslinya tetap terkirim dalam
respons JSON dan masih bisa dilihat siapa saja lewat tab "Network" di browser.
Jadi penyamaran dilakukan DI SINI, tepat sebelum data meninggalkan API. Ekspor
CSV di halaman juga dibangun dari data yang sama, sehingga ikut tersamar.

ATURAN
------
- Nama nasabah SELALU diganti "***", tidak peduli isinya:
      "BUDI SANTOSO WIJAYA"  ->  "***"
      "BUDIONO"              ->  "***"
- Berlaku untuk SEMUA peran, termasuk admin. Tidak ada pengecualian dan
  tidak ada endpoint untuk membuka penyamaran — kalau nama asli benar-benar
  dibutuhkan, sumbernya adalah berkas Excel aslinya, bukan aplikasi ini.
  (Karena tidak ada yang bisa membuka penyamaran, tidak ada pula yang perlu
  dicatat di branchops_audit untuk hal ini.)
- Nama PEGAWAI (cs_nama, teller_nama, flm1_nama, flm2_nama) TIDAK disamarkan.
  Yang wajib disamarkan hanya nama NASABAH.

CATATAN PEMAKAIAN
-----------------
Karena semua nama tampil sama ("***"), baris dibedakan lewat nomor rekening /
nomor deposito / nomor CIF, bukan lewat nama.
"""
from __future__ import annotations

# Nama field (kunci JSON) yang berisi nama nasabah dan harus disamarkan.
# Sengaja dicocokkan PERSIS, bukan "mengandung kata nama", supaya field lain
# seperti nama_file (nama berkas Excel) dan branch_name tidak ikut tersamar.
NAMA_NASABAH = {
    "nama_pemilik",     # dashboard 1, 2, 3
    "nama_pencairan",   # dashboard 1 — penerima dana pencairan
    "nasabah_it",       # dashboard 4 — nama versi data IT
    "nasabah_cabang",   # dashboard 4 — nama versi data cabang
    "nama",             # grafik "top nasabah" di dashboard 1 (alias SQL)
}

# Nama pegawai — didaftarkan di sini hanya sebagai catatan bahwa ini SENGAJA
# tidak disamarkan. Jangan tambahkan ke NAMA_NASABAH tanpa diminta.
NAMA_PEGAWAI = {"cs_nama", "teller_nama", "flm1_nama", "flm2_nama"}

TANDA_SAMAR = "***"


def mask_name(value):
    """Samarkan satu nama menjadi "***".

    Nilai kosong (None / string kosong) dikembalikan apa adanya, supaya sel
    yang memang kosong tidak berubah jadi seolah-olah ada nama tersembunyi."""
    if value is None:
        return None
    if not str(value).strip():
        return value
    return TANDA_SAMAR


def mask_issue_value(kolom, nilai):
    """Baris validasi (tabel branchops_issues) menyimpan nilai sel Excel apa
    adanya — termasuk nama nasabah, misalnya pada peringatan 'nama_terpotong'
    dengan kolom 'NamaPemilikRekening'. Samarkan kalau kolomnya kolom nama."""
    if nilai is None or not kolom:
        return nilai
    if "nama" in str(kolom).lower():
        return mask_name(nilai)
    return nilai


def apply(obj):
    """Telusuri dict/list hasil query dan samarkan setiap field nama nasabah.

    Mengembalikan struktur BARU — data asli di memori tidak diubah, supaya
    fungsi ini aman dipanggil di mana saja tanpa efek samping."""
    if isinstance(obj, dict):
        keluar = {}
        for k, v in obj.items():
            if k in NAMA_NASABAH:
                keluar[k] = mask_name(v)
            elif k == "nilai" and "kolom" in obj:
                # baris validasi: nilai sel mentah, disamarkan sesuai kolomnya
                keluar[k] = mask_issue_value(obj.get("kolom"), v)
            else:
                keluar[k] = apply(v)
        return keluar
    if isinstance(obj, list):
        return [apply(x) for x in obj]
    if isinstance(obj, tuple):
        return tuple(apply(x) for x in obj)
    return obj


def should_mask():
    """Selalu True — nama nasabah disamarkan untuk SEMUA peran.

    Fungsi ini sengaja dipertahankan (bukan dihapus) agar tetap ada satu
    tempat untuk memutuskan hal ini. Kalau suatu saat diminta ada peran yang
    boleh melihat nama asli, ubah di sini saja — tapi ingat aturan di
    CLAUDE.md: pembukaan penyamaran wajib dibatasi peran DAN dicatat ke
    branchops_audit."""
    return True
