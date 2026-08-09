// Panduan Pengguna Branch Ops — pembuat berkas .docx
// Dijalankan dengan: node manual.js
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType,
  Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle,
  PageBreak, LevelFormat, Footer, PageNumber, HeightRule, VerticalAlign,
} = require("docx");
const fs = require("fs");

// ---------------------------------------------------------------- warna
const BIRU = "1D4ED8";
const ABU = "6B7280";
const ABU_MUDA = "F3F4F6";
const MERAH = "B91C1C";
const HIJAU = "15803D";
const KUNING = "92400E";

// ---------------------------------------------------------------- bantu
const P = (text, opt = {}) =>
  new Paragraph({ children: [new TextRun({ text, ...opt.run })], ...opt.par });

const H1 = (text) =>
  new Paragraph({ text, heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 160 } });

const H2 = (text) =>
  new Paragraph({ text, heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 120 } });

const H3 = (text) =>
  new Paragraph({ text, heading: HeadingLevel.HEADING_3, spacing: { before: 220, after: 100 } });

const teks = (text) =>
  new Paragraph({ children: [new TextRun({ text, size: 21 })], spacing: { after: 120 }, alignment: AlignmentType.JUSTIFIED });

// paragraf dengan potongan tebal/miring
const rich = (runs) =>
  new Paragraph({
    children: runs.map((r) =>
      typeof r === "string"
        ? new TextRun({ text: r, size: 21 })
        : new TextRun({ size: 21, ...r })),
    spacing: { after: 120 },
    alignment: AlignmentType.JUSTIFIED,
  });

const butir = (text, level = 0) =>
  new Paragraph({
    children: [new TextRun({ text, size: 21 })],
    numbering: { reference: "butir", level },
    spacing: { after: 60 },
  });

// Daftar bernomor. Setiap daftar HARUS memakai instance berbeda, kalau tidak
// nomornya menyambung dari daftar sebelumnya — bagian 6.3 pernah mulai dari
// angka 4 karena bagian 2.1 sudah memakai 1-3.
let instLangkah = 0;
const daftarBaru = () => { instLangkah += 1; };
const langkah = (text) =>
  new Paragraph({
    children: [new TextRun({ text, size: 21 })],
    numbering: { reference: "langkah", level: 0, instance: instLangkah },
    spacing: { after: 80 },
  });

// label peran, mis. [EDITOR] atau [EDITOR + VIEWER]
const peran = (label, warna) =>
  new Paragraph({
    children: [new TextRun({ text: label, bold: true, size: 17, color: warna, allCaps: true })],
    spacing: { after: 100 },
  });

const PERAN_KEDUA = () => peran("Untuk peran: Editor dan Viewer", BIRU);
const PERAN_EDITOR = () => peran("Untuk peran: Editor saja", HIJAU);

// kotak catatan berwarna
function kotak(judul, isi, warna, latar) {
  return new Table({
    width: { size: 9360, type: WidthType.DXA },
    columnWidths: [9360],
    borders: {
      top: { style: BorderStyle.SINGLE, size: 2, color: warna },
      bottom: { style: BorderStyle.SINGLE, size: 2, color: warna },
      left: { style: BorderStyle.SINGLE, size: 18, color: warna },
      right: { style: BorderStyle.SINGLE, size: 2, color: warna },
      insideHorizontal: { style: BorderStyle.NONE },
      insideVertical: { style: BorderStyle.NONE },
    },
    rows: [
      new TableRow({
        children: [
          new TableCell({
            width: { size: 9360, type: WidthType.DXA },
            shading: { type: ShadingType.CLEAR, fill: latar },
            margins: { top: 140, bottom: 140, left: 180, right: 180 },
            children: [
              new Paragraph({
                children: [new TextRun({ text: judul, bold: true, size: 20, color: warna })],
                spacing: { after: 60 },
              }),
              ...isi.map((t) =>
                new Paragraph({
                  children: [new TextRun({ text: t, size: 20 })],
                  spacing: { after: 40 },
                })),
            ],
          }),
        ],
      }),
    ],
  });
}

const PENTING = (isi) => kotak("PENTING", isi, MERAH, "FEF2F2");
const CATATAN = (isi) => kotak("Catatan", isi, BIRU, "EFF6FF");
const HATI = (isi) => kotak("Hati-hati", isi, KUNING, "FFFBEB");

// tempat tangkapan layar — kotak setinggi ~4 cm supaya gambar benar-benar muat
let noGambar = 0;
function gambar(keterangan) {
  noGambar += 1;
  const garis = { style: BorderStyle.DASHED, size: 6, color: "9CA3AF" };
  return [
    new Table({
      width: { size: 9360, type: WidthType.DXA },
      columnWidths: [9360],
      borders: { top: garis, bottom: garis, left: garis, right: garis,
                 insideHorizontal: { style: BorderStyle.NONE },
                 insideVertical: { style: BorderStyle.NONE } },
      rows: [
        new TableRow({
          height: { value: 2300, rule: HeightRule.ATLEAST },
          children: [
            new TableCell({
              width: { size: 9360, type: WidthType.DXA },
              verticalAlign: VerticalAlign.CENTER,
              children: [
                new Paragraph({
                  alignment: AlignmentType.CENTER,
                  children: [new TextRun({
                    text: "[ tempelkan tangkapan layar di sini ]",
                    color: "9CA3AF", size: 19, italics: true })],
                }),
              ],
            }),
          ],
        }),
      ],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      spacing: { before: 60, after: 200 },
      children: [new TextRun({ text: `Gambar ${noGambar} — ${keterangan}`, size: 18, color: ABU, italics: true })],
    }),
  ];
}

