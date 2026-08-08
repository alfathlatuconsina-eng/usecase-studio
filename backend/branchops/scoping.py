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

DUA JENIS JATAH
---------------
Sejak Agustus 2026 ada DUA cara membatasi seorang pengguna, dan keduanya
SALING MENIADAKAN — satu pengguna memegang satu jenis saja:

    region_class  -> seluruh cabang dalam satu wilayah  ("Regional 1")
    branch_codes  -> daftar cabang tertentu             ["00123","00456"]

branch_codes adalah LARIK, bukan satu nilai — seorang penyelia bisa
memegang beberapa cabang dalam satu kota. Satu cabang cukup ditulis
sebagai larik satu unsur; tidak ada bentuk khusus untuk kasus itu.
"Tidak dijatah" selalu None, tidak pernah larik kosong.

Larangan memegang dua-duanya bukan sekadar kesepakatan di kode: ada CHECK
(ck_bo_users_satu_jatah) di schema.sql yang menolaknya di tingkat basis
data. Kalau toh suatu saat kedua kolom terisi, set_jatah() dan scope_aktif()
memenangkan CABANG — yang lebih sempit — supaya kegagalan berpihak pada
menutup data, bukan membukanya.

ATURAN
------
1. Peran 'admin' SELALU melihat semua cabang. Disengaja: admin yang tidak
   bisa melihat seluruh data tidak akan bisa memeriksa atau memperbaiki
   jatah wilayah pengguna lain.
2. Kelas khusus 'SEMUA' berarti melihat seluruh cabang. Ini yang diberikan
   kepada pengguna kantor pusat.
3. Pengguna yang jatahnya KOSONG (dua-duanya kosong) tidak melihat baris
   apa pun. Gagal-tertutup: data hanya terlihat setelah sengaja diberikan.
   Pengguna yang sudah ada sebelum fitur ini dipasang otomatis diberi
   kelas 'SEMUA' oleh migrasi di schema.sql, jadi tidak ada yang terkunci.
4. Cabang yang region_class-nya masih kosong hanya terlihat oleh admin dan
   kelas 'SEMUA'. Ini disengaja: cabang yang belum dikelompokkan tidak boleh
   bocor ke pengguna wilayah mana pun hanya karena masternya belum lengkap.
5. PENGECUALIAN aturan 4, disengaja: pengguna yang ditambatkan LANGSUNG ke
   sebuah cabang tetap melihat cabang itu walaupun cabangnya belum punya
   wilayah. Penunjukan langsung oleh admin lebih kuat daripada aturan
   "belum dikelompokkan" — kalau tidak, menambatkan pengguna ke cabang baru
   akan menghasilkan layar kosong tanpa petunjuk sebabnya.
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


def _bersihkan_kode(kode_list):
    """Rapikan daftar kode cabang: buang kosong, buang kembar, urutkan.

    Mengembalikan None bila tidak ada yang tersisa — bukan larik kosong.
    Diurutkan supaya dua daftar isi sama selalu tersimpan sama persis,
    sehingga perbandingan dan jejak audit tidak berubah hanya karena admin
    mencentang dengan urutan berbeda."""
    if not kode_list:
        return None
    if isinstance(kode_list, str):          # satu kode ditulis polos
        kode_list = [kode_list]
    bersih = sorted({(k or "").strip() for k in kode_list if (k or "").strip()})
    return bersih or None


def jatah_pengguna(email=None):
    """Jatah pengguna yang sedang masuk: (region_class, branch_codes).

    Dibaca dari basis data setiap kali, BUKAN dari JWT — supaya perubahan
    jatah berlaku pada request berikutnya, bukan pada login berikutnya.

    Karena CHECK ck_bo_users_satu_jatah, paling banyak satu dari keduanya
    terisi; yang lain pasti None. branch_codes berupa list, atau None."""
    email = email or _email()
    if not email:
        return None, None
    baris = db.q("""SELECT region_class, branch_codes
                      FROM branchops_users WHERE email=%s""", (email,))
    if not baris:
        return None, None
    r = baris[0]
    return ((r.get("region_class") or "").strip() or None,
            _bersihkan_kode(r.get("branch_codes")))


def kelas_pengguna(email=None):
    """Region Class milik pengguna. None bila ia dijatah per cabang."""
    return jatah_pengguna(email)[0]


