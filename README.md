# Asisten Plastik — Anugerah Sejahtera Sentosa

Bot Telegram buat bantu admin ngerapihin order plastik jadi:
- Data tersimpan rapi di Google Sheets (order, produk, customer, supplier)
- Invoice otomatis (harga x qty + info rekening)
- Surat Jalan otomatis (tanpa harga, buat kurir)
- Purchase Order (PO) ke supplier + catatan utang otomatis
- Pembukuan sederhana: kas masuk/keluar, piutang customer, utang supplier,
  laporan laba rugi bulanan

Order masuk **kapan aja langsung diproses** (gak ada siklus mingguan).
Bot ini buat admin sendiri, alurnya: paste/forward chat order customer atau
kirim fotonya ke bot ini, bot yang baca & rapihin.

---

## 1. Isi Project

```
asisten-plastik/
├── README.md
├── requirements.txt
├── .env.example        <- template buat testing lokal
├── config.py            <- identitas usaha, katalog awal, kategori
├── sheets_client.py       <- baca/tulis Google Sheets (auto bikin tab kalau belum ada)
├── ai_parser.py            <- parsing chat/foto order & PO pakai Claude
├── documents.py              <- generate Invoice / Surat Jalan / PO sebagai gambar
├── fonts/                     <- font buat render dokumen (DejaVu, open source)
├── logo.jpg                    <- logo Anugerah Sejahtera Sentosa
└── bot.py                       <- file utama, jalanin ini
```

## 2. Setup Google Sheets — OTOMATIS

Beda dari versi lama (bot roti Miss Piggy), bot ini **self-provisioning**:
begitu pertama kali jalan, kalau tab `PriceList`, `Customers`, `Orders`,
`Suppliers`, `PurchaseOrders`, `UtangSupplier`, `Kas` belum ada di
spreadsheet, bot otomatis bikinin sendiri (header kolom + isi awal
PriceList & Customers dari `config.py`). Yang perlu disiapin manual cuma:

1. Bikin 1 Google Sheet kosong
2. Share spreadsheet itu ke email service account (`client_email` di file
   JSON), kasih akses **Editor**
3. Isi `GOOGLE_SHEET_ID` (ID-nya ada di URL sheet, antara `/d/` dan `/edit`)

Setelah itu tinggal jalanin bot sekali, tab-tabnya otomatis muncul.

## 3. Isi Data yang Masih Perlu Dilengkapi

Beberapa hal di `config.py` masih placeholder, tolong diisi:
- `BUSINESS_ADDRESS` — alamat usaha (buat kop invoice/surat jalan)
- `PICKUP_ADDRESS` — alamat pickup/gudang kalau beda dari di atas
- Daftar supplier awal — boleh dikosongin, nanti keisi otomatis pas bikin
  PO pertama kali (lewat `/po`), atau isi manual di tab `Suppliers`

## 4. Install & Jalanin (Lokal, buat testing)

```bash
cd asisten-plastik
pip install -r requirements.txt
cp .env.example .env
# isi .env dengan token-token
python bot.py
```

Kalau berhasil, chat bot di Telegram, ketik `/start`.

## 5. Deploy 24/7

1. Push folder ini ke GitHub repo
2. Connect repo ke Railway (atau Render/VPS kecil)
3. Set semua environment variable dari `.env.example` di dashboard
4. Deploy — otomatis `pip install` dan jalanin `python bot.py`

## 6. Gak Wajib Pakai Command

Buat command yang cuma "nanya" (piutang, utang, laporan bulanan, daftar
harga) atau aksi simpel (tandai lunas, catat bayar utang, cetak ulang
invoice/surat jalan), admin **gak perlu ketik command** -- tinggal chat
santai kayak "utang ke siapa aja", "si Grandia udah bayar belum",
"kas bulan ini gimana". Bot nebak maksudnya pakai AI (`classify_intent` di
`ai_parser.py`) dan rute ke fungsi yang sama kayak commandnya. Kalau bot
ragu / gagal nebak, default-nya tetep dianggap ORDER customer (paling
aman, biar order gak kelewat).

## 7. Command Bot (opsional, buat yang mau lebih pasti/cepat)

| Command | Fungsi |
|---|---|
| `/start` | Salam pembuka + daftar command |
| `/pricelist` | Tampilin daftar harga dari Sheets |
| (paste/forward chat customer, atau kirim foto) | Bot parse jadi order, minta konfirmasi, lalu simpan + generate Invoice & Surat Jalan |
| `/invoice <no invoice / nama customer>` | Cetak ulang invoice |
| `/suratjalan <no invoice / nama customer>` | Cetak ulang surat jalan |
| `/lunas <no invoice / nama customer>` | Tandai order lunas, otomatis catat Kas Masuk |
| `/piutang` | Rekap tagihan customer yang belum lunas |
| `/po` | Mulai bikin Purchase Order ke supplier (otomatis nambah utang) |
| `/bayarutang <nama supplier> <jumlah>` | Catat pembayaran/cicilan ke supplier |
| `/utang` | Rekap utang ke semua supplier |
| `/kas masuk <jumlah> <keterangan>` | Catat uang masuk di luar penjualan |
| `/kas keluar <jumlah> <keterangan>` | Catat uang keluar (operasional, gaji, dll) |
| `/laporanbulanan [YYYY-MM]` | Laporan kas & laba rugi bulanan |
| `/batal` | Batalin order/PO yang lagi nunggu konfirmasi |

## 8. Batasan Versi Ini

- Invoice, Surat Jalan, dan PO dikirim sebagai **gambar PNG** rapi, siap
  di-forward ke customer/kurir/supplier.
- Parsing chat/foto order pakai AI itu cukup pinter buat kalimat natural,
  tapi tetep nunjukin hasil parse-nya dulu buat dikonfirmasi sebelum
  disimpen -- supaya gak ada salah baca.
- Laporan laba rugi dihitung dari tab `Kas` (kas masuk dikategoriin
  "Penjualan" begitu order ditandai lunas, kas keluar dikategoriin waktu
  bayar utang supplier / catat manual lewat `/kas`).