// tabel biasa
function tabel(headers, rows, widths) {
  const total = widths.reduce((a, b) => a + b, 0);
  const sel = (text, opt = {}) =>
    new TableCell({
      width: { size: opt.w, type: WidthType.DXA },
      shading: opt.head ? { type: ShadingType.CLEAR, fill: ABU_MUDA } : undefined,
      margins: { top: 90, bottom: 90, left: 120, right: 120 },
      children: [
        new Paragraph({
          children: [new TextRun({ text, bold: !!opt.head, size: 19 })],
        }),
      ],
    });
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: widths,
    borders: {
      top: { style: BorderStyle.SINGLE, size: 2, color: "D1D5DB" },
      bottom: { style: BorderStyle.SINGLE, size: 2, color: "D1D5DB" },
      left: { style: BorderStyle.SINGLE, size: 2, color: "D1D5DB" },
      right: { style: BorderStyle.SINGLE, size: 2, color: "D1D5DB" },
      insideHorizontal: { style: BorderStyle.SINGLE, size: 1, color: "E5E7EB" },
      insideVertical: { style: BorderStyle.SINGLE, size: 1, color: "E5E7EB" },
    },
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) => sel(h, { head: true, w: widths[i] })),
      }),
      ...rows.map((r) =>
        new TableRow({ children: r.map((c, i) => sel(c, { w: widths[i] })) })),
    ],
  });
}

const spasi = (n = 120) => new Paragraph({ text: "", spacing: { after: n } });

// ================================================================ ISI
const isi = [];

// ---------------------------------------------------------- halaman judul
isi.push(
  new Paragraph({ text: "", spacing: { after: 1800 } }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 120 },
    children: [new TextRun({ text: "PANDUAN PENGGUNA", bold: true, size: 30, color: ABU })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 100 },
    children: [new TextRun({ text: "Branch Operations and", bold: true, size: 52, color: BIRU })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 400 },
    children: [new TextRun({ text: "Transactions Monitoring", bold: true, size: 52, color: BIRU })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 1200 },
    border: { top: { style: BorderStyle.SINGLE, size: 6, color: BIRU } },
    children: [new TextRun({ text: "" })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 100 },
    children: [new TextRun({ text: "Untuk pengguna berperan EDITOR dan VIEWER", bold: true, size: 24 })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    spacing: { after: 1600 },
    children: [new TextRun({ text: "Panduan ini tidak membahas tugas admin.", size: 20, color: ABU, italics: true })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "USECASE-STUDIO.xyz", size: 20, color: ABU })],
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "Edisi Agustus 2026", size: 20, color: ABU })],
  }),
  new Paragraph({ children: [new PageBreak()] }),
);

// ---------------------------------------------------------- daftar isi
// Daftar isi ditulis manual, BUKAN sebagai field otomatis Word. Field
// otomatis tampil KOSONG sampai pembacanya menekan "Update Field" — dan
// halaman kosong terbaca sebagai dokumen rusak. Nomor bagian sudah cukup
// untuk menavigasi dokumen sependek ini.
isi.push(H1("Daftar Isi"));
const daftarIsi = [
  ["1.", "Sebelum Mulai", "Peran, penyamaran nama, jatah cabang, hak menu"],
  ["2.", "Masuk dan Keluar", "Cara masuk, keluar otomatis, keluar sendiri"],
  ["3.", "Mengenal Layar", "Menu, penyaring, mengunduh tabel"],
  ["4.", "Beranda", "Kartu menu dan daftar TBO yang masih terbuka"],
  ["5.", "Keempat Dashboard", "Break Deposito, Pencairan, TBO, Rekonsiliasi"],
  ["6.", "Mengunggah Berkas Excel", "Editor saja — tiga jenis berkas, langkah, dan jebakannya"],
  ["7.", "Mengubah Data", "Editor saja — ubah TBO, pencairan, tindak lanjut"],
  ["8.", "Kalau Ada Masalah", "Gejala yang sering ditemui dan penyelesaiannya"],
  ["9.", "Daftar Istilah", "Arti kata yang dipakai di layar"],
];
daftarIsi.forEach(([no, judul, ket]) => {
  isi.push(new Paragraph({
    spacing: { after: 30 },
    indent: { left: 260 },
    children: [
      new TextRun({ text: `${no}  `, bold: true, size: 22, color: BIRU }),
      new TextRun({ text: judul, bold: true, size: 22 }),
    ],
  }));
  isi.push(new Paragraph({
    spacing: { after: 140 },
    indent: { left: 560 },
    children: [new TextRun({ text: ket, size: 19, color: ABU })],
  }));
});
isi.push(new Paragraph({ children: [new PageBreak()] }));

// ---------------------------------------------------------- 1 pendahuluan
isi.push(H1("1. Sebelum Mulai"));

isi.push(H2("1.1 Untuk siapa panduan ini"));
isi.push(teks(
  "Panduan ini ditujukan bagi pengguna aplikasi Branch Operations and Transactions Monitoring " +
  "yang berperan sebagai Editor atau Viewer. Tugas admin — menambah pengguna, mengatur hak menu, " +
  "mengubah master data — tidak dibahas di sini."));
isi.push(teks("Setiap bagian diberi penanda peran di bagian atasnya:"));