def cabang_pengguna(email=None):
    """Daftar kode cabang milik pengguna. None bila ia dijatah per wilayah."""
    return jatah_pengguna(email)[1]


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
        None                    -> tanpa batasan, lihat semua cabang
        ("wilayah", "<kelas>")  -> hanya cabang dengan region_class itu
        ("cabang", [kode, ...]) -> hanya cabang-cabang itu
        ""                      -> tidak melihat apa pun (belum dijatah)

    Perhatikan bedanya None dan "" — keduanya "kosong" dalam arti Python,
    jadi pemeriksaannya harus pakai `is None`, bukan `if not scope`.

    Isinya sengaja dibuat BUNTU bagi pemanggil: analytics.py hanya meneruskan
    nilai ini ke klausa() tanpa pernah membukanya. Jadi menambah jenis jatah
    ketiga nanti cukup mengubah dua fungsi di berkas ini, bukan setiap query."""
    if boleh_semua():
        return None
    kelas, cabang = jatah_pengguna()
    # Cabang diperiksa lebih dulu: bila entah bagaimana kedua kolom terisi,
    # yang menang adalah jatah yang lebih SEMPIT.
    if cabang:
        return ("cabang", list(cabang))
    if kelas:
        return ("wilayah", kelas)
    return ""


def klausa(scope, alias="br"):
    """Potongan WHERE + parameter untuk sebuah nilai scope.

    Dipakai analytics.py. Dipisah dari scope_aktif() supaya analytics.py
    tetap bisa diuji tanpa perlu ada request Flask yang aktif.

    alias SELALU menunjuk branchops_branches, jadi kolom branch_code dan
    region_class dua-duanya pasti ada."""
    if scope is None:
        return "", []
    if isinstance(scope, tuple):
        jenis, nilai = scope
        if jenis == "cabang":
            # = ANY(%s) menerima satu larik sebagai SATU parameter, jadi
            # jumlah cabang tidak mengubah bentuk query. psycopg2 sendiri
            # yang mengubah list Python menjadi array PostgreSQL.
            kode = [nilai] if isinstance(nilai, str) else list(nilai or [])
            if not kode:
                return " AND FALSE", []      # daftar kosong -> tidak ada baris
            return f" AND {alias}.branch_code = ANY(%s)", [kode]
        if jenis == "wilayah":
            return f" AND {alias}.region_class = %s", [nilai]
        # Jenis tak dikenal -> tutup, jangan buka.
        return " AND FALSE", []
    if scope == "":
        # Tidak dijatah -> tidak ada baris yang cocok.
        return " AND FALSE", []
    # Jaring pengaman: string polos dibaca sebagai wilayah, seperti sebelum
    # jatah cabang ada. Menjaga pemanggil lama tetap benar, bukan diam-diam
    # berubah arti.
    return f" AND {alias}.region_class = %s", [scope]


def boleh_cabang(branch_code):
    """Bolehkah pengguna yang sedang masuk MENYENTUH baris di cabang ini?

    Dipakai endpoint yang mengubah SATU baris, di mana tidak ada query
    berfilter yang bisa disisipi klausa(). Contohnya PUT /tbo/<id>.

    Kenapa perlu: klausa() hanya melindungi baris yang DIBACA lewat daftar.
    Endpoint yang menerima id langsung dari URL tidak melewatinya sama
    sekali - tanpa pemeriksaan ini, seorang editor bisa mengubah baris
    cabang yang bahkan tidak boleh ia lihat, cukup dengan menebak id.

    Sengaja memakai scope_aktif() yang sama dengan pembacaan, supaya
    "yang boleh dilihat" dan "yang boleh diubah" tidak pernah berbeda arti.
    Menambah jenis jatah ketiga nanti cukup mengubah fungsi ini dan
    klausa(), bukan setiap endpoint.

    GAGAL TERTUTUP: apa pun yang tidak jelas menghasilkan False."""
    scope = scope_aktif()
    if scope is None:
        return True                      # admin / jatah SEMUA
    if scope == "":
        return False                     # belum dijatah -> tidak apa-apa
    if not branch_code:
        # Baris tanpa kode cabang hanya milik admin, dan admin sudah
        # tertangkap di cabang None di atas. Lihat aturan 5 di docstring.
        return False

    if isinstance(scope, tuple):
        jenis, nilai = scope
        if jenis == "cabang":
            kode = [nilai] if isinstance(nilai, str) else list(nilai or [])
            return branch_code in kode
        if jenis == "wilayah":
            b = db.q1("SELECT region_class FROM branchops_branches "
                      "WHERE branch_code=%s", (branch_code,))
            return bool(b) and b.get("region_class") == nilai
        return False                     # jenis tak dikenal -> tutup

    # String polos dibaca sebagai wilayah, sejalan dengan klausa().
    b = db.q1("SELECT region_class FROM branchops_branches "
              "WHERE branch_code=%s", (branch_code,))
    return bool(b) and b.get("region_class") == scope


def kode_di_luar_jatah(kode_list):
    """Dari sekumpulan kode cabang, mana yang DI LUAR jatah pengguna ini.

    Mengembalikan daftar kode yang TIDAK boleh disentuh, terurut. Daftar
    kosong berarti seluruhnya boleh.

    Dipakai POST /upload: sebuah berkas Excel memuat banyak cabang
    sekaligus, jadi pemeriksaannya harus atas HIMPUNAN kode, bukan satu
    baris demi satu baris. Memanggil boleh_cabang() per baris akan
    menembak basis data sekali per baris untuk jatah wilayah - satu berkas
    200 baris jadi 200 query. Di sini cukup SATU query.

    Aturannya sengaja SAMA PERSIS dengan boleh_cabang() dan klausa(),
    supaya "yang boleh dilihat", "yang boleh diubah" dan "yang boleh
    diunggah" tidak pernah berbeda arti. Kalau jenis jatah ketiga
    ditambahkan nanti, ketiganya harus diubah bersama.

    GAGAL TERTUTUP: jatah kosong atau jenis tak dikenal -> seluruh kode
    dianggap di luar jatah, bukan sebaliknya."""
    kode = sorted({(k or "").strip() for k in (kode_list or []) if (k or "").strip()})

    scope = scope_aktif()
    if scope is None:
        return []                       # admin / jatah SEMUA -> semuanya boleh
    if not kode:
        return []
    if scope == "":
        return kode                     # belum dijatah -> tidak satu pun boleh

    if isinstance(scope, tuple):
        jenis, nilai = scope
        if jenis == "cabang":
            boleh = set([nilai] if isinstance(nilai, str) else list(nilai or []))
            return [k for k in kode if k not in boleh]
        if jenis == "wilayah":
            wilayah = nilai
        else:
            return kode                 # jenis tak dikenal -> tutup semuanya
    else:
        # String polos dibaca sebagai wilayah, sejalan dengan klausa().
        wilayah = scope

    # Satu query untuk seluruh kode. Kode yang TIDAK ADA di master cabang
    # tidak akan muncul di hasil, jadi otomatis ikut terhitung di luar
    # jatah - sesuai aturan 4: cabang yang belum dikelompokkan hanya milik
    # admin.
    baris = db.q("""SELECT branch_code FROM branchops_branches
                     WHERE branch_code = ANY(%s) AND region_class = %s""",
                 (kode, wilayah))
    boleh = {r["branch_code"] for r in baris}
    return [k for k in kode if k not in boleh]


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


# Tipe cabang yang boleh dipakai. Daftar ini HARUS sama persis dengan
# CHECK (branch_type IN (...)) di schema.sql — kalau tidak, nilai yang lolos
# di sini akan ditolak PostgreSQL dan admin hanya melihat pesan error kasar.
# Diletakkan di modul ini supaya berdekatan dengan set_wilayah_cabang: dua-
# duanya menyunting satu baris di branchops_branches dari layar Master Data.
TIPE_CABANG = ("KC", "KCP", "Pusat", "Lainnya")


def set_tipe_cabang(branch_code, nilai):
    """Ubah tipe SATU cabang (KC/KCP/Pusat/Lainnya) dari layar Master Data.

    Kolom branch_type NOT NULL, jadi nilai kosong tidak diperbolehkan —
    'Lainnya' adalah pilihan untuk cabang yang tidak masuk kategori lain.

    CATATAN PENTING: mengunggah ulang master cabang akan MENIMPA nilai ini,
    karena parse_master menebak tipe dari nama cabang dan upsert di
    storage.py memakai branch_type=EXCLUDED.branch_type."""
    nilai = (nilai or "").strip()
    if nilai not in TIPE_CABANG:
        raise ValueError(f"Tipe '{nilai}' tidak dikenal. "
                         f"Pilih salah satu: {', '.join(TIPE_CABANG)}")
    n = db.execute("""UPDATE branchops_branches SET branch_type=%s
                       WHERE branch_code=%s""", (nilai, branch_code))
    if not n:
        raise ValueError(f"Cabang '{branch_code}' tidak ada di master cabang")
    return nilai


def pilihan_kelas():
    """Daftar untuk layar admin: kelas dari master + kelas khusus SEMUA."""
    return [KELAS_SEMUA] + [k for k in daftar_kelas() if k != KELAS_SEMUA]


def kode_tak_dikenal(kode_list):
    """Kode cabang mana saja dari daftar ini yang TIDAK ada di master.

    Diperiksa sekali untuk seluruh daftar, bukan satu per satu, supaya
    admin melihat semua kesalahan sekaligus alih-alih membetulkannya
    berulang kali."""
    kode_list = _bersihkan_kode(kode_list)
    if not kode_list:
        return []
    # Satu parameter saja, isinya seluruh daftar (bukan satu %s per kode).
    ada = {b["branch_code"] for b in db.q(
        "SELECT branch_code FROM branchops_branches WHERE branch_code = ANY(%s)",
        [list(kode_list)])}
    return [k for k in kode_list if k not in ada]


def periksa_jatah(kelas, kode_list):
    """Bersihkan sepasang (region_class, branch_codes) sebelum disimpan.

    Mengembalikan (kelas_bersih, daftar_kode) — paling banyak satu terisi,
    sisanya None. Melempar ValueError bila isiannya tidak masuk akal.

    Dipakai bersama oleh scoping.set_jatah() dan endpoint pengguna di
    app.py, supaya kedua jalur masuk memakai aturan yang persis sama."""
    kelas = (kelas or "").strip()
    kode_list = _bersihkan_kode(kode_list)
    if kelas and kode_list:
        raise ValueError("Satu pengguna hanya boleh punya SATU jatah: "
                         "wilayah saja, atau daftar cabang saja.")
    if kelas:
        if kelas != KELAS_SEMUA and kelas not in daftar_kelas():
            raise ValueError(f"Wilayah '{kelas}' tidak ada atau sedang nonaktif. "
                             f"Kelola daftarnya di tab Master Data.")
        return kelas, None
    if kode_list:
        # Kode tak dikenal DITOLAK, bukan disaring diam-diam. Menyaringnya
        # akan membuat admin mengira pengguna memegang 3 cabang padahal
        # yang tersimpan 2, dan selisihnya tidak muncul di layar mana pun.
        hilang = kode_tak_dikenal(kode_list)
        if hilang:
            raise ValueError(
                f"Cabang tidak ada di master cabang: {', '.join(hilang)}. "
                f"Unggah master cabang dulu di tab Unggah.")
        return None, kode_list
    # Dua-duanya kosong = sengaja tidak dijatah = tidak melihat apa pun.
    return None, None


def set_jatah(uid, kelas=None, kode_list=None):
    """Simpan jatah seorang pengguna. Mengembalikan (kelas, kode) tersimpan.

    SELALU menulis kedua kolom sekaligus. Menetapkan salah satu jenis jatah
    otomatis MENGOSONGKAN yang lain — keduanya saling meniadakan, jadi
    menyisakan nilai lama di kolom satunya hanya akan ditolak CHECK di basis
    data (atau, lebih buruk, tersimpan dan bermakna ganda).

    Nilai yang tidak dikenal ditolak, supaya salah ketik tidak diam-diam
    membuat pengguna kehilangan seluruh akses tanpa pesan apa pun."""
    kelas, kode_list = periksa_jatah(kelas, kode_list)
    db.execute("""UPDATE branchops_users SET region_class=%s, branch_codes=%s
                   WHERE id=%s""", (kelas, kode_list, uid))
    return kelas, kode_list


def set_kelas(uid, kelas):
    """Bentuk lama: menjatah wilayah saja. Ikut mengosongkan jatah cabang."""
    return set_jatah(uid, kelas=kelas, kode_list=None)[0]