isi.push(tabel(
  ["Peran", "Yang bisa dilakukan"],
  [
    ["Viewer", "Melihat seluruh dashboard, menyaring data, dan mengunduh tabel ke CSV. Tidak bisa mengubah atau mengunggah apa pun."],
    ["Editor", "Semua yang bisa dilakukan Viewer, ditambah mengunggah berkas Excel dan mengubah data TBO serta pencairan."],
    ["Admin", "Semua yang bisa dilakukan Editor, ditambah mengelola pengguna, hak menu, master data dan pengaturan. Di luar cakupan panduan ini."],
  ],
  [1500, 7860]));
isi.push(spasi());

isi.push(H2("1.2 Tiga hal yang perlu dipahami lebih dulu"));
isi.push(teks(
  "Tiga aturan berikut berlaku di seluruh aplikasi. Banyak pertanyaan yang muncul di hari-hari " +
  "pertama sebenarnya terjawab oleh salah satu dari ketiganya."));

isi.push(H3("a. Nama nasabah selalu tersamar"));
isi.push(rich([
  "Di seluruh layar, nama nasabah tampil sebagai ",
  { text: "***", bold: true },
  ". Ini disengaja dan berlaku untuk semua peran, termasuk admin. Penyamaran dilakukan di server, " +
  "bukan di layar, sehingga nama asli juga tidak ikut terbawa saat tabel diunduh ke CSV.",
]));
isi.push(rich([
  { text: "Akibatnya bagi pekerjaan sehari-hari: ", bold: true },
  "baris dibedakan lewat nomor rekening, nomor deposito, atau nomor CIF — bukan lewat nama. " +
  "Karena itu kotak pencarian pun mencari berdasarkan nomor, bukan nama.",
]));
isi.push(teks("Nama pegawai (CS, teller, FLM) tidak disamarkan, karena yang wajib dilindungi adalah data nasabah."));

isi.push(H3("b. Anda hanya melihat cabang yang menjadi jatah Anda"));
isi.push(rich([
  "Setiap pengguna diberi ",
  { text: "jatah cabang", bold: true },
  " oleh admin — bisa berupa satu wilayah, bisa berupa daftar cabang tertentu. Seluruh angka yang " +
  "Anda lihat, termasuk KPI dan grafik di Beranda, sudah dibatasi jatah itu.",
]));
isi.push(teks(
  "Jadi kalau jumlah di layar Anda berbeda dengan jumlah di layar rekan kerja, itu bukan kesalahan " +
  "aplikasi — jatah Anda berdua memang berbeda. Kalau Anda merasa seharusnya melihat sebuah cabang " +
  "tetapi cabang itu tidak muncul, hubungi admin."));
isi.push(CATATAN([
  "Pengguna yang belum diberi jatah sama sekali tidak melihat baris apa pun. Layar akan tampak kosong, bukan penuh.",
]));

isi.push(H3("c. Menu yang tampil mengikuti hak peran Anda"));
isi.push(teks(
  "Admin dapat mengatur menu mana yang boleh dibuka oleh tiap peran. Karena itu daftar menu di " +
  "bagian atas layar Anda bisa lebih pendek daripada yang tertulis di panduan ini. Menu yang tidak " +
  "menjadi hak Anda tidak akan tampil, dan tetap ditolak server kalau alamatnya dibuka langsung."));
isi.push(teks("Menu Beranda selalu tersedia untuk semua peran dan tidak dapat dicabut."));

isi.push(new Paragraph({ children: [new PageBreak()] }));

// ---------------------------------------------------------- 2 masuk
isi.push(H1("2. Masuk dan Keluar"));
isi.push(PERAN_KEDUA());

isi.push(H2("2.1 Masuk ke aplikasi"));
daftarBaru();
isi.push(langkah("Buka alamat aplikasi di peramban, lalu tambahkan /branchops di belakangnya."));
isi.push(langkah("Isi Email dan Password sesuai akun yang diberikan admin."));
isi.push(langkah("Klik tombol Sign In."));
isi.push(teks("Setelah berhasil, Anda akan mendarat di halaman Beranda."));
isi.push(...gambar("Halaman masuk Branch Operations"));

isi.push(PENTING([
  "Akun Branch Ops hanya berlaku untuk Branch Ops. Akun dashboard lain (PMO, People Development, " +
  "Service Quality, E-Library) tidak bisa dipakai di sini, dan sebaliknya.",
]));
isi.push(spasi());

isi.push(H2("2.2 Keluar otomatis kalau layar dibiarkan"));
isi.push(rich([
  "Kalau layar dibiarkan tanpa disentuh selama batas waktu yang ditetapkan admin, aplikasi akan " +
  "mengeluarkan Anda sendiri dan kembali ke halaman masuk. Halaman itu akan memberi keterangan " +
  "bahwa Anda keluar karena layar menganggur — ",
  { text: "itu bukan kerusakan", bold: true },
  ".",
]));
isi.push(teks("Hitungannya berhenti sementara selama dua keadaan, supaya Anda tidak terlempar keluar di saat yang paling merepotkan:"));
isi.push(butir("Selama berkas sedang diunggah atau data sedang dimuat."));
isi.push(butir("Selama kotak “pilih berkas” milik Windows sedang terbuka."));
isi.push(teks("Bekerja di satu tab akan menjaga tab Branch Ops lain tetap hidup — hitungannya dibagi bersama."));
isi.push(CATATAN([
  "Fitur ini menutup layar yang ditinggal terbuka. Ia tidak menggantikan kebiasaan menekan Keluar " +
  "kalau Anda meninggalkan komputer di tempat umum.",
]));
isi.push(spasi());

isi.push(H2("2.3 Keluar sendiri"));
isi.push(teks("Klik Keluar di pojok kanan atas. Anda akan kembali ke halaman masuk."));

isi.push(new Paragraph({ children: [new PageBreak()] }));

// ---------------------------------------------------------- 3 mengenal layar
isi.push(H1("3. Mengenal Layar"));
isi.push(PERAN_KEDUA());

isi.push(H2("3.1 Menu di bagian atas"));
isi.push(teks("Menu berikut mungkin tidak seluruhnya tampil, tergantung hak peran Anda."));
isi.push(tabel(
  ["Menu", "Isinya", "Peran"],
  [
    ["Beranda", "Ringkasan singkat dan daftar TBO yang masih terbuka", "Semua"],
    ["Break Deposito", "Pencairan sebelum jatuh tempo menurut data IT Group", "Semua"],
    ["Pencairan", "Seluruh pencairan deposito yang dilaporkan cabang", "Semua"],
    ["TBO", "Pembukaan rekening yang dokumennya belum lengkap", "Semua"],
    ["Rekonsiliasi", "Perbandingan data IT dengan laporan cabang", "Semua"],
    ["Unggah", "Mengunggah berkas Excel dan melihat riwayatnya", "Editor"],
    ["Master Data, Pengguna, Pengaturan, Audit", "Pengelolaan aplikasi", "Admin"],
  ],
  [2100, 5560, 1700]));
isi.push(spasi());
isi.push(...gambar("Menu di bagian atas layar"));

isi.push(H2("3.2 Penyaring yang sama di keempat dashboard"));
isi.push(teks("Di bawah judul dashboard ada sederet penyaring. Setelah diubah, tabel dan grafik langsung menyesuaikan."));
isi.push(tabel(
  ["Penyaring", "Kegunaan"],
  [
    ["Dari tanggal / Sampai tanggal", "Membatasi periode. Terisi otomatis mengikuti rentang data yang tersedia pada menu itu."],
    ["Cabang", "Menampilkan satu cabang saja. Daftarnya hanya memuat cabang yang menjadi jatah Anda."],
    ["Tipe", "Menyaring menurut KC, KCP atau Pusat."],
    ["Status", "Hanya di menu Rekonsiliasi."],
    ["Duplikat dikecualikan", "Hanya di menu Pencairan. Menentukan apakah baris kembar ikut dihitung."],
    ["Reset", "Mengembalikan seluruh penyaring ke keadaan awal."],
  ],
  [2800, 6560]));
isi.push(spasi());
isi.push(PENTING([
  "Setiap menu punya rentang tanggalnya sendiri. Pindah menu tidak membawa serta tanggal yang Anda " +
  "pilih di menu sebelumnya, karena ketiga jenis data punya periode yang berbeda.",
]));
isi.push(spasi());

isi.push(H2("3.3 Mengunduh tabel"));
isi.push(rich([
  "Tombol ",
  { text: "Unduh tabel (CSV)", bold: true },
  " di kanan atas menyimpan isi tabel yang sedang tampil. Yang terunduh persis sama dengan yang " +
  "terlihat di layar — termasuk hasil penyaringan dan hasil pencarian. Nama nasabah tetap tersamar " +
  "di dalam berkas CSV.",
]));
isi.push(HATI([
  "Berkas CSV berisi data internal: nomor rekening, nominal dan nama cabang. Perlakukan seperti " +
  "dokumen kerja, jangan disebarkan di luar keperluan.",
]));

isi.push(new Paragraph({ children: [new PageBreak()] }));

// ---------------------------------------------------------- 4 beranda
isi.push(H1("4. Beranda"));
isi.push(PERAN_KEDUA());
isi.push(teks("Beranda adalah halaman pertama sesudah masuk. Isinya dua bagian."));

isi.push(H2("4.1 Kartu menu"));
isi.push(teks(
  "Deretan kartu di bagian atas memuat jumlah ringkas tiap dashboard, dan berfungsi sebagai " +
  "pintasan — klik kartunya untuk membuka menu bersangkutan. Kartu hanya muncul untuk menu yang " +
  "menjadi hak peran Anda."));

isi.push(H2("4.2 TBO yang masih terbuka"));
isi.push(teks(
  "Daftar ini menggabungkan dua sumber: TBO dari pembukaan rekening dan TBO dari pencairan " +
  "deposito. Urutannya dimulai dari yang paling lama terlambat, sehingga yang paling perlu " +
  "ditangani selalu berada di atas."));
isi.push(teks("Kolom Sumber menunjukkan asal barisnya, dan itu menentukan tombol mana yang tersedia:"));
isi.push(butir("tbo — berasal dari data pembukaan rekening (menu TBO)."));
isi.push(butir("pencairan — berasal dari data pencairan deposito (menu Pencairan)."));
isi.push(rich([
  { text: "Editor ", bold: true },
  "akan melihat tombol Ubah dan Tandai lengkap pada tiap baris. ",
  { text: "Viewer ", bold: true },
  "hanya melihat daftarnya.",
]));
isi.push(...gambar("Beranda — kartu menu dan daftar TBO yang masih terbuka"));

isi.push(new Paragraph({ children: [new PageBreak()] }));

// ---------------------------------------------------------- 5 dashboard
isi.push(H1("5. Keempat Dashboard"));
isi.push(PERAN_KEDUA());

isi.push(H2("5.1 Break Deposito"));
isi.push(teks(
  "Judul lengkapnya “Data Break Deposito (dari IT Group)”. Berisi pencairan deposito yang " +
  "dilakukan sebelum jatuh tempo, diambil langsung dari sistem inti. Karena sumbernya sistem, " +
  "kolomnya terisi penuh dan angkanya layak dipakai sebagai pembanding laporan cabang."));
isi.push(teks("Kartu ringkasan yang tersedia:"));
isi.push(tabel(
  ["Kartu", "Artinya"],
  [
    ["Nominal break", "Total nilai pencairan sebelum jatuh tempo"],
    ["Penalti dipungut", "Total penalti, dan berapa banyak break yang lolos tanpa penalti"],
    ["Rate tertimbang", "Rata-rata suku bunga yang ditimbang nominal, bukan rata-rata biasa"],
    ["Durasi proses", "Waktu median dari awal sampai akhir proses break"],
    ["Di luar jam operasional", "Transaksi di luar jam kerja yang ditetapkan admin"],
    ["Via rekening perantara", "Dana tidak langsung masuk ke rekening nasabah"],
  ],
  [2800, 6560]));
isi.push(spasi());
isi.push(teks(
  "Di bawahnya tersedia grafik tren harian, sebaran jam transaksi, cabang dengan nominal " +
  "tertinggi, distribusi rate, konsentrasi nasabah, dan tabel detail transaksi."));
isi.push(CATATAN([
  "Nama panjang dipotong 20 karakter oleh sistem inti, sehingga dua nasabah berbeda bisa tampak " +
  "sama. Baris yang terpotong diberi tanda pada bagian konsentrasi nasabah.",
]));
isi.push(spasi());
isi.push(...gambar("Menu Break Deposito"));

isi.push(H2("5.2 Pencairan"));
isi.push(teks(
  "Judul lengkapnya “Seluruh Pencairan Deposito (dari Cabang)”. Berisi laporan pencairan yang " +
  "dikirim cabang. Urutan bagiannya dari atas ke bawah:"));
isi.push(butir("Kartu ringkasan: arus keluar dana, rollover, penempatan kembali, kelengkapan data."));
isi.push(butir("Arus dana dan volume — komposisi arus dana dan tren harian."));
isi.push(butir("Pencairan dipercepat vs sesuai jatuh tempo."));
isi.push(butir("Detail transaksi."));
isi.push(butir("Rincian per cabang menurut jenis pencairan — dapat dibuka-tutup."));
isi.push(spasi());
isi.push(PENTING([
  "Tabel “Detail transaksi” di menu ini HANYA menampilkan baris yang memiliki Data TBO.",
  "Ini disengaja: menu Pencairan dipakai untuk menindaklanjuti dokumen yang masih menggantung. " +
  "Kartu ringkasan dan grafik di atasnya tetap menghitung SELURUH pencairan, bukan yang ber-TBO saja.",
]));
isi.push(spasi());
isi.push(teks(
  "Kalau jumlah baris ber-TBO lebih banyak daripada yang dapat ditampilkan sekaligus, akan muncul " +
  "pemberitahuan di atas tabel. Persempit rentang tanggal atau pilih satu cabang untuk melihat sisanya."));
isi.push(rich([
  { text: "Mencari satu transaksi: ", bold: true },
  "gunakan kotak pencarian di atas tabel dan ketik nomor deposito. Tanda baca diabaikan, sehingga " +
  "0012-3456 tetap menemukan 00123456. Tekan Enter atau klik tombol cari. Untuk menampilkan seluruh " +
  "baris kembali, kosongkan kotaknya.",
]));
isi.push(...gambar("Menu Pencairan — bagian Detail transaksi"));

isi.push(H2("5.3 TBO"));
isi.push(teks(
  "Judul lengkapnya “Pembukaan Rekening dengan TBO (dari Cabang)”. TBO adalah rekening yang sudah " +
  "dibuka tetapi dokumen persyaratannya belum lengkap. Menu ini memantau berapa lama dokumen itu " +
  "masih menggantung."));
isi.push(tabel(
  ["Istilah di layar", "Artinya"],
  [
    ["TBO outstanding", "Dokumen belum lengkap dan masih dihitung keterlambatannya"],
    ["Lengkap", "Dokumen sudah dipenuhi; keterlambatan berhenti dihitung"],
    ["Dikecualikan", "Baris yang memang tidak memerlukan dokumen TBO"],
    ["Target Pemenuhan TBO", "Tanggal batas dokumen harus lengkap"],
    ["Terlambat", "Jumlah hari melewati target. Tanda “—” berarti belum ada target, bukan tepat waktu"],
    ["Aging", "Usia hari sejak data diinput, untuk baris yang masih outstanding"],
  ],
  [2800, 6560]));
isi.push(spasi());
isi.push(PENTING([
  "Kolom Terlambat dihitung ulang setiap kali layar dibuka, bukan disimpan. Angka yang Anda lihat " +
  "hari ini akan bertambah sendiri besok selama statusnya masih Outstanding.",
]));
isi.push(spasi());
isi.push(rich([
  { text: "Mencari satu rekening: ", bold: true },
  "kotak pencarian di menu ini mencari berdasarkan ",
  { text: "nomor rekening", bold: true },
  ", bukan nama. Alasannya ada di bagian 1.2 — seluruh nama tampil sebagai ***, sehingga pencarian " +
  "nama tidak akan menemukan apa pun.",
]));
isi.push(...gambar("Menu TBO"));

isi.push(H2("5.4 Rekonsiliasi"));
isi.push(teks(
  "Membandingkan data IT dengan laporan cabang untuk periode yang sama, lalu mengelompokkan hasilnya:"));
isi.push(tabel(
  ["Status", "Artinya", "Yang perlu dilakukan"],
  [
    ["Cocok", "Kedua sumber sepakat", "Tidak ada"],
    ["Selisih material", "Nominal berbeda melebihi batas toleransi", "Telusuri ke cabang"],
    ["Tidak dilaporkan cabang", "Ada di data IT, tidak ada di laporan cabang", "Minta cabang melengkapi laporan"],
    ["Tidak ada di data IT", "Dilaporkan cabang, tidak ditemukan di data IT", "Periksa ulang laporan cabang"],
  ],
  [2300, 3900, 3160]));
isi.push(spasi());
isi.push(teks(
  "Kolom Tindak lanjut menandai proses penanganan, dimulai dari “Belum ditinjau”. Editor dapat " +
  "mengubah tindak lanjut dan menambahkan catatan; Viewer hanya melihat."));
isi.push(CATATAN([
  "Menu Rekonsiliasi tidak memiliki tombol unggah, dan memang tidak akan pernah punya. Barisnya " +
  "bukan hasil unggahan melainkan hasil perbandingan dua tabel lain.",
]));
isi.push(...gambar("Menu Rekonsiliasi"));

isi.push(new Paragraph({ children: [new PageBreak()] }));

// ---------------------------------------------------------- 6 unggah
isi.push(H1("6. Mengunggah Berkas Excel"));
isi.push(PERAN_EDITOR());
isi.push(teks(
  "Bagian ini hanya berlaku untuk peran Editor. Viewer tidak akan melihat tombol maupun menu unggah."));

isi.push(H2("6.1 Tiga jenis berkas"));
isi.push(tabel(
  ["Jenis berkas", "Asalnya", "Masuk ke menu"],
  [
    ["Data Transaksi dari IT (break deposito)", "Export dari IT Group", "Break Deposito"],
    ["Data dari Cabang — Pencairan Deposito", "Laporan cabang", "Pencairan"],
    ["Data dari Cabang — Buka Rekening TBO", "Laporan cabang", "TBO"],
  ],
  [4200, 2900, 2260]));
isi.push(spasi());
isi.push(PENTING([
  "Susunan kolom pada berkas Excel harus persis sama dengan template. Aplikasi membaca kolom " +
  "menurut POSISI, bukan menurut judulnya.",
  "Menyisipkan kolom baru di tengah TIDAK akan memunculkan pesan galat — datanya hanya akan masuk " +
  "ke kolom yang salah, diam-diam. Kalau perlu menambah kolom, letakkan di paling kanan dan " +
  "beri tahu admin lebih dulu.",
]));
isi.push(spasi());
isi.push(teks("Template ketiga berkas tersedia di folder contoh dan sudah diuji terbaca tanpa baris ditolak."));

isi.push(H2("6.2 Dua cara mengunggah"));
isi.push(teks("Keduanya menuju proses yang sama persis, jadi pilih yang paling dekat dengan pekerjaan Anda."));
isi.push(butir("Lewat menu Unggah — pilih jenis berkas, lalu pilih berkasnya."));
isi.push(butir("Lewat tombol di dalam dashboard Break Deposito, Pencairan atau TBO — jenis berkasnya sudah ditentukan oleh menu yang sedang dibuka."));
isi.push(teks("Tombol di dalam dashboard berlabel sesuai menunya, misalnya “Unggah Data Pencairan” saat Anda berada di menu Pencairan."));
isi.push(...gambar("Tombol unggah di dalam dashboard"));

isi.push(H2("6.3 Langkah mengunggah"));
daftarBaru();
isi.push(langkah("Pilih berkas .xlsx yang akan diunggah."));
isi.push(langkah("Tunggu sebentar. Aplikasi membaca dan memeriksa isinya."));
isi.push(langkah("Baca ringkasan yang muncul: berapa baris terbaca, berapa akan masuk, berapa ditolak, berapa berperingatan."));
isi.push(langkah("Baca daftar penolakan kalau ada. Daftarnya dikelompokkan menurut jenis masalah beserta nomor barisnya."));
isi.push(langkah("Kalau hasilnya sudah benar, klik Komit. Kalau belum, klik Batalkan, perbaiki berkasnya, lalu ulangi."));
isi.push(spasi());
isi.push(PENTING([
  "Data BELUM masuk dashboard sampai Anda menekan Komit.",
  "Unggahan berhenti sebagai draft dengan sengaja, supaya daftar penolakan sempat dibaca. Menutup " +
  "kotak dialog tanpa menekan Komit maupun Batalkan akan meninggalkan draft yang menggantung — " +
  "bereskan lewat menu Unggah.",
]));
isi.push(spasi());
isi.push(rich([
  "Tombol ",
  { text: "Unduh catatan (CSV)", bold: true },
  " menyimpan seluruh temuan validasi ke satu berkas, berguna kalau berkasnya perlu dikembalikan " +
  "ke cabang untuk diperbaiki.",
]));
isi.push(...gambar("Ringkasan hasil pemeriksaan berkas sebelum dikomit"));

isi.push(H2("6.4 Anda hanya boleh mengunggah data cabang jatah Anda"));
isi.push(teks(
  "Kalau berkas memuat satu saja cabang di luar jatah Anda, SELURUH berkas ditolak dan tidak ada " +
  "satu baris pun yang tersimpan. Layar akan menyebutkan kode cabang yang bermasalah."));
isi.push(teks("Kalau itu terjadi, ada dua jalan keluar:"));
isi.push(butir("Unggah berkas yang hanya berisi cabang jatah Anda."));
isi.push(butir("Minta admin yang mengunggah berkas gabungan tersebut."));
isi.push(CATATAN([
  "Baris di luar jatah tidak disaring diam-diam, melainkan ditolak seluruhnya. Ini disengaja: " +
  "berkas yang tersaring sebagian membuat orang mengira seluruh kiriman sudah masuk.",
]));
isi.push(spasi());

isi.push(H2("6.5 Mengganti unggahan yang sudah terlanjur dikomit"));
isi.push(HATI([
  "Mengunggah berkas perbaikan TIDAK otomatis membatalkan unggahan lama, kecuali rentang " +
  "tanggalnya sama persis.",
  "Kalau tanggalnya bergeser walau sehari — misalnya karena satu tanggal diperbaiki — kedua batch " +
  "akan sama-sama aktif dan transaksi yang sama terhitung dua kali. Tidak ada pesan galat yang muncul.",
]));
isi.push(teks("Karena itu, kalau tujuan Anda MENGGANTI unggahan sebelumnya dan bukan menambah periode baru:"));
daftarBaru();
isi.push(langkah("Buka menu Unggah."));
isi.push(langkah("Cari batch lama pada daftar Riwayat unggahan."));
isi.push(langkah("Klik Batal pada batch itu."));
isi.push(langkah("Baru unggah dan komit berkas perbaikannya."));
isi.push(spasi());
isi.push(teks(
  "Membatalkan lebih aman daripada menghapus. Batch yang dibatalkan hilang dari seluruh dashboard " +
  "tetapi datanya tetap tersimpan, dan sewaktu-waktu dapat dikomit kembali."));

isi.push(H2("6.6 Membaca Riwayat unggahan"));
isi.push(tabel(
  ["Kolom", "Artinya"],
  [
    ["Lingkup", "Kode cabang bila berkas itu hanya berisi satu cabang, atau “se-bank” bila mencakup banyak cabang. Menentukan batch lama mana yang tergantikan saat dikomit."],
    ["Status draft", "Sudah terunggah, belum tampil di dashboard"],
    ["Status committed", "Aktif dan tampil di dashboard"],
    ["Status dibatalkan", "Tidak tampil, tetapi datanya masih tersimpan"],
  ],
  [2200, 7160]));
isi.push(spasi());
isi.push(...gambar("Menu Unggah — Riwayat unggahan"));

isi.push(new Paragraph({ children: [new PageBreak()] }));

// ---------------------------------------------------------- 7 mengubah
isi.push(H1("7. Mengubah Data"));
isi.push(PERAN_EDITOR());
isi.push(teks(
  "Editor dapat memperbaiki sebagian data tanpa perlu mengunggah ulang berkas Excel. Setiap " +
  "perubahan tercatat dalam jejak audit beserta nama pengguna dan waktunya."));

isi.push(H2("7.1 Ubah data TBO"));
isi.push(teks("Dari menu TBO atau dari daftar di Beranda, klik Ubah pada baris yang bersangkutan."));
isi.push(teks("Yang umumnya perlu diubah:"));
isi.push(butir("Target Pemenuhan TBO — tanggal batas dokumen harus lengkap."));
isi.push(butir("Status TBO — Outstanding, Lengkap, atau Dikecualikan."));
isi.push(butir("Dokumen TBO dan keterangan."));
isi.push(spasi());
isi.push(teks(
  "Beberapa kolom identitas sengaja dikunci dan tampil abu-abu: kode cabang, tanggal input, " +
  "nomor CIF, nomor rekening, nama pemilik dan tanggal penempatan. Kolom itu ditampilkan — bukan " +
  "disembunyikan — supaya jelas datanya tetap ada, hanya tidak boleh diubah dari sini."));
isi.push(CATATAN([
  "Tombol Tandai lengkap di Beranda adalah jalan pintas untuk mengubah status menjadi Lengkap " +
  "tanpa membuka kotak dialog.",
]));
isi.push(...gambar("Kotak dialog Ubah data TBO"));

isi.push(H2("7.2 Ubah data pencairan"));
isi.push(teks("Dari menu Pencairan atau dari Beranda, klik Ubah pada baris yang bersangkutan."));
isi.push(PENTING([
  "Hanya baris yang memiliki Data TBO yang dapat diubah. Baris tanpa Data TBO akan ditolak server " +
  "walaupun tombolnya sempat terlihat.",
]));
isi.push(spasi());
isi.push(teks("Selain kolom TBO, di sini Anda juga dapat memperbaiki arus dana bila hasil pembacaan otomatis kurang tepat. Perubahan itu ditandai sebagai keputusan manusia, bukan tebakan aplikasi."));

isi.push(H2("7.3 Mengubah tindak lanjut rekonsiliasi"));
isi.push(teks(
  "Di menu Rekonsiliasi, Editor dapat mengubah kolom Tindak lanjut dan menambahkan catatan " +
  "penanganan. Tombol “Jalankan ulang rekonsiliasi” juga tersedia bagi Editor, dan berguna " +
  "sesudah ada unggahan baru yang perlu dibandingkan ulang."));

isi.push(new Paragraph({ children: [new PageBreak()] }));

// ---------------------------------------------------------- 8 masalah
isi.push(H1("8. Kalau Ada Masalah"));
isi.push(PERAN_KEDUA());

isi.push(tabel(
  ["Yang terjadi", "Kemungkinan sebabnya", "Yang perlu dilakukan"],
  [
    ["Layar kosong, tidak ada satu baris pun",
     "Jatah cabang belum diberikan, atau penyaring tanggal terlalu sempit",
     "Klik Reset. Kalau tetap kosong, hubungi admin untuk memeriksa jatah Anda"],
    ["Tiba-tiba kembali ke halaman masuk",
     "Layar dibiarkan menganggur melewati batas waktu",
     "Masuk kembali. Keterangannya tertulis di halaman masuk"],
    ["Semua nama nasabah tampil ***",
     "Memang begitu seharusnya, berlaku untuk semua peran",
     "Gunakan nomor rekening atau nomor deposito untuk membedakan baris"],
    ["Mencari nama nasabah tidak menemukan apa pun",
     "Pencarian memakai nomor, bukan nama",
     "Cari dengan nomor rekening (menu TBO) atau nomor deposito (menu Pencairan)"],
    ["Tombol unggah tidak ada",
     "Peran Viewer, atau hak menu Unggah belum diberikan",
     "Hubungi admin bila menurut Anda seharusnya ada"],
    ["Berkas ditolak, disebut ada cabang di luar jatah",
     "Berkas memuat cabang yang bukan jatah Anda",
     "Unggah berkas yang hanya berisi cabang Anda, atau minta admin mengunggahnya"],
    ["Banyak baris ditolak dengan alasan cabang tak dikenal",
     "Kode cabang pada berkas belum terdaftar di master cabang",
     "Hubungi admin untuk memperbarui master cabang lebih dulu"],
    ["Angka di dashboard terlihat dobel",
     "Dua batch periode berbeda sama-sama aktif",
     "Buka menu Unggah, batalkan batch lama yang tergantikan (lihat bagian 6.5)"],
    ["Data sudah diunggah tetapi belum tampil",
     "Batch masih berstatus draft",
     "Buka menu Unggah dan tekan Komit pada batch tersebut"],
    ["Kolom Terlambat berisi tanda —",
     "Baris itu belum punya Target Pemenuhan TBO",
     "Isi targetnya lewat tombol Ubah (Editor), atau minta Editor mengisinya"],
  ],
  [2500, 3300, 3560]));

isi.push(new Paragraph({ children: [new PageBreak()] }));

// ---------------------------------------------------------- 9 istilah
isi.push(H1("9. Daftar Istilah"));
isi.push(tabel(
  ["Istilah", "Penjelasan"],
  [
    ["Batch", "Satu kali unggahan berkas Excel, beserta seluruh baris di dalamnya"],
    ["Break deposito", "Pencairan deposito sebelum tanggal jatuh tempo"],
    ["Committed", "Status batch yang sudah aktif dan tampil di dashboard"],
    ["Draft", "Status batch yang sudah terunggah tetapi belum tampil di dashboard"],
    ["Dikecualikan", "Baris yang memang tidak memerlukan dokumen TBO"],
    ["Jatah", "Cabang mana saja yang boleh dilihat oleh seorang pengguna"],
    ["Lingkup", "Cakupan sebuah batch: satu cabang tertentu, atau se-bank"],
    ["Outstanding", "Dokumen TBO belum lengkap dan masih dihitung keterlambatannya"],
    ["Penyamaran", "Penggantian nama nasabah menjadi *** sebelum data meninggalkan server"],
    ["Rekonsiliasi", "Pembandingan data IT dengan laporan cabang"],
    ["Rollover", "Deposito yang diperpanjang, bukan ditarik keluar"],
    ["TBO", "Rekening sudah dibuka, dokumen persyaratannya belum lengkap"],
    ["Tindak lanjut", "Tahap penanganan sebuah temuan rekonsiliasi"],
  ],
  [2200, 7160]));

isi.push(spasi(240));
isi.push(new Paragraph({
  spacing: { before: 240 },
  border: { top: { style: BorderStyle.SINGLE, size: 4, color: "D1D5DB" } },
  children: [new TextRun({
    text: "Panduan ini menjelaskan aplikasi per Agustus 2026. Bila tampilan di layar berbeda dengan " +
      "panduan, yang berlaku adalah layar — mintalah panduan versi terbaru kepada admin.",
    size: 18, color: ABU, italics: true,
  })],
}));

// ================================================================ DOKUMEN
const doc = new Document({
  creator: "USECASE-STUDIO.xyz",
  title: "Panduan Pengguna — Branch Operations and Transactions Monitoring",
  description: "Panduan untuk pengguna berperan Editor dan Viewer",
  numbering: {
    config: [
      {
        reference: "butir",
        levels: [
          { level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 460, hanging: 240 } } } },
          { level: 1, format: LevelFormat.BULLET, text: "◦", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 900, hanging: 240 } } } },
        ],
      },
      {
        reference: "langkah",
        levels: [
          { level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
            style: { paragraph: { indent: { left: 460, hanging: 300 } } } },
        ],
      },
    ],
  },
  styles: {
    default: {
      document: { run: { font: "Calibri", size: 21 } },
    },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 30, bold: true, color: BIRU, font: "Calibri" },
        paragraph: { spacing: { before: 360, after: 160 } } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 25, bold: true, color: "1F2937", font: "Calibri" },
        paragraph: { spacing: { before: 280, after: 120 } } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, color: "374151", font: "Calibri" },
        paragraph: { spacing: { before: 220, after: 100 } } },
    ],
  },
  sections: [
    {
      properties: {
        page: {
          margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 },
        },
      },
      footers: {
        default: new Footer({
          children: [
            new Paragraph({
              alignment: AlignmentType.CENTER,
              children: [
                new TextRun({ text: "Panduan Pengguna Branch Ops  ·  ", size: 16, color: ABU }),
                new TextRun({ children: [PageNumber.CURRENT], size: 16, color: ABU }),
              ],
            }),
          ],
        }),
      },
      children: isi,
    },
  ],
});

Packer.toBuffer(doc).then((buf) => {
  fs.writeFileSync(process.argv[2], buf);
  console.log("tersimpan:", process.argv[2], buf.length, "byte");
});
