"""
Semua fungsi baca/tulis ke Google Sheets ada di sini.
Sheet ini "database" utama sistem -- 7 tab:
  PriceList, Customers, Orders, Suppliers, PurchaseOrders, UtangSupplier, Kas

Bot ini SELF-PROVISIONING: begitu pertama kali jalan, kalau tab-tab di atas
belum ada di spreadsheet, bot otomatis bikinin (termasuk header kolom &
ngisi PriceList/Customers dari SEED_PRODUCTS/SEED_CUSTOMERS di config.py).
Jadi Riky cuma perlu bikin 1 spreadsheet KOSONG & share ke service account
-- sisanya otomatis.
"""

import copy
import datetime
import json
import logging
import threading
import time
import uuid

import gspread
from google.oauth2.service_account import Credentials

import config

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# ---- definisi skema: nama tab -> header kolom ----
SCHEMA = {
    config.SHEET_PRICELIST: [
        "Item_Code", "Nama", "Deskripsi", "Kategori", "Satuan",
        "Harga_Jual", "Harga_Beli", "Khusus_Customer", "Supplier", "Isi_Bal", "Stok_Min", "Qty_Order",
    ],
    config.SHEET_MUTASI: ["Waktu", "Item_Code", "Nama", "Jenis", "Qty", "Satuan", "Ref", "Catatan", "Oleh"],
    config.SHEET_HARGA_CUSTOMER: ["Customer", "Item_Code", "Harga_Jual"],
    config.SHEET_CUSTOMERS: ["Nama", "No_HP", "Alamat"],
    config.SHEET_ORDERS: [
        "Timestamp", "No_Invoice", "Nama_Customer", "No_HP", "Alamat",
        "Metode", "Item_Code", "Nama_Item", "Kategori", "Qty", "Satuan",
        "Harga_Satuan", "Subtotal", "Ongkir", "Status", "Tanggal_Bayar",
        "No_PO_Customer", "Tanggal_Kirim",
    ],
    config.SHEET_SUPPLIERS: ["Nama_Supplier", "No_HP", "Barang", "Alamat"],
    config.SHEET_PURCHASE_ORDERS: [
        "Timestamp", "No_PO", "Nama_Supplier", "Item", "Qty", "Satuan",
        "Harga_Satuan", "Subtotal", "Status", "Tanggal_Lunas",
    ],
    config.SHEET_UTANG_SUPPLIER: [
        "Tanggal", "Nama_Supplier", "No_PO", "Jenis", "Jumlah",
        "Saldo_Berjalan", "Catatan",
    ],
    config.SHEET_KAS: [
        "Tanggal", "Jenis", "Kategori", "Jumlah", "Keterangan", "Ref",
    ],
    config.SHEET_PENGINGAT: [
        "ID", "Jenis", "Ref", "Nama", "Jumlah", "Tanggal", "Status",
        "Terkirim_Tgl", "Dibuat", "Catatan",
    ],
    config.SHEET_TOPIK: ["Kunci", "Chat_ID", "Thread_ID"],
    config.SHEET_STAFF: ["ID", "Nama", "Hash", "Salt", "Aktif", "Dibuat"],
    config.SHEET_PENGAJUAN: ["ID", "Batch", "Waktu", "Staff", "Jenis", "Item_Code", "Nama", "Qty", "Satuan",
                             "Ref", "Status", "Diputuskan_Oleh", "Diputuskan_Waktu", "Pesan_TG"],
    config.SHEET_KOMISI: ["Customer", "Rp_per_Satuan", "Penerima", "Catatan"],
    config.SHEET_KOMISI_CATAT: ["No_Invoice", "Customer", "Penerima", "Qty", "Rp_per_Satuan", "Jumlah",
                                "Status", "Dibuat", "Dibayar"],
    config.SHEET_PENERIMAAN: ["No_PO", "Status", "Batch", "Staff", "Waktu", "Catatan", "Peta"],
    config.SHEET_PERMINTAAN: ["ID", "Waktu", "Staff", "Item_Code", "Nama", "Qty", "Satuan", "Catatan", "Status"],
    config.SHEET_PENGIRIMAN: ["No_Invoice", "Status", "Staff", "Waktu"],
    config.SHEET_LINKORDER: ["Token", "Nama_Customer", "Aktif", "Dibuat", "Catatan"],
    config.SHEET_PESANANWEB: ["ID", "Waktu", "Nama", "Payload", "Status"],
    config.SHEET_TAGIHAN: [
        "Nama", "Tipe", "Hari_Kontra_Bon", "Tempo_Hari", "Alias",
    ],
}


def _today_str():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=7)  # WIB
    return now.strftime("%Y-%m-%d")


HARI_ID = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]


def _today_date():
    return datetime.datetime.strptime(_today_str(), "%Y-%m-%d").date()


def _norm(s):
    return "".join(ch for ch in str(s or "").lower() if ch.isalnum())


def hari_index(nama_hari):
    """'Selasa' -> 1 (Senin=0); None kalau bukan nama hari."""
    n = str(nama_hari or "").strip().lower().replace("'", "").replace("’", "")
    alias = {"senin": 0, "selasa": 1, "rabu": 2, "kamis": 3, "jumat": 4,
             "sabtu": 5, "minggu": 6, "ahad": 6}
    return alias.get(n)


def next_weekday(after_date, weekday_idx):
    """Tanggal hari `weekday_idx` berikutnya, PALING CEPAT besok (bukan hari ini)."""
    d = after_date + datetime.timedelta(days=1)
    while d.weekday() != weekday_idx:
        d += datetime.timedelta(days=1)
    return d


def tgl_dmy(date_or_str):
    """date / '2026-10-27' -> '27-10-2026'."""
    if isinstance(date_or_str, str):
        try:
            date_or_str = datetime.datetime.strptime(date_or_str[:10], "%Y-%m-%d").date()
        except ValueError:
            return str(date_or_str)
    return date_or_str.strftime("%d-%m-%Y")


def hari_dari_tanggal(date_or_str):
    if isinstance(date_or_str, str):
        date_or_str = datetime.datetime.strptime(date_or_str[:10], "%Y-%m-%d").date()
    return HARI_ID[date_or_str.weekday()]


def _now_str():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    return now.strftime("%Y-%m-%d %H:%M:%S")


_WRITE_METHODS = {
    "append_row", "append_rows", "update", "update_cell", "update_cells", "update_acell",
    "batch_update", "delete_rows", "delete_row", "insert_row", "insert_rows", "clear",
    "batch_clear", "format", "batch_format", "resize", "add_rows", "add_cols", "sort",
    "merge_cells", "unmerge_cells", "freeze", "set_basic_filter", "clear_basic_filter",
}
_CACHE_TTL = 45  # detik; hemat kuota baca Google Sheets (maks 60 baca/menit). Nulis = cache tab itu langsung dibuang.


class _CachedWS:
    """Pembungkus Worksheet: hasil baca disimpen sebentar (TTL) dan dibuang
    otomatis tiap ada penulisan ke tab yang sama."""

    def __init__(self, ws, cache, lock):
        self._ws, self._cache, self._lock = ws, cache, lock

    def _read(self, name, *a, **kw):
        key = (self._ws.title, name, repr(a), repr(sorted(kw.items())))
        now = time.time()
        with self._lock:
            hit = self._cache.get(key)
            if hit and now - hit[0] < _CACHE_TTL:
                return copy.deepcopy(hit[1])
        for coba in range(3):
            try:
                val = getattr(self._ws, name)(*a, **kw)
                break
            except gspread.exceptions.APIError as e:
                # 429 = kuota baca per menit abis -> tunggu bentar, coba lagi
                if "429" not in str(e) or coba == 2:
                    raise
                time.sleep(4 * (coba + 1))
        with self._lock:
            self._cache[key] = (time.time(), copy.deepcopy(val))
        return val

    def _invalidate(self):
        with self._lock:
            for k in [k for k in self._cache if k[0] == self._ws.title]:
                del self._cache[k]

    def get_all_values(self, *a, **kw):
        return self._read("get_all_values", *a, **kw)

    def get_all_records(self, *a, **kw):
        return self._read("get_all_records", *a, **kw)

    def row_values(self, *a, **kw):
        return self._read("row_values", *a, **kw)

    def __getattr__(self, name):
        attr = getattr(self._ws, name)
        if name in _WRITE_METHODS and callable(attr):
            def wrapped(*a, **kw):
                try:
                    return attr(*a, **kw)
                finally:
                    self._invalidate()
            return wrapped
        return attr


class SheetsClient:
    def __init__(self):
        if config.GOOGLE_SERVICE_ACCOUNT_JSON:
            info = json.loads(config.GOOGLE_SERVICE_ACCOUNT_JSON)
            creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        else:
            creds = Credentials.from_service_account_file(
                config.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
            )
        self.gc = gspread.authorize(creds)
        self.sh = self.gc.open_by_key(config.GOOGLE_SHEET_ID)
        self._lock = threading.Lock()
        self._ws_objs = {}
        self._data_cache = {}
        self._cache_lock = threading.Lock()
        self._ensure_schema()

    # ---------------- SETUP OTOMATIS ----------------

    def _ensure_schema(self):
        existing = {ws.title: ws for ws in self.sh.worksheets()}
        for name, headers in SCHEMA.items():
            if name not in existing:
                ws = self.sh.add_worksheet(title=name, rows=200, cols=max(len(headers), 8))
                ws.append_row(headers, value_input_option="RAW")
            else:
                ws = existing[name]
                first_row = ws.row_values(1)
                if not first_row:
                    ws.append_row(headers, value_input_option="RAW")
                else:
                    # Migrasi kolom baru: kalau ada nama kolom di SCHEMA yang
                    # belum ada di header Sheets yang UDAH jalan (bukan tab
                    # baru), tambahin di ujung kanan -- data lama gak
                    # kesentuh, cuma kolom baru nambah kosong buat baris lama.
                    missing = [h for h in headers if h not in first_row]
                    if missing:
                        ws.update("A1", [first_row + missing])

        # kalau spreadsheet baru dibuat gspread nyisain tab default "Sheet1"
        # kosong -- hapus biar rapi (aman diabaikan kalau gagal/gak ada).
        try:
            default_ws = self.sh.worksheet("Sheet1")
            if not default_ws.get_all_values():
                self.sh.del_worksheet(default_ws)
        except gspread.exceptions.WorksheetNotFound:
            pass

        self._seed_pricelist_if_empty()
        self._seed_customers_if_empty()
        self._seed_tagihan_if_empty()
        self._ensure_batal_red_formatting(config.SHEET_ORDERS)
        self._ensure_batal_red_formatting(config.SHEET_PURCHASE_ORDERS)

    @staticmethod
    def _col_letter(idx0):
        """idx0: index kolom 0-based -> huruf kolom ala Sheets (A, B, ..., Z, AA, ...)."""
        n = idx0 + 1
        letters = ""
        while n > 0:
            n, rem = divmod(n - 1, 26)
            letters = chr(65 + rem) + letters
        return letters

    def _has_batal_conditional_format(self, sheet_id):
        """Cek apakah tab ini UDAH punya conditional format rule Status=Batal
        -- biar gak nambahin rule yang sama berkali-kali tiap bot restart."""
        try:
            meta = self.sh.fetch_sheet_metadata()
        except Exception:
            return True  # gagal cek -> anggap udah ada, gak usah maksa nambahin
        for sheet in meta.get("sheets", []):
            if sheet.get("properties", {}).get("sheetId") != sheet_id:
                continue
            for rule in sheet.get("conditionalFormats", []):
                formula = (
                    rule.get("booleanRule", {})
                    .get("condition", {})
                    .get("values", [{}])[0]
                    .get("userEnteredValue", "")
                )
                if "Batal" in formula:
                    return True
        return False

    def _ensure_batal_red_formatting(self, tab_name):
        """Pasang conditional formatting: baris otomatis kewarna MERAH kalau
        kolom Status-nya 'Batal' -- biar keliatan jelas langsung di Google
        Sheets tanpa perlu ngapus barisnya (data batal tetep kesimpen buat
        histori). Formatting doang, gak fatal kalau gagal (mis. akun service
        gak punya izin format) -- bot tetep jalan normal."""
        headers = SCHEMA.get(tab_name)
        if not headers or "Status" not in headers:
            return
        try:
            ws = self._ws(tab_name)
            if self._has_batal_conditional_format(ws.id):
                return
            status_col_letter = self._col_letter(headers.index("Status"))
            self.sh.batch_update({
                "requests": [{
                    "addConditionalFormatRule": {
                        "rule": {
                            "ranges": [{
                                "sheetId": ws.id,
                                "startRowIndex": 1,
                                "startColumnIndex": 0,
                                "endColumnIndex": len(headers),
                            }],
                            "booleanRule": {
                                "condition": {
                                    "type": "CUSTOM_FORMULA",
                                    "values": [{"userEnteredValue": f'=${status_col_letter}2="Batal"'}],
                                },
                                "format": {
                                    "backgroundColor": {"red": 0.96, "green": 0.80, "blue": 0.80},
                                },
                            },
                        },
                        "index": 0,
                    },
                }],
            })
        except Exception:
            pass

    def _seed_pricelist_if_empty(self):
        ws = self.sh.worksheet(config.SHEET_PRICELIST)
        rows = ws.get_all_values()
        if len(rows) <= 1:  # cuma header / kosong total
            data = [
                [
                    p["item_code"], p["nama"], p["deskripsi"], p["kategori"],
                    p["satuan"], p["harga_jual"], p["harga_beli"],
                ]
                for p in config.SEED_PRODUCTS
            ]
            if data:
                ws.append_rows(data, value_input_option="RAW")

    def _seed_customers_if_empty(self):
        ws = self.sh.worksheet(config.SHEET_CUSTOMERS)
        rows = ws.get_all_values()
        if len(rows) <= 1:
            data = [[nama, "", ""] for nama in config.SEED_CUSTOMERS]
            if data:
                ws.append_rows(data, value_input_option="RAW")

    def _seed_tagihan_if_empty(self):
        ws = self.sh.worksheet(config.SHEET_TAGIHAN)
        rows = ws.get_all_values()
        if len(rows) <= 1:
            data = [list(r) for r in config.SEED_TAGIHAN]
            if data:
                ws.append_rows(data, value_input_option="RAW")

    def _ws(self, name):
        ws = self._ws_objs.get(name)
        if ws is None:
            ws = self.sh.worksheet(name)
            self._ws_objs[name] = ws
        return _CachedWS(ws, self._data_cache, self._cache_lock)

    # kolom yang isinya BISA kelihatan angka murni (no HP, kode item) tapi
    # harus tetap dibaca sebagai teks -- kalau enggak, gspread otomatis
    # nyoba convert ke number dan ngilangin angka 0 di depan (mis. No_HP
    # "0812xxx" jadi 812).
    _TEXT_ONLY_COLUMNS = {"No_HP", "Item_Code"}

    @classmethod
    def _numericise_ignore_for(cls, headers):
        ignore = []
        for i, h in enumerate(headers, start=1):
            if h in cls._TEXT_ONLY_COLUMNS:
                ignore.append(i)
        return ignore

    def _records(self, ws):
        """Kayak get_all_records, tapi dibangun dari get_all_values (yang bisa
        di-prefetch sekaligus semua tab = hemat kuota). Kolom No_HP/Item_Code
        tetap teks biar angka 0 di depan gak ilang."""
        from gspread.utils import numericise_all
        values = ws.get_all_values()
        if not values or not values[0]:
            return []
        keys = values[0]
        ignore = self._numericise_ignore_for(keys)
        out = []
        for row in values[1:]:
            row = list(row) + [""] * (len(keys) - len(row))
            out.append(dict(zip(keys, numericise_all(row[:len(keys)], default_blank="", ignore=ignore))))
        return out

    def prefetch(self):
        """Baca SEMUA tab dalam 1 panggilan API (values_batch_get) terus taruh di
        cache. Dipanggil sebelum dashboard / laporan yang baca banyak tab."""
        now = time.time()
        with self._cache_lock:
            fresh = {k[0] for k, v in self._data_cache.items()
                     if k[1] == "get_all_values" and now - v[0] < _CACHE_TTL - 5}
        if not getattr(self, "_titles", None):
            try:
                self._titles = [w.title for w in self.sh.worksheets()]
            except Exception:
                return
        want = [t for t in self._titles if t in SCHEMA and t not in fresh]
        if not want:
            return
        try:
            res = self.sh.values_batch_get([f"'{t}'" for t in want])
        except Exception:
            logger.exception("prefetch gagal (lanjut baca biasa)")
            return
        for t, vr in zip(want, res.get("valueRanges", [])):
            vals = vr.get("values", [])
            w = max((len(r) for r in vals), default=0)
            vals = [list(r) + [""] * (w - len(r)) for r in vals]
            with self._cache_lock:
                self._data_cache[(t, "get_all_values", "()", "[]")] = (time.time(), copy.deepcopy(vals))

    # ---------------- PRICELIST ----------------

    def get_price_list(self):
        return self._records(self._ws(config.SHEET_PRICELIST))

    def get_price_map(self):
        """dict item_code (upper) -> row produk"""
        out = {}
        for row in self.get_price_list():
            code = str(row.get("Item_Code", "")).strip().upper()
            if code:
                out[code] = row
        return out

    def find_product(self, query):
        """Cari produk berdasarkan Item_Code (persis) atau nama/kategori
        (loose contains, case-insensitive). Balikin row pertama yang cocok,
        atau None."""
        query = (query or "").strip().lower()
        if not query:
            return None
        price_list = self.get_price_list()
        for row in price_list:
            if str(row.get("Item_Code", "")).strip().lower() == query:
                return row
        candidates = []
        for row in price_list:
            haystack = " ".join([
                str(row.get("Nama", "")), str(row.get("Kategori", "")),
                str(row.get("Deskripsi", "")),
            ]).lower()
            if query in haystack:
                candidates.append(row)
        if len(candidates) == 1:
            return candidates[0]
        if len(candidates) > 1:
            # ambil yang nama-nya paling mirip (paling pendek = paling spesifik)
            candidates.sort(key=lambda r: len(str(r.get("Nama", ""))))
            return candidates[0]
        return None

    def update_price(self, item_code, harga_jual=None, harga_beli=None):
        """Update Harga_Jual dan/atau Harga_Beli buat 1 produk di PriceList
        (dicari by Item_Code, persis). Cuma field yang dikasih (bukan None)
        yang diupdate. Balikin True kalau item_code ketemu & keupdate,
        False kalau item_code gak ada di katalog."""
        ws = self._ws(config.SHEET_PRICELIST)
        headers = ws.row_values(1)
        col_code = headers.index("Item_Code") + 1
        col_jual = headers.index("Harga_Jual") + 1
        col_beli = headers.index("Harga_Beli") + 1
        target = (item_code or "").strip().upper()
        if not target:
            return False
        all_values = ws.get_all_values()
        for idx, row in enumerate(all_values[1:], start=2):
            if len(row) < col_code:
                continue
            if row[col_code - 1].strip().upper() != target:
                continue
            if harga_jual is not None:
                ws.update_cell(idx, col_jual, harga_jual)
            if harga_beli is not None:
                ws.update_cell(idx, col_beli, harga_beli)
            return True
        return False

    def cari_produk_massal(self, query):
        """Cari banyak produk sekaligus: Kategori (persis) > Nama/Deskripsi
        (semua kata cocok) > Khusus_Customer. Balikin (cara, [rows])."""
        q = (query or "").strip().lower()
        rows = [r for r in self.get_price_list() if str(r.get("Item_Code", "")).strip()]
        if not q:
            return "", []
        hit = [r for r in rows if str(r.get("Kategori", "")).strip().lower() == q]
        if hit:
            return "kategori", hit
        words = q.split()
        hit = [r for r in rows if all(w in (str(r.get("Nama", "")) + " " + str(r.get("Deskripsi", ""))
                                              + " " + str(r.get("Item_Code", ""))).lower() for w in words)]
        if hit:
            return "nama", hit
        hit = [r for r in rows if q in str(r.get("Khusus_Customer", "")).lower()]
        if hit:
            return "khusus customer", hit
        return "", []

    def bulk_update_price(self, codes, field, harga):
        """Ubah Harga_Jual / Harga_Beli buat banyak item sekaligus (1x tulis)."""
        from gspread.utils import rowcol_to_a1
        ws = self._ws(config.SHEET_PRICELIST)
        values = ws.get_all_values()
        headers = values[0]
        c_code = headers.index("Item_Code")
        c_f = headers.index("Harga_Jual" if field == "jual" else "Harga_Beli")
        want = {c.strip().upper() for c in codes}
        data = []
        for i, row in enumerate(values[1:], start=2):
            if len(row) > c_code and row[c_code].strip().upper() in want:
                data.append({"range": rowcol_to_a1(i, c_f + 1), "values": [[harga]]})
        if data:
            ws.batch_update(data)
        return len(data)

    def rename_product(self, item_code, new_nama=None, new_kategori=None, new_satuan=None):
        """Ganti Nama/Kategori/Satuan produk yang SUDAH ADA di PriceList
        (dicari by Item_Code, persis) -- dipakai pas admin REVISI nama/ukuran
        produk secara PERMANEN di katalog (misal 'PP bening 40x60' direvisi
        jadi 'PP bening 45x65'), beda sama update_price yang cuma ngurusin
        harga. Field yang dikasih None/kosong dibiarin sama kayak sebelumnya.
        Balikin True kalau item_code ketemu & keupdate, False kalau enggak."""
        ws = self._ws(config.SHEET_PRICELIST)
        headers = ws.row_values(1)
        col_code = headers.index("Item_Code") + 1
        col_nama = headers.index("Nama") + 1
        col_kategori = headers.index("Kategori") + 1
        col_satuan = headers.index("Satuan") + 1
        target = (item_code or "").strip().upper()
        if not target:
            return False
        all_values = ws.get_all_values()
        for idx, row in enumerate(all_values[1:], start=2):
            if len(row) < col_code:
                continue
            if row[col_code - 1].strip().upper() != target:
                continue
            if new_nama and new_nama.strip():
                ws.update_cell(idx, col_nama, new_nama.strip())
            if new_kategori and new_kategori.strip():
                ws.update_cell(idx, col_kategori, new_kategori.strip())
            if new_satuan and new_satuan.strip():
                ws.update_cell(idx, col_satuan, new_satuan.strip())
            return True
        return False

    def add_products_bulk(self, products):
        """products: list dict {item_code,nama,deskripsi,kategori,satuan,harga_jual,
        harga_beli,khusus}. Kode yang udah ada dilewat. Balikin (ditambah, dilewat)."""
        ws = self._ws(config.SHEET_PRICELIST)
        headers = ws.row_values(1)
        have = {str(r.get("Item_Code", "")).strip().upper() for r in self.get_price_list()}
        rows, skipped = [], 0
        keymap = {"Item_Code": "item_code", "Nama": "nama", "Deskripsi": "deskripsi", "Kategori": "kategori",
                  "Satuan": "satuan", "Harga_Jual": "harga_jual", "Harga_Beli": "harga_beli",
                  "Khusus_Customer": "khusus", "Supplier": "supplier", "Isi_Bal": "isi_bal"}
        from gspread.utils import rowcol_to_a1
        values = ws.get_all_values()
        c_code = headers.index("Item_Code")
        fix = []
        isi_kolom = [(headers.index(h), k) for h, k in (("Supplier", "supplier"), ("Isi_Bal", "isi_bal")) if h in headers]
        for p in products:
            if p["item_code"].upper() in have:
                skipped += 1
                for c_x, key in isi_kolom:
                    if not p.get(key):
                        continue
                    for i, row in enumerate(values[1:], start=2):
                        if len(row) > c_code and row[c_code].strip().upper() == p["item_code"].upper() \
                                and (len(row) <= c_x or not str(row[c_x]).strip()):
                            fix.append({"range": rowcol_to_a1(i, c_x + 1), "values": [[p[key]]]})
                continue
            rows.append([p.get(keymap.get(h, ""), "") for h in headers])
        if fix:
            ws.batch_update(fix)
        if rows:
            ws.append_rows(rows, value_input_option="RAW")
        return len(rows), skipped

    def add_product(self, item_code, nama, deskripsi="", kategori="", satuan="", harga_jual=0, harga_beli=0):
        """Tambah 1 baris produk BARU ke PriceList. item_code WAJIB unik --
        kalau kode itu udah kepake, gak nambah apa-apa (balikin False) biar
        gak duplikat. Balikin True kalau berhasil ditambahin."""
        code = (item_code or "").strip().upper()
        if not code:
            return False
        if code in self.get_price_map():
            return False
        ws = self._ws(config.SHEET_PRICELIST)
        ws.append_row([code, nama, deskripsi, kategori, satuan, harga_jual, harga_beli])
        return True

    def get_pricelist_text(self):
        rows = self.get_price_list()
        by_kategori = {}
        for r in rows:
            by_kategori.setdefault(r.get("Kategori", "Lainnya"), []).append(r)
        lines = []
        for kategori, items in by_kategori.items():
            lines.append(f"*{kategori}*")
            for it in items:
                harga = f"Rp{int(it['Harga_Jual']):,}".replace(",", ".")
                ket = f" ({it['Deskripsi']})" if it.get("Deskripsi") else ""
                lines.append(f"  {it['Item_Code']} - {it['Nama']}{ket}: {harga}/{it['Satuan']}")
            lines.append("")
        return "\n".join(lines).strip()

    # ---------------- CUSTOMERS ----------------

    def get_customers(self):
        return self._records(self._ws(config.SHEET_CUSTOMERS))

    def get_customer_names(self):
        return [str(r.get("Nama", "")).strip() for r in self.get_customers() if r.get("Nama")]

    def get_customer(self, nama):
        """Baris Customers yang namanya sama (case-insensitive), atau None."""
        nama_lower = (nama or "").strip().lower()
        if not nama_lower:
            return None
        for r in self.get_customers():
            if str(r.get("Nama", "")).strip().lower() == nama_lower:
                return r
        return None

    def update_customer(self, nama, no_hp=None, alamat=None):
        """Update data customer SECARA PERMANEN: baris di sheet Customers
        (dibuat kalau belum ada) + semua invoice customer ini yang masih
        Pending (belum lunas). Invoice yang udah Lunas/Batal dibiarin biar
        arsipnya gak berubah. Balikin jumlah invoice Pending yang keupdate."""
        from gspread.utils import rowcol_to_a1
        nama = (nama or "").strip()
        new_vals = {}
        if (no_hp or "").strip():
            new_vals["No_HP"] = no_hp.strip()
        if (alamat or "").strip():
            new_vals["Alamat"] = alamat.strip()
        if not nama or not new_vals:
            return 0

        # --- sheet Customers ---
        ws = self._ws(config.SHEET_CUSTOMERS)
        values = ws.get_all_values()
        headers = values[0] if values else []
        row_idx = None
        for i, row in enumerate(values[1:], start=2):
            if row and row[0].strip().lower() == nama.lower():
                row_idx = i
                break
        if row_idx is None:
            ws.append_row([nama, new_vals.get("No_HP", ""), new_vals.get("Alamat", "")],
                          value_input_option="RAW")
        else:
            ws.batch_update(
                [{"range": rowcol_to_a1(row_idx, headers.index(col_name) + 1), "values": [[v]]}
                 for col_name, v in new_vals.items()],
            )

        # --- invoice Pending ---
        wo = self._ws(config.SHEET_ORDERS)
        ov = wo.get_all_values()
        if not ov:
            return 0
        oh = ov[0]
        c_inv, c_name, c_status = (oh.index("No_Invoice"), oh.index("Nama_Customer"), oh.index("Status"))
        data, invoices = [], set()
        for i, row in enumerate(ov[1:], start=2):
            if len(row) <= max(c_inv, c_name, c_status):
                continue
            if row[c_name].strip().lower() != nama.lower() or row[c_status] != "Pending":
                continue
            invoices.add(row[c_inv])
            for col_name, v in new_vals.items():
                data.append({"range": rowcol_to_a1(i, oh.index(col_name) + 1), "values": [[v]]})
        if data:
            wo.batch_update(data)
        return len(invoices)

    def add_customer_if_new(self, nama, no_hp="", alamat=""):
        nama = (nama or "").strip()
        if not nama:
            return
        existing_lower = [n.lower() for n in self.get_customer_names()]
        if nama.lower() not in existing_lower:
            self._ws(config.SHEET_CUSTOMERS).append_row(
                [nama, no_hp, alamat], value_input_option="RAW"
            )

    # ---------------- NOMOR DOKUMEN ----------------

    def _next_number(self, prefix, existing_numbers, tanggal=None, seq_start=None):
        """Nomor dokumen PREFIX-YYYYMMDD-NNN. Default: urutan reset tiap hari
        (mulai 001). Kalau seq_start dikasih: urutan jalan TERUS lintas hari
        (nomor terbesar yang udah ada + 1) dan gak pernah di bawah seq_start."""
        today = (tanggal or _today_str()).replace("-", "")
        today_prefix = f"{prefix}-{today}-"
        if seq_start is not None:
            nums = [int(n.split("-")[-1]) for n in existing_numbers
                    if n.startswith(f"{prefix}-") and n.split("-")[-1].isdigit()]
            seq = max(max(nums) + 1 if nums else 0, int(seq_start))
            return f"{today_prefix}{seq:03d}"
        seq = 1
        used = [n for n in existing_numbers if n.startswith(today_prefix)]
        if used:
            nums = []
            for n in used:
                try:
                    nums.append(int(n.split("-")[-1]))
                except ValueError:
                    pass
            if nums:
                seq = max(nums) + 1
        return f"{today_prefix}{seq:03d}"

    def next_invoice_number(self, tanggal=None):
        existing = [str(r.get("No_Invoice", "")) for r in self.get_all_orders()]
        return self._next_number(config.INVOICE_PREFIX, existing, tanggal,
                                 seq_start=getattr(config, "INVOICE_SEQ_START", None))

    def next_po_number(self):
        existing = [str(r.get("No_PO", "")) for r in self.get_all_pos()]
        return self._next_number(config.PO_PREFIX, existing)

    # ---------------- ORDERS ----------------

    def get_all_orders(self):
        return self._records(self._ws(config.SHEET_ORDERS))

    def add_order(self, nama_customer, no_hp, alamat, metode, items, ongkir=0,
                  no_po_customer="", tanggal_kirim="", tanggal_order=""):
        """items: list of dict {item_code, nama_item, kategori, qty, satuan,
        harga_satuan}. Nulis 1 baris per item, semuanya share No_Invoice yang
        sama. no_po_customer/tanggal_kirim opsional (referensi No. PO dari
        customer & tanggal request kirim, kalau ada). Balikin no_invoice
        yang dipakai. tanggal_order (YYYY-MM-DD, opsional) = tanggal invoice
        kalau order ini pindahan dari nota/program lama; kosong = hari ini."""
        tgl = None
        try:
            if tanggal_order:
                tgl = datetime.datetime.strptime(str(tanggal_order).strip(), "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            tgl = None
        with self._lock:
            no_invoice = self.next_invoice_number(tgl)
            ts = _now_str()
            if tgl:
                ts = f"{tgl} {ts.split(' ', 1)[1]}"
            ws = self._ws(config.SHEET_ORDERS)
            rows = []
            for idx, it in enumerate(items):
                subtotal = float(it["qty"]) * float(it["harga_satuan"])
                rows.append([
                    ts, no_invoice, nama_customer, no_hp, alamat, metode,
                    it.get("item_code", ""), it["nama_item"], it.get("kategori", ""),
                    it["qty"], it.get("satuan", ""), it["harga_satuan"], subtotal,
                    ongkir if idx == 0 else 0,  # ongkir cuma dicatat 1x di baris pertama
                    "Pending", "",
                    no_po_customer, tanggal_kirim,
                ])
            ws.append_rows(rows, value_input_option="RAW")
            self.add_customer_if_new(nama_customer, no_hp, alamat)
        try:
            total = sum(float(it["qty"]) * float(it["harga_satuan"]) for it in items) + float(ongkir or 0)
            self.create_invoice_reminders(no_invoice, nama_customer, total, tgl)
        except Exception:
            logger.exception("gagal bikin pengingat invoice %s", no_invoice)
        return no_invoice

    def get_order_items(self, no_invoice):
        return [r for r in self.get_all_orders() if str(r.get("No_Invoice", "")) == no_invoice]

    def get_orders_by_customer(self, nama_customer, status=None):
        nama_lower = (nama_customer or "").strip().lower()
        out = []
        for r in self.get_all_orders():
            if str(r.get("Nama_Customer", "")).strip().lower() != nama_lower:
                continue
            if status and str(r.get("Status", "")) != status:
                continue
            out.append(r)
        return out

    def find_customer_invoices(self, key, limit=8):
        """Daftar invoice (tanpa yang Batal) buat 1 customer, terbaru dulu.
        Nama dicocokin persis dulu; kalau gak ada, cocokin sebagian (mis.
        'pillow' ketemu 'Pillow Cake'). Tiap item: {no_invoice, nama, tanggal,
        total, status}."""
        key_l = (key or "").strip().lower()
        if not key_l:
            return []
        rows = [r for r in self.get_all_orders() if str(r.get("Status", "")) != "Batal"]
        match = [r for r in rows if str(r.get("Nama_Customer", "")).strip().lower() == key_l]
        if not match:
            match = [r for r in rows if key_l in str(r.get("Nama_Customer", "")).strip().lower()]
        by_inv = {}
        for r in match:
            inv = str(r.get("No_Invoice", ""))
            d = by_inv.setdefault(inv, {"no_invoice": inv, "nama": r.get("Nama_Customer", ""),
                                        "tanggal": str(r.get("Timestamp", ""))[:10],
                                        "total": 0.0, "status": r.get("Status", ""), "_ts": str(r.get("Timestamp", ""))})
            try:
                d["total"] += float(r.get("Subtotal", 0) or 0)
            except (TypeError, ValueError):
                pass
        for inv, d in by_inv.items():
            first = next((r for r in match if str(r.get("No_Invoice", "")) == inv), None)
            try:
                d["total"] += float(first.get("Ongkir", 0) or 0)
            except (TypeError, ValueError, AttributeError):
                pass
        return sorted(by_inv.values(), key=lambda d: d["_ts"], reverse=True)[:limit]

    def get_latest_invoice_for_customer(self, nama_customer):
        orders = self.get_orders_by_customer(nama_customer)
        if not orders:
            return None
        return sorted(orders, key=lambda r: str(r.get("Timestamp", "")))[-1].get("No_Invoice")

    def mark_order_lunas(self, no_invoice):
        """Tandai semua baris dengan No_Invoice ini jadi Lunas. Balikin total
        (subtotal + ongkir) buat dicatat ke Kas."""
        ws = self._ws(config.SHEET_ORDERS)
        headers = ws.row_values(1)
        col_invoice = headers.index("No_Invoice") + 1
        col_status = headers.index("Status") + 1
        col_tgl = headers.index("Tanggal_Bayar") + 1
        col_subtotal = headers.index("Subtotal") + 1
        col_ongkir = headers.index("Ongkir") + 1

        all_values = ws.get_all_values()
        total = 0.0
        found = False
        updates = []
        for idx, row in enumerate(all_values[1:], start=2):
            if len(row) < col_invoice:
                continue
            if row[col_invoice - 1] != no_invoice:
                continue
            found = True
            try:
                total += float(row[col_subtotal - 1] or 0)
            except ValueError:
                pass
            try:
                total += float(row[col_ongkir - 1] or 0)
            except ValueError:
                pass
            updates.append((idx, col_status, "Lunas"))
            updates.append((idx, col_tgl, _today_str()))
        if not found:
            return None
        for r, c, v in updates:
            ws.update_cell(r, c, v)
        self._safe_close_reminders(no_invoice, "Selesai")
        try:
            self.catat_komisi(no_invoice)
        except Exception:
            logger.exception("gagal catat komisi %s", no_invoice)
        return total

    def unmark_order_lunas(self, no_invoice):
        """Balikin invoice yang kesalahan ditandai Lunas jadi Pending: kosongin
        Tanggal_Bayar, hapus catatan Kas Masuk 'Pelunasan <inv>', dan pasang
        lagi pengingat cek pembayaran. Balikin total, atau None kalau gak ketemu."""
        ws = self._ws(config.SHEET_ORDERS)
        values = ws.get_all_values()
        if not values:
            return None
        headers = values[0]
        c_inv, c_st, c_tgl = headers.index("No_Invoice"), headers.index("Status"), headers.index("Tanggal_Bayar")
        c_sub, c_ong, c_nama = headers.index("Subtotal"), headers.index("Ongkir"), headers.index("Nama_Customer")
        from gspread.utils import rowcol_to_a1
        data, total, nama, found = [], 0.0, "", False
        for i, row in enumerate(values[1:], start=2):
            if len(row) <= c_inv or row[c_inv] != no_invoice:
                continue
            found = True
            nama = row[c_nama] if len(row) > c_nama else nama
            for c in (c_sub, c_ong):
                try:
                    total += float(row[c] or 0) if len(row) > c else 0
                except ValueError:
                    pass
            data.append({"range": rowcol_to_a1(i, c_st + 1), "values": [["Pending"]]})
            data.append({"range": rowcol_to_a1(i, c_tgl + 1), "values": [[""]]})
        if not found:
            return None
        ws.batch_update(data)
        kas = self._ws(config.SHEET_KAS)
        kv = kas.get_all_values()
        if kv:
            kh = kv[0]
            k_ref, k_ket = kh.index("Ref"), kh.index("Keterangan")
            rows_del = [i for i, r in enumerate(kv[1:], start=2)
                        if len(r) > k_ref and r[k_ref] == no_invoice
                        and len(r) > k_ket and str(r[k_ket]).startswith("Pelunasan")]
            for i in sorted(rows_del, reverse=True):
                kas.delete_rows(i)
        try:
            tempo = self.get_tempo(nama, "customer")
            self.add_reminder("bayar_customer", no_invoice, nama, total,
                              _today_date() + datetime.timedelta(days=tempo), "Dibalikin dari Lunas")
        except Exception:
            logger.exception("gagal pasang pengingat ulang %s", no_invoice)
        try:
            self.batal_komisi(no_invoice)
        except Exception:
            logger.exception("gagal batalin komisi %s", no_invoice)
        return total

    def edit_order_header(self, no_invoice, updates):
        """Betulin data header order yang SUDAH kesimpen (nama customer, no
        HP, alamat, metode, no_po_customer, dan/atau tanggal_kirim) -- BUKAN
        item/qty/harga. `updates` dict subset dari {nama_customer, no_hp,
        alamat, metode, no_po_customer, tanggal_kirim} -> nilai baru,
        cuma field yang ada isinya yang diupdate. Update semua baris yang
        share No_Invoice ini (1 order = beberapa baris, 1 per item).
        Balikin True kalau invoice ketemu & keupdate, False kalau enggak
        ketemu."""
        field_to_col = {
            "nama_customer": "Nama_Customer",
            "no_hp": "No_HP",
            "alamat": "Alamat",
            "metode": "Metode",
            "no_po_customer": "No_PO_Customer",
            "tanggal_kirim": "Tanggal_Kirim",
        }
        ws = self._ws(config.SHEET_ORDERS)
        headers = ws.row_values(1)
        col_invoice = headers.index("No_Invoice") + 1
        col_map = {}
        for key, col_name in field_to_col.items():
            val = (updates.get(key) or "").strip()
            if val:
                col_map[key] = (headers.index(col_name) + 1, val)

        if not col_map:
            return False

        all_values = ws.get_all_values()
        found = False
        cell_updates = []
        for idx, row in enumerate(all_values[1:], start=2):
            if len(row) < col_invoice or row[col_invoice - 1] != no_invoice:
                continue
            found = True
            for col, val in col_map.values():
                cell_updates.append((idx, col, val))
        if not found:
            return False
        from gspread.utils import rowcol_to_a1
        ws.batch_update(
            [{"range": rowcol_to_a1(r, c), "values": [[v]]} for r, c, v in cell_updates],
        )  # batch_update default-nya RAW (+62 / 0813 aman)
        if "nama_customer" in updates and (updates.get("nama_customer") or "").strip():
            self.add_customer_if_new(updates["nama_customer"].strip())
        return True

    def edit_order_item_qty(self, no_invoice, item_code, qty_baru=None, harga_baru=None):
        """Ganti Qty dan/atau Harga_Satuan (Subtotal dihitung ulang otomatis
        dari nilai final keduanya) buat 1 item di dalam order tertentu.
        Field yang dikasih None dibiarin sama kayak sebelumnya. Balikin
        True kalau baris item ketemu & keupdate, False kalau enggak (atau
        kalau qty_baru & harga_baru dua-duanya None -- gak ada yang mau
        diubah)."""
        if qty_baru is None and harga_baru is None:
            return False
        ws = self._ws(config.SHEET_ORDERS)
        headers = ws.row_values(1)
        col_invoice = headers.index("No_Invoice") + 1
        col_item_code = headers.index("Item_Code") + 1
        col_qty = headers.index("Qty") + 1
        col_harga = headers.index("Harga_Satuan") + 1
        col_subtotal = headers.index("Subtotal") + 1
        target_code = (item_code or "").strip().upper()
        if not target_code:
            return False
        all_values = ws.get_all_values()
        for idx, row in enumerate(all_values[1:], start=2):
            if len(row) < col_item_code:
                continue
            if row[col_invoice - 1] != no_invoice:
                continue
            if row[col_item_code - 1].strip().upper() != target_code:
                continue
            try:
                qty_val = float(qty_baru) if qty_baru is not None else float(row[col_qty - 1] or 0)
                harga_val = float(harga_baru) if harga_baru is not None else float(row[col_harga - 1] or 0)
            except (TypeError, ValueError):
                return False
            if qty_baru is not None:
                ws.update_cell(idx, col_qty, qty_val)
            if harga_baru is not None:
                ws.update_cell(idx, col_harga, harga_val)
            ws.update_cell(idx, col_subtotal, qty_val * harga_val)
            return True
        return False

    def edit_order_item_product(
        self, no_invoice, old_item_code, new_item_code=None, new_nama_item=None,
        new_kategori=None, new_satuan=None, qty_baru=None, harga_baru=None,
    ):
        """Ganti PRODUK/UKURAN 1 baris item di dalam order tertentu -- dipakai
        pas admin merevisi barang jadi varian/ukuran lain (misal 'PE Susu
        Hippe 30x40' direvisi jadi 'PE Susu Hippe 35x45'), bukan cuma ganti
        qty/harga. Item lama dicari lewat old_item_code + no_invoice. Field
        new_* yang dikasih None/kosong dibiarin sama kayak sebelumnya.
        Subtotal selalu dihitung ulang dari Qty & Harga_Satuan final.
        Balikin True kalau baris ketemu & keupdate, False kalau enggak."""
        ws = self._ws(config.SHEET_ORDERS)
        headers = ws.row_values(1)
        col_invoice = headers.index("No_Invoice") + 1
        col_item_code = headers.index("Item_Code") + 1
        col_nama = headers.index("Nama_Item") + 1
        col_kategori = headers.index("Kategori") + 1
        col_qty = headers.index("Qty") + 1
        col_satuan = headers.index("Satuan") + 1
        col_harga = headers.index("Harga_Satuan") + 1
        col_subtotal = headers.index("Subtotal") + 1
        target_code = (old_item_code or "").strip().upper()
        if not target_code:
            return False
        all_values = ws.get_all_values()
        for idx, row in enumerate(all_values[1:], start=2):
            if len(row) < col_item_code:
                continue
            if row[col_invoice - 1] != no_invoice:
                continue
            if row[col_item_code - 1].strip().upper() != target_code:
                continue
            try:
                qty_val = float(qty_baru) if qty_baru is not None else float(row[col_qty - 1] or 0)
                harga_val = float(harga_baru) if harga_baru is not None else float(row[col_harga - 1] or 0)
            except (TypeError, ValueError):
                return False
            if new_item_code and new_item_code.strip():
                ws.update_cell(idx, col_item_code, new_item_code.strip().upper())
            if new_nama_item and new_nama_item.strip():
                ws.update_cell(idx, col_nama, new_nama_item.strip())
            if new_kategori and new_kategori.strip():
                ws.update_cell(idx, col_kategori, new_kategori.strip())
            if new_satuan and new_satuan.strip():
                ws.update_cell(idx, col_satuan, new_satuan.strip())
            if qty_baru is not None:
                ws.update_cell(idx, col_qty, qty_val)
            if harga_baru is not None:
                ws.update_cell(idx, col_harga, harga_val)
            ws.update_cell(idx, col_subtotal, qty_val * harga_val)
            return True
        return False

    def cancel_order(self, no_invoice):
        """Tandai semua baris dengan No_Invoice ini Status='Batal' -- order
        DIHAPUS/DIBATALIN secara logis (datanya tetep ada buat histori,
        tapi otomatis keluar dari piutang karena get_pending_orders cuma
        ngitung yang Status-nya Pending). Balikin True kalau ketemu, False
        kalau enggak."""
        ws = self._ws(config.SHEET_ORDERS)
        headers = ws.row_values(1)
        col_invoice = headers.index("No_Invoice") + 1
        col_status = headers.index("Status") + 1
        all_values = ws.get_all_values()
        found = False
        for idx, row in enumerate(all_values[1:], start=2):
            if len(row) < col_invoice or row[col_invoice - 1] != no_invoice:
                continue
            found = True
            ws.update_cell(idx, col_status, "Batal")
        if found:
            self._safe_close_reminders(no_invoice, "Batal")
        return found

    def get_pending_orders(self):
        return [r for r in self.get_all_orders() if str(r.get("Status", "")) == "Pending"]

    def get_piutang_summary(self):
        """dict nama_customer -> total belum lunas"""
        out = {}
        for r in self.get_pending_orders():
            nama = r.get("Nama_Customer", "-")
            try:
                subtotal = float(r.get("Subtotal", 0) or 0)
            except ValueError:
                subtotal = 0
            try:
                ongkir = float(r.get("Ongkir", 0) or 0)
            except ValueError:
                ongkir = 0
            out[nama] = out.get(nama, 0) + subtotal + ongkir
        return out

    def get_piutang_detail(self):
        """Piutang per customer (nama yang beda huruf besar/kecil/spasi digabung):
        {kunci: {kunci, nama, total, invoices: [{invoice, tgl, total, umur}]}} urut invoice terlama dulu."""
        hari_ini = _today_date()
        inv = {}
        for r in self.get_pending_orders():
            no = str(r.get("No_Invoice", "")).strip()
            if not no:
                continue
            o = inv.setdefault(no, {"invoice": no, "nama": str(r.get("Nama_Customer", "-")).strip() or "-",
                                    "tgl": str(r.get("Timestamp", ""))[:10], "total": 0.0})
            o["total"] += self._f(r.get("Subtotal")) + self._f(r.get("Ongkir"))
        out = {}
        for o in sorted(inv.values(), key=lambda o: (o["tgl"], o["invoice"])):
            k = _norm(o["nama"]) or "-"
            c = out.setdefault(k, {"kunci": k, "nama": o["nama"], "total": 0.0, "invoices": []})
            try:
                umur = (hari_ini - datetime.datetime.strptime(o["tgl"], "%Y-%m-%d").date()).days
            except ValueError:
                umur = 0
            c["invoices"].append({**o, "umur": umur})
            c["total"] += o["total"]
            if o["nama"].isupper() or len(o["nama"]) > len(c["nama"]):
                c["nama"] = o["nama"]
        return out

    def cocokkan_transfer(self, nominal, customer="", hari=120, maks=6):
        """Transfer masuk Rp `nominal` -> cari kombinasi bon (per customer) yang jumlahnya PAS.
        Bon belum lunas DAN yang udah ditandai lunas (`hari` terakhir) ikut dicek, biar ketahuan
        kalau ada yang kepencet lunas / lupa dipencet. Balikin {"pas": [...], "mirip": [...]}."""
        import itertools
        target = int(round(nominal))
        batas = (_today_date() - datetime.timedelta(days=hari)).strftime("%Y-%m-%d")
        inv = {}
        for r in self.get_all_orders():
            no = str(r.get("No_Invoice", "")).strip()
            st = str(r.get("Status", ""))
            if not no or st == "Batal":
                continue
            o = inv.setdefault(no, {"invoice": no, "customer": str(r.get("Nama_Customer", "")).strip(),
                                    "tgl": str(r.get("Timestamp", ""))[:10], "status": st,
                                    "bayar": str(r.get("Tanggal_Bayar", ""))[:10], "total": 0.0})
            o["total"] += self._f(r.get("Subtotal")) + self._f(r.get("Ongkir"))
        grup = {}
        kc = _norm(customer)
        for o in inv.values():
            if o["status"] == "Lunas" and (o["bayar"] or o["tgl"]) < batas:
                continue
            k = _norm(o["customer"])
            if kc and not (kc in k or k in kc):
                continue
            grup.setdefault(k, []).append(o)
        pas, mirip = [], []
        for k, lst in grup.items():
            # bon belum lunas dulu, terus yang lunas paling baru; maks 22 bon per customer
            lst = sorted([o for o in lst if o["status"] != "Lunas"], key=lambda o: o["tgl"]) + \
                  sorted([o for o in lst if o["status"] == "Lunas"], key=lambda o: o["bayar"], reverse=True)
            lst = lst[:22]
            amt = [int(round(o["total"])) for o in lst]
            for n in range(1, min(maks, len(lst)) + 1):
                for comb in itertools.combinations(range(len(lst)), n):
                    s_ = sum(amt[i] for i in comb)
                    d = target - s_
                    if abs(d) <= 1:
                        pas.append([lst[i] for i in comb])
                    elif 0 < abs(d) <= max(target * 0.01, 5000):
                        mirip.append(([lst[i] for i in comb], d))
                if len(pas) > 40:
                    break

        def skor(c):
            lunas = sum(1 for o in c if o["status"] == "Lunas")
            return (len(c), lunas, min(o["tgl"] for o in c))   # bon paling dikit = paling masuk akal

        def bentuk(c, d=0):
            return {"customer": c[0]["customer"], "selisih": d, "invoices": sorted(c, key=lambda o: o["tgl"]),
                    "belum": [o["invoice"] for o in c if o["status"] != "Lunas"],
                    "sudah": [o["invoice"] for o in c if o["status"] == "Lunas"]}
        pas.sort(key=skor)
        mirip.sort(key=lambda x: (abs(x[1]), skor(x[0])))
        return {"pas": [bentuk(c) for c in pas[:6]], "mirip": [bentuk(c, d) for c, d in mirip[:4]] if not pas else []}

    _lunas_lock = threading.Lock()

    def lunas_banyak(self, invoices, via=""):
        """Customer transfer sekaligus: tandai banyak invoice Lunas + catat Kas Masuk
        per invoice (biar /batallunas tetap bisa). Balikin [(invoice, total)] yang berhasil."""
        hasil = []
        with self._lunas_lock:
            pending = {str(r.get("No_Invoice", "")) for r in self.get_pending_orders()}
            for no in dict.fromkeys(str(i).strip() for i in invoices):
                if no not in pending:
                    continue
                total = self.mark_order_lunas(no)
                if total is None:
                    continue
                self.add_kas_entry("Masuk", "Penjualan", total,
                                   keterangan=f"Pelunasan {no}" + (f" (via {via})" if via else ""), ref=no)
                hasil.append((no, total))
        return hasil

    # ---------------- SUPPLIERS ----------------

    def get_suppliers(self):
        return self._records(self._ws(config.SHEET_SUPPLIERS))

    def get_supplier_names(self):
        return [str(r.get("Nama_Supplier", "")).strip() for r in self.get_suppliers() if r.get("Nama_Supplier")]

    def add_supplier_if_new(self, nama, no_hp="", barang="", alamat=""):
        nama = (nama or "").strip()
        if not nama:
            return
        existing_lower = [n.lower() for n in self.get_supplier_names()]
        if nama.lower() not in existing_lower:
            self._ws(config.SHEET_SUPPLIERS).append_row(
                [nama, no_hp, barang, alamat], value_input_option="RAW"
            )

    # ---------------- PURCHASE ORDERS ----------------

    def get_all_pos(self):
        return self._records(self._ws(config.SHEET_PURCHASE_ORDERS))

    def nama_supplier_baku(self, nama):
        """'csb' / 'Csb' / 'CSB' / alias di PengaturanTagihan -> 1 nama baku
        (yang ada di tab Suppliers), biar PO & utang gak kepisah."""
        nama = (nama or "").strip()
        if not nama:
            return nama
        try:
            daftar = self.get_supplier_names()
        except Exception:
            return nama
        by = {_norm(n): n for n in daftar if n}
        if _norm(nama) in by:
            return by[_norm(nama)]
        try:
            for r in self._records(self._ws(config.SHEET_TAGIHAN)):
                ks = [str(r.get("Nama", ""))] + [a for a in str(r.get("Alias", "")).split(",") if a.strip()]
                if _norm(nama) in {_norm(k) for k in ks}:
                    for k in ks:
                        if _norm(k) in by:
                            return by[_norm(k)]
                    return str(r.get("Nama", "")).strip() or nama
        except Exception:
            pass
        return nama

    def add_purchase_order(self, nama_supplier, items):
        """items: list of dict {nama_item, qty, satuan, harga_satuan}.
        Nulis 1 baris per item dgn No_PO yang sama, status Belum Lunas,
        dan otomatis nambah entry 'Utang Baru' ke UtangSupplier.
        Balikin (no_po, total)."""
        nama_supplier = self.nama_supplier_baku(nama_supplier)
        with self._lock:
            no_po = self.next_po_number()
            ts = _now_str()
            ws = self._ws(config.SHEET_PURCHASE_ORDERS)
            rows = []
            total = 0.0
            for it in items:
                subtotal = float(it["qty"]) * float(it["harga_satuan"])
                total += subtotal
                rows.append([
                    ts, no_po, nama_supplier, it["nama_item"], it["qty"],
                    it.get("satuan", ""), it["harga_satuan"], subtotal,
                    "Belum Lunas", "",
                ])
            ws.append_rows(rows, value_input_option="RAW")
            self.add_supplier_if_new(nama_supplier)
            self._add_utang_entry(nama_supplier, no_po, "Utang Baru", total, "PO baru")
        try:
            self.create_po_reminder(no_po, nama_supplier, total)
        except Exception:
            logger.exception("gagal bikin pengingat PO %s", no_po)
        return no_po, total

    def get_po_items(self, no_po):
        return [r for r in self.get_all_pos() if str(r.get("No_PO", "")) == no_po]

    def get_pos_by_supplier(self, nama_supplier, exclude_status=None):
        nama_lower = (nama_supplier or "").strip().lower()
        out = []
        for r in self.get_all_pos():
            if str(r.get("Nama_Supplier", "")).strip().lower() != nama_lower:
                continue
            if exclude_status and str(r.get("Status", "")) == exclude_status:
                continue
            out.append(r)
        return out

    def get_latest_po_for_supplier(self, nama_supplier):
        """Cari No_PO PALING BARU buat supplier ini yang BELUM dibatalin.
        Coba exact match nama dulu, kalau gak ketemu coba loose-contains
        (biar 'CSB' bisa nemu 'CSB' walau dari sisi lain penulisan agak beda)."""
        pos = self.get_pos_by_supplier(nama_supplier, exclude_status="Batal")
        if not pos:
            nama_lower = (nama_supplier or "").strip().lower()
            if nama_lower:
                pos = [
                    r for r in self.get_all_pos()
                    if nama_lower in str(r.get("Nama_Supplier", "")).strip().lower()
                    and str(r.get("Status", "")) != "Batal"
                ]
        if not pos:
            return None
        return sorted(pos, key=lambda r: str(r.get("Timestamp", "")))[-1].get("No_PO")

    def cancel_po(self, no_po):
        """Tandai semua baris No_PO ini Status='Batal', dan balikin (reverse)
        utang yang otomatis kecatet pas PO ini disimpan -- biar PO yang
        batal gak lagi keitung di utang supplier. Balikin
        (found, nama_supplier, total)."""
        ws = self._ws(config.SHEET_PURCHASE_ORDERS)
        headers = ws.row_values(1)
        col_po = headers.index("No_PO") + 1
        col_status = headers.index("Status") + 1
        col_supplier = headers.index("Nama_Supplier") + 1
        col_subtotal = headers.index("Subtotal") + 1
        all_values = ws.get_all_values()
        found = False
        nama_supplier = ""
        total = 0.0
        for idx, row in enumerate(all_values[1:], start=2):
            if len(row) < col_po or row[col_po - 1] != no_po:
                continue
            if row[col_status - 1] == "Batal":
                continue  # udah dibatalin sebelumnya, jangan dobel reverse utang
            found = True
            nama_supplier = row[col_supplier - 1]
            try:
                total += float(row[col_subtotal - 1] or 0)
            except (TypeError, ValueError):
                pass
            ws.update_cell(idx, col_status, "Batal")
        if found and total:
            with self._lock:
                self._add_utang_entry(nama_supplier, no_po, "Batal PO", total, "PO dibatalin, utang dibalikin")
        if found:
            self._safe_close_reminders(no_po, "Batal")
        return found, nama_supplier, total

    _bayar_po_lock = threading.Lock()

    def bayar_po(self, no_po, via="dashboard"):
        """PO udah dibayar ke supplier: kurangin utang (nilai PO + penyesuaian barang
        lebih/kurang), catat Kas Keluar, tandai PO Lunas, tutup pengingat. Gak bisa dobel.
        Balikin (supplier, total) atau None kalau PO gak ada / udah lunas / batal."""
        with self._bayar_po_lock:
            rows = self.get_po_items(no_po)
            st = str(rows[0].get("Status", "")) if rows else ""
            if not rows or st in ("Lunas", "Batal"):
                return None
            sup = self.nama_supplier_baku(str(rows[0].get("Nama_Supplier", "")))
            total = sum(self._f(r.get("Subtotal")) for r in rows) + self.penyesuaian_po(no_po)
            self.bayar_utang(sup, total, f"Pelunasan {no_po}")
            self.add_kas_entry("Keluar", "Bayar Supplier", total,
                               keterangan=f"Bayar utang {sup} {no_po} (via {via})", ref=no_po)
            self.mark_po_lunas(no_po)
            try:
                self.close_reminders_for_ref(no_po, "Selesai")
            except Exception:
                pass
            return sup, total

    def mark_po_lunas(self, no_po):
        ws = self._ws(config.SHEET_PURCHASE_ORDERS)
        headers = ws.row_values(1)
        col_po = headers.index("No_PO") + 1
        col_status = headers.index("Status") + 1
        col_tgl = headers.index("Tanggal_Lunas") + 1
        all_values = ws.get_all_values()
        found = False
        for idx, row in enumerate(all_values[1:], start=2):
            if len(row) >= col_po and row[col_po - 1] == no_po:
                found = True
                ws.update_cell(idx, col_status, "Lunas")
                ws.update_cell(idx, col_tgl, _today_str())
        if found:
            self._safe_close_reminders(no_po, "Selesai")
        return found

    # ---------------- UTANG SUPPLIER ----------------

    def _get_saldo_utang(self, nama_supplier):
        total = 0.0
        kunci = {_norm(nama_supplier), _norm(self.nama_supplier_baku(nama_supplier))}
        for r in self._records(self._ws(config.SHEET_UTANG_SUPPLIER)):
            n = str(r.get("Nama_Supplier", "")).strip()
            if _norm(n) not in kunci and _norm(self.nama_supplier_baku(n)) not in kunci:
                continue
            try:
                jumlah = float(r.get("Jumlah", 0) or 0)
            except ValueError:
                jumlah = 0
            if r.get("Jenis") == "Utang Baru":
                total += jumlah
            elif r.get("Jenis") in ("Pembayaran", "Batal PO"):
                total -= jumlah
            elif r.get("Jenis") == "Penyesuaian":
                total += jumlah  # + = barang datang lebih, - = kurang
        return total

    def _add_utang_entry(self, nama_supplier, no_po, jenis, jumlah, catatan=""):
        saldo = self._get_saldo_utang(nama_supplier)
        saldo_baru = saldo + jumlah if jenis in ("Utang Baru", "Penyesuaian") else saldo - jumlah
        self._ws(config.SHEET_UTANG_SUPPLIER).append_row(
            [_today_str(), nama_supplier, no_po, jenis, jumlah, saldo_baru, catatan],
            value_input_option="RAW",
        )
        return saldo_baru

    def bayar_utang(self, nama_supplier, jumlah, catatan=""):
        """Catat pembayaran ke supplier. Balikin sisa utang setelah dibayar."""
        nama_supplier = self.nama_supplier_baku(nama_supplier)
        with self._lock:
            saldo_baru = self._add_utang_entry(nama_supplier, "", "Pembayaran", jumlah, catatan)
        return saldo_baru

    def get_utang_summary(self):
        """dict nama_supplier -> sisa utang (cuma yang > 0)"""
        names = {}
        for r in self._records(self._ws(config.SHEET_UTANG_SUPPLIER)):
            nama = str(r.get("Nama_Supplier", "")).strip()
            if nama:
                baku = self.nama_supplier_baku(nama)
                names.setdefault(_norm(baku), baku)
        names = list(names.values())
        out = {}
        for nama in names:
            saldo = self._get_saldo_utang(nama)
            if round(saldo) != 0:
                out[nama] = saldo
        return out

    # ---------------- PENGINGAT ----------------

    def get_tagihan_setting(self, nama, tipe):
        """Baris PengaturanTagihan buat customer/supplier ini (cocok persis
        nama/alias dulu, lalu cocok sebagian), atau None."""
        n = _norm(nama)
        if not n:
            return None
        rows = [r for r in self._records(self._ws(config.SHEET_TAGIHAN))
                if str(r.get("Tipe", "")).strip().lower() == tipe.lower()]

        def keys(r):
            ks = [_norm(r.get("Nama", ""))] + [_norm(a) for a in str(r.get("Alias", "")).split(",")]
            return [k for k in ks if k]

        for r in rows:
            if n in keys(r):
                return r
        for r in rows:
            for k in keys(r):
                if len(k) >= 4 and (k in n or (len(n) >= 4 and n in k)):
                    return r
        return None

    def get_tempo(self, nama, tipe):
        st = self.get_tagihan_setting(nama, tipe)
        default = config.DEFAULT_TEMPO_CUSTOMER if tipe.lower() == "customer" else config.DEFAULT_TEMPO_SUPPLIER
        try:
            v = int(float((st or {}).get("Tempo_Hari") or default))
            return v if v > 0 else default
        except (TypeError, ValueError):
            return default

    def add_reminder(self, jenis, ref, nama, jumlah, tanggal, catatan=""):
        """jenis: kontra_bon | bayar_customer | bayar_supplier. tanggal: date/str."""
        rid = "R" + uuid.uuid4().hex[:7]
        tgl = tanggal.strftime("%Y-%m-%d") if hasattr(tanggal, "strftime") else str(tanggal)[:10]
        self._ws(config.SHEET_PENGINGAT).append_row(
            [rid, jenis, ref, nama, jumlah, tgl, "Aktif", "", _now_str(), catatan],
            value_input_option="RAW",
        )
        return rid

    def _reminder_records(self):
        return self._records(self._ws(config.SHEET_PENGINGAT))

    def get_reminder(self, rid):
        for r in self._reminder_records():
            if str(r.get("ID", "")) == rid:
                return r
        return None

    def get_active_reminders(self):
        out = [r for r in self._reminder_records() if str(r.get("Status", "")) == "Aktif"]
        return sorted(out, key=lambda r: (str(r.get("Tanggal", "")), str(r.get("Ref", ""))))

    def get_due_reminders(self, today_str):
        """Pengingat Aktif yang tanggalnya udah tiba/lewat dan belum dikirim hari ini."""
        return [r for r in self.get_active_reminders()
                if str(r.get("Tanggal", "")) <= today_str and str(r.get("Terkirim_Tgl", "")) != today_str]

    def tandai_kontra_bon(self, ref):
        """Invoice `ref` udah di-kontra bon: tutup pengingat kontra bon-nya dan
        pasang pengingat cek pembayaran sesuai tempo. Balikin (tempo, due) atau None."""
        rem = next((r for r in self.get_active_reminders()
                    if r.get("Jenis") == "kontra_bon" and str(r.get("Ref", "")) == ref), None)
        if not rem:
            return None
        tempo = config.KONTRABON_TEMPO_HARI
        due = _today_date() + datetime.timedelta(days=tempo)
        self.update_reminder(rem["ID"], Status="Selesai")
        self.add_reminder("bayar_customer", ref, rem.get("Nama", ""), rem.get("Jumlah", 0), due,
                          "Cek pembayaran setelah kontra bon")
        return tempo, due

    def update_reminder(self, rid, **fields):
        """fields: Status / Tanggal / Terkirim_Tgl / Catatan."""
        from gspread.utils import rowcol_to_a1
        ws = self._ws(config.SHEET_PENGINGAT)
        values = ws.get_all_values()
        if not values:
            return False
        headers = values[0]
        for i, row in enumerate(values[1:], start=2):
            if row and row[0] == rid:
                data = []
                for k, v in fields.items():
                    if k in headers:
                        v = v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else v
                        data.append({"range": rowcol_to_a1(i, headers.index(k) + 1), "values": [[v]]})
                if data:
                    ws.batch_update(data)
                return True
        return False

    # ---------------- ORDER ONLINE ----------------

    # ---------------- STOK GUDANG ----------------
    # Stok dihitung dari: hitungan terakhir (Jenis "Hitung" = jumlah sebenarnya
    # di gudang saat itu) + barang Masuk/Penyesuaian setelahnya - semua qty
    # order (yang gak Batal) setelah hitungan itu. Jadi edit/batal order
    # otomatis ikut, tanpa perlu catat stok keluar manual.

    @staticmethod
    def _f(v, default=0.0):
        try:
            return float(str(v).replace(",", ".").strip())
        except (TypeError, ValueError):
            return default

    def add_mutasi(self, entries):
        """entries: list dict {item_code,nama,jenis,qty,satuan,ref,catatan,oleh}."""
        if not entries:
            return 0
        ts = _now_str()
        rows = [[ts, e["item_code"], e.get("nama", ""), e["jenis"], e["qty"], e.get("satuan", ""),
                 e.get("ref", ""), e.get("catatan", ""), e.get("oleh", "")] for e in entries]
        self._ws(config.SHEET_MUTASI).append_rows(rows, value_input_option="RAW")
        return len(rows)

    def get_stok_all(self):
        """List dict per produk: code,nama,kategori,satuan,isi_bal,min,stok(None=belum dihitung),status."""
        produk = [r for r in self.get_price_list() if str(r.get("Item_Code", "")).strip()]
        mut = self._records(self._ws(config.SHEET_MUTASI))
        by_item = {}
        for m in mut:
            by_item.setdefault(str(m.get("Item_Code", "")).strip().upper(), []).append(m)
        orders = [o for o in self.get_all_orders() if str(o.get("Status", "")) != "Batal"]
        ord_by = {}
        for o in orders:
            ord_by.setdefault(str(o.get("Item_Code", "")).strip().upper(), []).append(o)
        # barang yang "distok": dipesan / khusus customer langganan (Grandia, Shu Guo, ...)
        langganan = [k for k in getattr(config, "STOK_PANTAU_CUSTOMER", []) if k]

        def _langganan(nama):
            n = _norm(nama)
            return any(k in n for k in langganan)

        pantau = {str(o.get("Item_Code", "")).strip().upper() for o in orders if _langganan(o.get("Nama_Customer", ""))}
        for r in produk:
            if any(_langganan(x) for x in str(r.get("Khusus_Customer", "")).split(",") if x.strip()):
                pantau.add(str(r["Item_Code"]).strip().upper())
        out = []
        for r in produk:
            code = str(r["Item_Code"]).strip()
            ms = sorted(by_item.get(code.upper(), []), key=lambda m: str(m.get("Waktu", "")))
            hit = [m for m in ms if m.get("Jenis") == "Hitung"]
            stok, t0, estimasi = None, "", False
            masuk_aja = [m for m in ms if m.get("Jenis") in ("Masuk", "Penyesuaian")]
            if not hit and masuk_aja:
                # belum ada hitung awal, tapi udah ada barang masuk: hitung sementara
                # dari barang masuk dikurangi penjualan SETELAH barang masuk pertama
                estimasi = True
                t0 = str(masuk_aja[0].get("Waktu", ""))
                stok = sum(self._f(m.get("Qty")) for m in masuk_aja)
                for o in ord_by.get(code.upper(), []):
                    if str(o.get("Timestamp", "")) > t0:
                        stok -= self._f(o.get("Qty"))
            if hit:
                t0 = str(hit[-1].get("Waktu", ""))
                stok = self._f(hit[-1].get("Qty"))
                for m in ms:
                    if str(m.get("Waktu", "")) > t0 and m.get("Jenis") in ("Masuk", "Penyesuaian"):
                        stok += self._f(m.get("Qty"))
                for o in ord_by.get(code.upper(), []):
                    if str(o.get("Timestamp", "")) > t0:
                        stok -= self._f(o.get("Qty"))
            mn = self._f(r.get("Stok_Min"))
            auto_min = False
            if mn <= 0 and code.upper() in pantau:
                mn = float(getattr(config, "STOK_MIN_KATEGORI", {}).get(str(r.get("Kategori", "")).strip().upper(), 0))
                auto_min = mn > 0
            if stok is None:
                status = "belum"
            elif stok <= 0:
                status = "habis"
            elif mn > 0 and stok <= mn:
                status = "menipis"
            else:
                status = "aman"
            out.append({"code": code, "nama": r.get("Nama", "") + (
                        " - " + str(r.get("Deskripsi")) if str(r.get("Deskripsi", "")).strip() not in ("", "POLOS") else ""),
                        "kategori": r.get("Kategori", ""), "satuan": r.get("Satuan", ""),
                        "isi_bal": self._f(r.get("Isi_Bal")), "min": mn, "stok": stok, "status": status,
                        "estimasi": estimasi, "auto_min": auto_min, "dipantau": mn > 0})
        return out

    def get_mutasi_recent(self, n=15):
        rows = self._records(self._ws(config.SHEET_MUTASI))
        return sorted(rows, key=lambda m: str(m.get("Waktu", "")), reverse=True)[:n]

    def set_stok_setting(self, code, field, value):
        """field: 'min' atau 'isi_bal' -> kolom Stok_Min / Isi_Bal di PriceList."""
        from gspread.utils import rowcol_to_a1
        ws = self._ws(config.SHEET_PRICELIST)
        values = ws.get_all_values()
        headers = values[0]
        col = headers.index("Stok_Min" if field == "min" else "Isi_Bal")
        c_code = headers.index("Item_Code")
        for i, row in enumerate(values[1:], start=2):
            if len(row) > c_code and row[c_code].strip().upper() == code.strip().upper():
                ws.batch_update([{"range": rowcol_to_a1(i, col + 1), "values": [[value]]}])
                return True
        return False

    def set_supplier_produk(self, codes, supplier):
        """Isi kolom Supplier di PriceList buat banyak kode sekaligus (1x tulis)."""
        from gspread.utils import rowcol_to_a1
        supplier = self.nama_supplier_baku(supplier)
        ws = self._ws(config.SHEET_PRICELIST)
        values = ws.get_all_values()
        h = values[0]
        if "Supplier" not in h:
            return 0
        c_code, c_sup = h.index("Item_Code"), h.index("Supplier")
        want = {str(c).strip().upper() for c in codes}
        data = [{"range": rowcol_to_a1(i, c_sup + 1), "values": [[supplier]]}
                for i, row in enumerate(values[1:], start=2)
                if len(row) > c_code and row[c_code].strip().upper() in want]
        if data:
            ws.batch_update(data)
        try:
            self.add_supplier_if_new(supplier)
        except Exception:
            pass
        return len(data)

    # ---------------- STAFF GUDANG ----------------

    @staticmethod
    def _hash_pw(pw, salt):
        import hashlib
        return hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 120_000).hex()

    def _staff_rows(self):
        return self._records(self._ws(config.SHEET_STAFF))

    def create_staff(self, nama):
        """Bikin akun staff baru. Balikin (id, password_polos) -- password cuma
        keliatan sekali ini; di sheet disimpen cuma hash-nya."""
        import re
        import secrets
        base = re.sub(r"[^a-z0-9]", "", nama.lower())[:12] or "staff"
        ids = {str(r.get("ID", "")).lower() for r in self._staff_rows()}
        sid, n = base, 1
        while sid in ids:
            n += 1
            sid = f"{base}{n}"
        alfabet = "abcdefghjkmnpqrstuvwxyz23456789"
        pw = "".join(secrets.choice(alfabet) for _ in range(8))
        salt = secrets.token_hex(8)
        self._ws(config.SHEET_STAFF).append_row(
            [sid, nama, self._hash_pw(pw, salt), salt, "YA", _now_str()], value_input_option="RAW")
        return sid, pw

    def reset_staff_password(self, sid, pw=None):
        """pw=None -> bikin acak. Balikin password baru, atau None kalau ID gak ada."""
        import secrets
        ws = self._ws(config.SHEET_STAFF)
        for i, row in enumerate(ws.get_all_values()[1:], start=2):
            if row and row[0].lower() == sid.lower():
                alfabet = "abcdefghjkmnpqrstuvwxyz23456789"
                pw = pw or "".join(secrets.choice(alfabet) for _ in range(8))
                salt = secrets.token_hex(8)
                ws.batch_update([{"range": f"C{i}:D{i}", "values": [[self._hash_pw(pw, salt), salt]]}])
                return pw
        return None

    def set_staff_aktif(self, sid, aktif):
        ws = self._ws(config.SHEET_STAFF)
        for i, row in enumerate(ws.get_all_values()[1:], start=2):
            if row and row[0].lower() == sid.lower():
                ws.batch_update([{"range": f"E{i}", "values": [["YA" if aktif else "TIDAK"]]}])
                return True
        return False

    def verify_staff(self, sid, pw):
        import hmac
        for r in self._staff_rows():
            if str(r.get("ID", "")).lower() == str(sid).strip().lower():
                if str(r.get("Aktif", "")).upper() == "TIDAK":
                    return None
                h = self._hash_pw(pw, str(r.get("Salt", "")))
                if hmac.compare_digest(h, str(r.get("Hash", ""))):
                    return {"id": r["ID"], "nama": r.get("Nama", "")}
        return None

    def get_staff_info(self, sid):
        for r in self._staff_rows():
            if str(r.get("ID", "")).lower() == str(sid).lower() and str(r.get("Aktif", "")).upper() != "TIDAK":
                return {"id": r["ID"], "nama": r.get("Nama", "")}
        return None

    def list_staff(self):
        return [{"id": r.get("ID"), "nama": r.get("Nama"), "aktif": str(r.get("Aktif", "")).upper() != "TIDAK"}
                for r in self._staff_rows()]

    # pengajuan stok (staff ajukan -> owner setujui)
    def add_pengajuan(self, staff, jenis, entries, ref=""):
        """jenis: Masuk | Hitung. entries: [{item_code,nama,qty,satuan}]. Balikin batch id."""
        batch = "B" + uuid.uuid4().hex[:6].upper()
        ts = _now_str()
        rows = [[f"{batch}-{i + 1}", batch, ts, staff, jenis, e["item_code"], e.get("nama", ""), e["qty"],
                 e.get("satuan", ""), ref, "Menunggu", "", "", ""] for i, e in enumerate(entries)]
        self._ws(config.SHEET_PENGAJUAN).append_rows(rows, value_input_option="RAW")
        return batch

    def set_pesan_tg(self, batch, refs):
        """Simpen id pesan Telegram (chat:msg;...) buat 1 batch pengajuan, biar
        tombolnya bisa diilangin kalau udah diputuskan dari tempat lain."""
        from gspread.utils import rowcol_to_a1
        ws = self._ws(config.SHEET_PENGAJUAN)
        values = ws.get_all_values()
        if not values or "Pesan_TG" not in values[0]:
            return False
        h = values[0]
        cb, cp = h.index("Batch"), h.index("Pesan_TG")
        for i, row in enumerate(values[1:], start=2):
            if len(row) > cb and row[cb] == batch:
                ws.batch_update([{"range": rowcol_to_a1(i, cp + 1),
                                  "values": [[";".join(f"{c}:{m}" for c, m in refs)]]}])
                return True
        return False

    def get_pesan_tg(self, batch):
        for r in self._records(self._ws(config.SHEET_PENGAJUAN)):
            if str(r.get("Batch", "")) == batch and str(r.get("Pesan_TG", "")).strip():
                out = []
                for part in str(r["Pesan_TG"]).split(";"):
                    try:
                        c, m = part.rsplit(":", 1)
                        out.append((int(c), int(m)))
                    except ValueError:
                        continue
                return out
        return []

    def get_pengajuan(self, status=None, staff=None):
        rows = self._records(self._ws(config.SHEET_PENGAJUAN))
        if status:
            rows = [r for r in rows if r.get("Status") == status]
        if staff:
            rows = [r for r in rows if str(r.get("Staff", "")) == staff]
        return rows

    def set_stok_owner(self, code, qty, oleh="owner (dashboard)"):
        """Owner langsung nyetel stok real 1 barang (dicatat sebagai Hitung)."""
        p = next((r for r in self.get_price_list() if str(r.get("Item_Code", "")).strip().upper() == str(code).strip().upper()), None)
        if not p:
            return False
        self.add_mutasi([{"item_code": str(p["Item_Code"]).strip(), "nama": self._label_produk(p), "jenis": "Hitung",
                          "qty": qty, "satuan": str(p.get("Satuan", "")), "ref": "", "catatan": "Diubah owner",
                          "oleh": oleh}])
        return True

    def get_pengajuan_disetujui(self, hari=3):
        """Batch pengajuan stok yang udah DISETUJUI beberapa hari terakhir (buat dicek / dijadiin stok real)."""
        batas = (_today_date() - datetime.timedelta(days=hari)).strftime("%Y-%m-%d")
        by = {}
        for r in self.get_pengajuan("Disetujui"):
            if str(r.get("Diputuskan_Waktu", "") or r.get("Waktu", ""))[:10] < batas:
                continue
            b = by.setdefault(r["Batch"], {"batch": r["Batch"], "staff": r.get("Staff", ""), "jenis": r.get("Jenis", ""),
                                            "waktu": str(r.get("Diputuskan_Waktu", "") or r.get("Waktu", "")),
                                            "ref": r.get("Ref", ""), "items": []})
            b["items"].append({"code": r.get("Item_Code", ""), "nama": r.get("Nama", ""), "qty": r.get("Qty", ""),
                               "satuan": r.get("Satuan", "")})
        real = self._batch_udah_real()
        # hitung stok (opname) terakhir per barang -> kiriman yang lebih lama dari itu udah "ketimpa"
        hitung_akhir = {}
        for m in self._records(self._ws(config.SHEET_MUTASI)):
            if m.get("Jenis") == "Hitung":
                k = str(m.get("Item_Code", "")).strip().upper()
                hitung_akhir[k] = max(hitung_akhir.get(k, ""), str(m.get("Waktu", "")))
        for b in by.values():
            b["sudah_real"] = real.get(b["batch"], "")
            codes = [str(i["code"]).strip().upper() for i in b["items"]]
            b["ketimpa"] = bool(codes) and all(hitung_akhir.get(k, "") > b["waktu"] for k in codes)
            b["beres"] = bool(b["sudah_real"] or b["ketimpa"] or b["jenis"] == "Hitung")
        return sorted(by.values(), key=lambda b: b["waktu"], reverse=True)

    def _batch_udah_real(self):
        """{batch: waktu} buat batch yang udah pernah 'Dijadiin stok real'."""
        out = {}
        for m in self._records(self._ws(config.SHEET_MUTASI)):
            if m.get("Jenis") == "Hitung" and str(m.get("Catatan", "")).startswith("Dijadiin stok real dari "):
                out[str(m.get("Ref", ""))] = str(m.get("Waktu", ""))
        return out

    def jadikan_stok_real(self, batch, oleh="owner (dashboard)"):
        """Angka di 1 batch yang udah disetujui dijadiin STOK REAL sekarang (Hitung).
        Balikin jumlah barang, 0 kalau batch gak ada, -1 kalau udah pernah."""
        rows = [r for r in self.get_pengajuan("Disetujui") if r.get("Batch") == batch]
        if not rows:
            return 0
        if batch in self._batch_udah_real():
            return -1
        self.add_mutasi([{"item_code": r["Item_Code"], "nama": r.get("Nama", ""), "jenis": "Hitung", "qty": r.get("Qty"),
                          "satuan": r.get("Satuan", ""), "ref": batch, "catatan": f"Dijadiin stok real dari {batch}",
                          "oleh": oleh} for r in rows])
        return len(rows)

    _putus_lock = threading.Lock()

    def decide_pengajuan(self, batch, approve, oleh="owner"):
        """Setujui/tolak 1 batch (cuma yang masih 'Menunggu', jadi gak bisa dobel).
        Dikunci biar klik Telegram & dashboard barengan tetap cuma 1 yang jalan."""
        with self._putus_lock:
            return self._decide_pengajuan(batch, approve, oleh)

    def _decide_pengajuan(self, batch, approve, oleh="owner"):
        """Setujui/tolak 1 batch. Kalau disetujui -> masuk ke MutasiStok. Balikin jumlah baris, atau None."""
        from gspread.utils import rowcol_to_a1
        ws = self._ws(config.SHEET_PENGAJUAN)
        values = ws.get_all_values()
        if not values:
            return None
        h = values[0]
        cb, cs, co, cw = h.index("Batch"), h.index("Status"), h.index("Diputuskan_Oleh"), h.index("Diputuskan_Waktu")
        data, entries = [], []
        for i, row in enumerate(values[1:], start=2):
            if len(row) > cs and row[cb] == batch and row[cs] == "Menunggu":
                st = "Disetujui" if approve else "Ditolak"
                data += [{"range": rowcol_to_a1(i, cs + 1), "values": [[st]]},
                         {"range": rowcol_to_a1(i, co + 1), "values": [[oleh]]},
                         {"range": rowcol_to_a1(i, cw + 1), "values": [[_now_str()]]}]
                entries.append({"item_code": row[h.index("Item_Code")], "nama": row[h.index("Nama")],
                                "jenis": row[h.index("Jenis")], "qty": row[h.index("Qty")],
                                "satuan": row[h.index("Satuan")], "ref": row[h.index("Ref")] or batch,
                                "catatan": f"Pengajuan {batch}", "oleh": row[h.index("Staff")]})
        if not entries:
            return None
        if approve:
            self.add_mutasi(entries)
        ws.batch_update(data)
        try:
            ref0 = str(entries[0].get("ref", ""))
            if ref0.upper().startswith(config.PO_PREFIX):
                self.set_penerimaan_status(batch, "Diterima" if approve else "Ditolak")
                if approve:
                    self.sesuaikan_utang_po(ref0.strip())
        except Exception:
            logger.exception("gagal update status penerimaan PO")
        return len(entries)

    # ---------------- TERIMA PO (staff cek barang datang) ----------------

    @staticmethod
    def _label_produk(p):
        """Sama persis dengan label di PO (Nama + (Deskripsi) kalau bukan POLOS)."""
        nama = str(p.get("Nama", "") or "")
        d = str(p.get("Deskripsi", "") or "").strip()
        return f"{nama} ({d})" if d and d.upper() != "POLOS" else nama

    def _cocok_produk(self, nama_item, produk):
        n = _norm(nama_item)
        for p in produk:
            if _norm(self._label_produk(p)) == n:
                return p
        for p in produk:
            if _norm(p.get("Nama", "")) == n:
                return p
        return None

    def _kandidat(self, nama_item, produk, cocok=None, n=6):
        """Produk PriceList yang mirip nama barang di PO (buat pilihan staff)."""
        import difflib
        q = _norm(nama_item)
        qt = set(str(nama_item).lower().replace("(", " ").replace(")", " ").replace("x", " x ").split())
        skor = []
        for p in produk:
            lab = self._label_produk(p)
            sc_ = difflib.SequenceMatcher(None, q, _norm(lab)).ratio()
            pt = set(lab.lower().replace("(", " ").replace(")", " ").replace("x", " x ").split())
            if qt and pt:
                sc_ += 0.5 * len(qt & pt) / max(len(qt), 1)
            skor.append((sc_, p))
        skor.sort(key=lambda x: -x[0])
        out = []
        for sc_, p in skor:
            if cocok is not None and str(p["Item_Code"]) == str(cocok["Item_Code"]):
                continue
            if sc_ < 0.45 and len(out) >= 2:
                break
            out.append({"code": str(p["Item_Code"]).strip(), "nama": self._label_produk(p),
                        "satuan": str(p.get("Satuan", "") or "")})
            if len(out) >= n:
                break
        return out

    def _po_terbuka_rows(self):
        return [r for r in self.get_all_pos() if str(r.get("Status", "")) != "Batal" and str(r.get("No_PO", "")).strip()]

    def _po_lines(self):
        """{no_po: info} buat semua PO yang gak Batal, lengkap dengan berapa yang
        SUDAH diterima (pengajuan disetujui) per baris -- jadi PO bisa datang
        nyicil (misal pesan 5000, datang 1000 dulu)."""
        import json as _json
        produk = [p for p in self.get_price_list() if str(p.get("Item_Code", "")).strip()]
        by_code = {str(p["Item_Code"]).strip().upper(): p for p in produk}
        pen = self._records(self._ws(config.SHEET_PENERIMAAN))
        peta, menunggu, ditutup = {}, set(), set()
        for r in pen:
            no, st = str(r.get("No_PO", "")), str(r.get("Status", ""))
            if st == "Ditolak":
                continue
            if st == "Menunggu":
                menunggu.add(no)
            if st == "Ditutup":
                ditutup.add(no)
            try:
                for k, v in (_json.loads(r.get("Peta") or "{}") or {}).items():
                    if v:
                        peta.setdefault(no, {})[_norm(k)] = str(v).strip().upper()
            except (ValueError, AttributeError):
                pass
        diterima = {}
        for r in self._records(self._ws(config.SHEET_PENGAJUAN)):
            if str(r.get("Status", "")) != "Disetujui":
                continue
            ref = str(r.get("Ref", "")).strip()
            if not ref.upper().startswith(config.PO_PREFIX):
                continue
            k = str(r.get("Item_Code", "")).strip().upper()
            diterima.setdefault(ref, {})
            diterima[ref][k] = diterima[ref].get(k, 0.0) + self._f(r.get("Qty"))
        out = {}
        for r in self._po_terbuka_rows():
            no = str(r["No_PO"]).strip()
            d = out.setdefault(no, {"po": no, "supplier": str(r.get("Nama_Supplier", "")),
                                    "tgl": str(r.get("Timestamp", ""))[:10], "items": [],
                                    "menunggu": no in menunggu, "ditutup": no in ditutup})
            nama = str(r.get("Item", ""))
            p = self._cocok_produk(nama, produk)
            code = str(p["Item_Code"]).strip() if p else ""
            if not p and _norm(nama) in peta.get(no, {}):
                p = by_code.get(peta[no][_norm(nama)])
                code = str(p["Item_Code"]).strip() if p else ""
            qty = self._f(r.get("Qty"))
            sat = str(r.get("Satuan", "") or "")
            isi = self._f((p or {}).get("Isi_Bal"))
            unit = "bal" if (p and isi > 0 and sat.strip().lower() == "bal") else "sat"
            kali = isi if unit == "bal" else 1.0
            d["items"].append({"nama": nama, "qty": qty, "satuan": sat, "code": code, "unit": unit,
                               "kali": kali, "pesan_stok": qty * kali, "harga": self._f(r.get("Harga_Satuan")),
                               "satuan_stok": str((p or {}).get("Satuan", "") or sat),
                               "_p": p})
        # baris PO yang namanya gak cocok katalog & belum ada peta: tebak dari barang yang
        # beneran pernah diterima buat PO ini (biar penerimaan lama tetap kehitung)
        import difflib
        for no, d in out.items():
            dapat = [k for k in diterima.get(no, {}) if k]
            dipakai = {it["code"].upper() for it in d["items"] if it["code"]}
            sisa = [k for k in dapat if k not in dipakai]
            for it in d["items"]:
                if it["code"] or not sisa:
                    continue
                k = max(sisa, key=lambda c: difflib.SequenceMatcher(
                    None, _norm(it["nama"]), _norm(self._label_produk(by_code.get(c, {})) or c)).ratio())
                p = by_code.get(k)
                sisa.remove(k)
                it["code"] = str(p["Item_Code"]).strip() if p else k
                it["satuan_stok"] = str((p or {}).get("Satuan", "") or it["satuan_stok"])
                # satuan PO lama (KG) beda sama satuan stok (Pak): anggap 1 baris PO = 1 kiriman
                if p and str(p.get("Satuan", "")).strip().lower() != it["satuan"].strip().lower():
                    it["kali"] = (diterima[no].get(k, 0.0) / it["qty"]) if it["qty"] else 1.0
                    it["pesan_stok"] = it["qty"] * it["kali"]
        # bagi yang udah diterima ke baris-baris PO (per kode barang, urut)
        for no, d in out.items():
            sisa_kode = dict(diterima.get(no, {}))
            for it in d["items"]:
                k = it["code"].upper()
                dapat = min(it["pesan_stok"], sisa_kode.get(k, 0.0)) if k else 0.0
                if k:
                    sisa_kode[k] = sisa_kode.get(k, 0.0) - dapat
                it["diterima_stok"] = dapat
                it["sisa_stok"] = max(it["pesan_stok"] - dapat, 0.0)
                it["sisa"] = round(it["sisa_stok"] / it["kali"], 3) if it["kali"] else it["sisa_stok"]
            d["lengkap"] = all(it["code"] and it["sisa_stok"] <= 0.0001 for it in d["items"])
            d["sebagian"] = any(it["diterima_stok"] > 0 for it in d["items"])
        return out

    def get_po_untuk_terima(self, hanya_belum=True, limit=40):
        """PO + item buat dicek staff gudang. PO hilang dari daftar kalau semua
        barangnya udah datang lengkap, atau ditutup owner."""
        produk = [p for p in self.get_price_list() if str(p.get("Item_Code", "")).strip()]
        res = []
        sejak = getattr(config, "TERIMA_PO_SEJAK", "")
        for d in sorted(self._po_lines().values(), key=lambda d: d["po"], reverse=True):
            if hanya_belum and sejak and d["tgl"] and d["tgl"] < sejak and not d["menunggu"]:
                continue
            if d["menunggu"]:
                st = "Menunggu"
            elif d["ditutup"]:
                st = "Ditutup"
            elif d["lengkap"]:
                st = "Diterima"
            elif d["sebagian"]:
                st = "Sebagian"
            else:
                st = ""
            if hanya_belum and st in ("Diterima", "Ditutup"):
                continue
            d["status_terima"] = st
            for it in d["items"]:
                p = it.pop("_p")
                it["kandidat"] = self._kandidat(it["nama"], produk, p)
            res.append(d)
            if len(res) >= limit:
                break
        return res

    def add_penerimaan(self, no_po, batch, staff, catatan="", peta=None):
        import json as _json
        self._ws(config.SHEET_PENERIMAAN).append_row(
            [no_po, "Menunggu", batch, staff, _now_str(), catatan,
             _json.dumps(peta or {}, ensure_ascii=False)], value_input_option="RAW")

    def tutup_po(self, no_po, oleh="owner"):
        """Owner nutup PO yang sisanya gak bakal dikirim supplier -> utang
        disesuaikan ke barang yang beneran datang."""
        self._ws(config.SHEET_PENERIMAAN).append_row(
            [no_po, "Ditutup", "", oleh, _now_str(), "Ditutup owner (sisa gak dikirim)", "{}"],
            value_input_option="RAW")
        try:
            return self.sesuaikan_utang_po(no_po)
        except Exception:
            logger.exception("gagal sesuaikan utang %s", no_po)
            return 0.0

    def cari_penyesuaian_salah(self):
        """Catatan 'Penyesuaian' utang buat PO LAMA (sebelum TERIMA_PO_SEJAK) -- itu
        muncul gara-gara PO lama ke-input ulang di Terima PO, bukan barang beneran lebih."""
        sejak = getattr(config, "TERIMA_PO_SEJAK", "")
        tgl_po = {}
        for r in self.get_all_pos():
            tgl_po.setdefault(str(r.get("No_PO", "")), str(r.get("Timestamp", ""))[:10])
        ws = self._ws(config.SHEET_UTANG_SUPPLIER)
        values = ws.get_all_values()
        h = values[0] if values else []
        if "Jenis" not in h:
            return []
        cj, cp, cn, cm = h.index("Jenis"), h.index("No_PO"), h.index("Nama_Supplier"), h.index("Jumlah")
        out = []
        for i, row in enumerate(values[1:], start=2):
            if len(row) > cj and row[cj] == "Penyesuaian":
                po = row[cp]
                if sejak and tgl_po.get(po, "9999") < sejak:
                    out.append({"baris": i, "po": po, "supplier": row[cn], "jumlah": self._f(row[cm]),
                                "tgl": row[0]})
        return out

    def hapus_penyesuaian_salah(self):
        """Hapus catatan dari cari_penyesuaian_salah() (dari bawah biar nomor baris gak geser)."""
        with self._lock:
            rows = self.cari_penyesuaian_salah()
            ws = self._ws(config.SHEET_UTANG_SUPPLIER)
            for r in sorted(rows, key=lambda r: -r["baris"]):
                ws.delete_rows(r["baris"])
            return rows

    def penyesuaian_po(self, no_po):
        """Total penyesuaian utang (bertanda) yang udah dicatat buat PO ini."""
        tot = 0.0
        for r in self._records(self._ws(config.SHEET_UTANG_SUPPLIER)):
            if str(r.get("No_PO", "")) == no_po and r.get("Jenis") == "Penyesuaian":
                tot += self._f(r.get("Jumlah"))
        return tot

    def sesuaikan_utang_po(self, no_po):
        """Utang supplier ngikutin barang yang BENERAN datang:
        - selama PO masih kebuka: yang ditagih = max(pesan, datang) per barang
          (sisanya dianggap masih bakal dateng)
        - kalau PO udah lengkap / ditutup: yang ditagih = yang datang.
        Selisih dari nilai PO dicatat sebagai 'Penyesuaian' di UtangSupplier.
        Balikin selisih yang baru dicatat (0 kalau gak ada perubahan)."""
        d = self._po_lines().get(no_po)
        if not d:
            return 0.0
        final = d["lengkap"] or d["ditutup"]
        nilai_po = tagih = 0.0
        for it in d["items"]:
            datang = it["diterima_stok"] / it["kali"] if it["kali"] else it["diterima_stok"]
            # kelebihan kiriman: _po_lines nge-cap diterima di jumlah pesanan, jadi hitung ulang lebihnya
            nilai_po += it["qty"] * it["harga"]
            q = datang if final else max(it["qty"], datang)
            tagih += q * it["harga"]
        lebih = self._kelebihan_po(no_po, d)
        tagih += lebih
        delta = round(tagih - nilai_po - self.penyesuaian_po(no_po))
        if abs(delta) < 1:
            return 0.0
        ket = (f"Barang datang {'lebih' if delta > 0 else 'kurang'} dari PO"
               + (" (PO ditutup)" if d["ditutup"] else ""))
        with self._lock:
            self._add_utang_entry(d["supplier"], no_po, "Penyesuaian", delta, ket)
        try:
            baru = nilai_po + self.penyesuaian_po(no_po)
            for r in self.get_active_reminders():
                if r.get("Jenis") == "bayar_supplier" and str(r.get("Ref", "")) == no_po:
                    self.update_reminder(r["ID"], Jumlah=round(baru))
        except Exception:
            logger.exception("gagal update pengingat bayar %s", no_po)
        return float(delta)

    def _kelebihan_po(self, no_po, d):
        """Nilai barang yang datang MELEBIHI pesanan (per kode barang)."""
        dapat = {}
        for r in self._records(self._ws(config.SHEET_PENGAJUAN)):
            if str(r.get("Status", "")) == "Disetujui" and str(r.get("Ref", "")).strip() == no_po:
                k = str(r.get("Item_Code", "")).strip().upper()
                dapat[k] = dapat.get(k, 0.0) + self._f(r.get("Qty"))
        pesan, harga_stok = {}, {}
        for it in d["items"]:
            k = it["code"].upper()
            if not k:
                continue
            pesan[k] = pesan.get(k, 0.0) + it["pesan_stok"]
            harga_stok.setdefault(k, it["harga"] / it["kali"] if it["kali"] else it["harga"])
        return sum(max(dapat.get(k, 0.0) - pesan[k], 0.0) * harga_stok[k] for k in pesan)

    def set_penerimaan_status(self, batch, status):
        ws = self._ws(config.SHEET_PENERIMAAN)
        for i, row in enumerate(ws.get_all_values()[1:], start=2):
            if len(row) > 2 and row[2] == batch:
                ws.batch_update([{"range": f"B{i}", "values": [[status]]}])
                return True
        return False

    def po_banding(self, no_po, diterima):
        """Bandingin PO vs yang datang SEKARANG (diterima: {item_code: qty satuan stok}).
        Balikin list {nama, pesan, sebelumnya, terima, sisa, satuan, selisih}."""
        d = self._po_lines().get(no_po)
        out, sisa_kode = [], {k.upper(): v for k, v in diterima.items()}
        for it in (d or {}).get("items", []):
            k = it["code"].upper()
            now = min(it["sisa_stok"], sisa_kode.get(k, 0.0)) if k else 0.0
            if k:
                sisa_kode[k] = sisa_kode.get(k, 0.0) - now
            out.append({"nama": it["nama"], "pesan": it["pesan_stok"], "sebelumnya": it["diterima_stok"],
                        "terima": now, "sisa": it["sisa_stok"] - now, "satuan": it["satuan_stok"],
                        "selisih": now - it["sisa_stok"]})
        for k, v in sisa_kode.items():
            if v > 0.0001:
                ada = next((o for o in reversed(out) if (d and any(i["code"].upper() == k and i["nama"] == o["nama"] for i in d["items"]))), None)
                if ada:
                    ada["terima"] += v
                    ada["selisih"] += v
                    ada["sisa"] -= v
                else:
                    out.append({"nama": k, "pesan": 0, "sebelumnya": 0, "terima": v, "sisa": -v, "satuan": "",
                                "selisih": v})
        return out

    # permintaan barang (staff minta owner order)
    def add_permintaan(self, staff, entries):
        ts = _now_str()
        rows = []
        for e in entries:
            rows.append(["Q" + uuid.uuid4().hex[:6].upper(), ts, staff, e["item_code"], e.get("nama", ""),
                         e["qty"], e.get("satuan", ""), e.get("catatan", ""), "Baru"])
        self._ws(config.SHEET_PERMINTAAN).append_rows(rows, value_input_option="RAW")
        return [r[0] for r in rows]

    def get_permintaan(self, staff=None, status=None, n=50):
        rows = self._records(self._ws(config.SHEET_PERMINTAAN))
        if staff:
            rows = [r for r in rows if r.get("Staff") == staff]
        if status:
            rows = [r for r in rows if r.get("Status") == status]
        return sorted(rows, key=lambda r: str(r.get("Waktu", "")), reverse=True)[:n]

    def set_permintaan_status(self, pid, status):
        ws = self._ws(config.SHEET_PERMINTAAN)
        for i, row in enumerate(ws.get_all_values()[1:], start=2):
            if row and row[0] == pid:
                ws.batch_update([{"range": f"I{i}", "values": [[status]]}])
                return True
        return False

    _po_minta_lock = threading.Lock()

    def buat_po_dari_permintaan(self, pids):
        """Permintaan barang staff (status Baru) -> PO otomatis, dikelompokin per
        Supplier (kolom Supplier di PriceList), harga = Harga_Beli. Balikin
        (daftar_po, gagal): daftar_po = [{no_po, supplier, items, total}],
        gagal = [{nama, alasan}] buat barang yang supplier/harga belinya kosong."""
        with self._po_minta_lock:
            want = {str(p) for p in pids}
            # "Selesai" = udah keburu ditandai beres tapi belum dibikinin PO -> boleh diulang
            rows = [r for r in self.get_permintaan(None, None, 1000)
                    if str(r.get("ID", "")) in want and r.get("Status") in ("Baru", "Selesai")]
            pl = {str(p.get("Item_Code", "")).strip().upper(): p for p in self.get_price_list()}
            per_sup, gagal = {}, []
            for r in rows:
                p = pl.get(str(r.get("Item_Code", "")).strip().upper())
                sup = str((p or {}).get("Supplier", "") or "").strip()
                hb = self._f((p or {}).get("Harga_Beli"))
                if not p or not sup or hb <= 0:
                    gagal.append({"id": r.get("ID"), "nama": r.get("Nama", ""), "code": str(r.get("Item_Code", "")),
                              "kategori": str((p or {}).get("Kategori", "")),
                              "kurang": "supplier" if p and not sup else "harga" if p else "produk",
                                  "alasan": "Supplier kosong di PriceList" if p and not sup else
                                  "Harga beli kosong di PriceList" if p else "Barang gak ada di PriceList"})
                    continue
                per_sup.setdefault(sup, []).append((r, p, hb))
            return self._po_per_supplier(per_sup), gagal

    def _po_per_supplier(self, per_sup):
        """per_sup: {supplier: [(row_permintaan_atau_None, produk, harga_beli[, qty])]} -> bikin PO."""
        hasil = []
        if True:
            for sup, isi in per_sup.items():
                gabung = {}
                for t in isi:
                    r, p, hb = t[0], t[1], t[2]
                    r = r or {"Qty": t[3] if len(t) > 3 else 0, "ID": "", "Satuan": p.get("Satuan", "")}
                    k = str(p["Item_Code"]).strip().upper()
                    g = gabung.setdefault(k, {"nama_item": self._label_produk(p), "qty": 0.0,
                                              "satuan": str(p.get("Satuan", "") or r.get("Satuan", "")),
                                              "harga_satuan": hb, "_ids": []})
                    g["qty"] += self._f(r.get("Qty"))
                    g["_ids"].append(str(r.get("ID")))
                items = list(gabung.values())
                no_po, total = self.add_purchase_order(sup, [{k: v for k, v in i.items() if k != "_ids"} for i in items])
                for i in items:
                    for pid in i["_ids"]:
                        if pid:
                            self.set_permintaan_status(pid, f"PO {no_po}")
                hasil.append({"no_po": no_po, "supplier": sup, "total": total,
                              "items": [{k: v for k, v in i.items() if k != "_ids"} for i in items]})
        return hasil

    def qty_order_default(self, p):
        """Jumlah order otomatis: kolom Qty_Order, atau aturan kategori (mis. SAMPAH 125)."""
        q = self._f(p.get("Qty_Order"))
        if q > 0:
            return q
        return float(config.QTY_ORDER_KATEGORI.get(str(p.get("Kategori", "")).strip().upper(), 0))

    def po_sedang_jalan(self):
        """{item_code: [(no_po, sisa_stok)]} buat PO yang barangnya belum datang lengkap."""
        out = {}
        for d in self._po_lines().values():
            if d["lengkap"] or d["ditutup"]:
                continue
            for it in d["items"]:
                if it["code"] and it["sisa_stok"] > 0:
                    out.setdefault(it["code"].upper(), []).append((d["po"], it["sisa_stok"]))
        return out

    def saran_order(self, codes=None):
        """Barang menipis/habis + jumlah order + supplier + PO yang lagi jalan."""
        pl = {str(p.get("Item_Code", "")).strip().upper(): p for p in self.get_price_list()}
        jalan = self.po_sedang_jalan()
        out = []
        for i in self.get_stok_all():
            # cuma barang yang distok (ada Stok_Min / dipesan langganan) yang di-alert
            if i["status"] not in ("habis", "menipis") or not i.get("dipantau"):
                continue
            k = str(i["code"]).upper()
            if codes is not None and k not in codes:
                continue
            p = pl.get(k, {})
            out.append({**i, "qty_order": self.qty_order_default(p), "supplier": str(p.get("Supplier", "") or "").strip(),
                        "harga_beli": self._f(p.get("Harga_Beli")), "po_jalan": jalan.get(k, [])})
        return out

    _po_stok_lock = threading.Lock()

    def buat_po_barang(self, pesanan):
        """pesanan: [(item_code, qty)] -> PO per supplier. Balikin (daftar_po, gagal)."""
        with self._po_stok_lock:
            pl = {str(p.get("Item_Code", "")).strip().upper(): p for p in self.get_price_list()}
            per_sup, gagal = {}, []
            for code, qty in pesanan:
                p = pl.get(str(code).strip().upper())
                sup = str((p or {}).get("Supplier", "") or "").strip()
                hb = self._f((p or {}).get("Harga_Beli"))
                if not p or not sup or hb <= 0 or qty <= 0:
                    gagal.append({"code": code, "nama": self._label_produk(p) if p else code,
                                  "alasan": "Barang gak ada di PriceList" if not p else "Supplier kosong (isi pakai /supplier)"
                                  if not sup else "Harga beli kosong" if hb <= 0 else "Jumlah 0"})
                    continue
                per_sup.setdefault(sup, []).append((None, p, hb, qty))
            return self._po_per_supplier(per_sup), gagal

    def permintaan_nunggu_po(self, codes=None):
        """Permintaan (Baru / Selesai tanpa PO) -- opsional cuma buat kode tertentu."""
        want = {str(c).upper() for c in codes} if codes else None
        return [r for r in self.get_permintaan(None, None, 1000)
                if r.get("Status") in ("Baru", "Selesai")
                and (want is None or str(r.get("Item_Code", "")).upper() in want)]

    def permintaan_satu_kiriman(self, pid):
        """Semua ID permintaan (status Baru) yang dikirim barengan sama `pid`."""
        rows = self.get_permintaan(None, None, 500)
        r0 = next((r for r in rows if str(r.get("ID", "")) == pid), None)
        if not r0:
            return []
        return [str(r["ID"]) for r in rows if r.get("Waktu") == r0.get("Waktu") and r.get("Staff") == r0.get("Staff")
                and r.get("Status") in ("Baru", "Selesai")]

    # pengiriman order (staff tandai barang udah keluar/dikirim)
    def get_pengiriman_map(self):
        return {str(r.get("No_Invoice", "")): r for r in self._records(self._ws(config.SHEET_PENGIRIMAN))}

    def set_pengiriman(self, no_invoice, staff):
        ws = self._ws(config.SHEET_PENGIRIMAN)
        for i, row in enumerate(ws.get_all_values()[1:], start=2):
            if row and row[0] == no_invoice:
                ws.batch_update([{"range": f"A{i}:D{i}", "values": [[no_invoice, "Dikirim", staff, _now_str()]]}])
                return
        ws.append_row([no_invoice, "Dikirim", staff, _now_str()], value_input_option="RAW")

    def set_pengiriman_banyak(self, invoices, staff):
        """Tandai banyak invoice 'Dikirim' sekaligus (1x baca, 1x tulis)."""
        ws = self._ws(config.SHEET_PENGIRIMAN)
        ada = {row[0] for row in ws.get_all_values()[1:] if row}
        baru = [[inv, "Dikirim", staff, _now_str()] for inv in dict.fromkeys(invoices) if inv and inv not in ada]
        if baru:
            ws.append_rows(baru, value_input_option="RAW")
        return len(baru)

    def get_orders_gudang(self, limit=40):
        """Order customer yang gak Batal, dikelompokin per invoice, terbaru dulu."""
        by = {}
        for r in self.get_all_orders():
            if str(r.get("Status", "")) == "Batal":
                continue
            inv = str(r.get("No_Invoice", ""))
            d = by.setdefault(inv, {"invoice": inv, "customer": r.get("Nama_Customer", ""),
                                    "alamat": r.get("Alamat", ""), "metode": r.get("Metode", ""),
                                    "tgl": str(r.get("Timestamp", ""))[:10], "kirim": str(r.get("Tanggal_Kirim", "")),
                                    "po": r.get("No_PO_Customer", ""), "items": []})
            d["items"].append({"nama": r.get("Nama_Item", ""), "qty": r.get("Qty", ""), "satuan": r.get("Satuan", "")})
        kirim = self.get_pengiriman_map()
        out = []
        for d in sorted(by.values(), key=lambda d: d["invoice"], reverse=True)[:limit]:
            k = kirim.get(d["invoice"])
            d["dikirim"] = bool(k)
            d["dikirim_oleh"] = (k or {}).get("Staff", "")
            d["dikirim_waktu"] = str((k or {}).get("Waktu", ""))
            out.append(d)
        return out

    # ---------------- KOMISI "JALUR BELAKANG" (RAHASIA, cuma owner) ----------------

    def get_komisi_setting(self):
        """{norm(customer): {customer, rate, penerima, catatan}}"""
        out = {}
        for r in self._records(self._ws(config.SHEET_KOMISI)):
            nm = str(r.get("Customer", "")).strip()
            rate = self._f(r.get("Rp_per_Satuan"))
            if nm and rate > 0:
                out[_norm(nm)] = {"customer": nm, "rate": rate, "penerima": str(r.get("Penerima", "")).strip(),
                                  "catatan": str(r.get("Catatan", "")).strip()}
        return out

    def komisi_untuk(self, customer):
        return self.get_komisi_setting().get(_norm(customer))

    def set_komisi(self, customer, rate, penerima="", catatan=""):
        """Pasang/ubah komisi customer. rate <= 0 -> hapus. Balikin 'baru'/'ubah'/'hapus'/None."""
        from gspread.utils import rowcol_to_a1
        ws = self._ws(config.SHEET_KOMISI)
        values = ws.get_all_values()
        key = _norm(customer)
        for i, row in enumerate(values[1:], start=2):
            if row and _norm(row[0]) == key:
                if rate <= 0:
                    ws.delete_rows(i)
                    return "hapus"
                ws.batch_update([{"range": f"A{i}:D{i}", "values": [[customer, rate, penerima or (row[2] if len(row) > 2 else ""),
                                                                     catatan or (row[3] if len(row) > 3 else "")]]}])
                return "ubah"
        if rate <= 0:
            return None
        ws.append_row([customer, rate, penerima, catatan], value_input_option="RAW")
        return "baru"

    def _komisi_rows(self):
        return self._records(self._ws(config.SHEET_KOMISI_CATAT))

    def get_komisi_catat(self, no_invoice):
        for r in self._komisi_rows():
            if str(r.get("No_Invoice", "")) == no_invoice and str(r.get("Status", "")) != "Batal":
                return r
        return None

    def catat_komisi(self, no_invoice):
        """Dipanggil pas invoice LUNAS: kalau customer-nya punya komisi, catat
        tagihan komisinya (status Belum). Gak dobel. Balikin baris atau None."""
        ada = self.get_komisi_catat(no_invoice)
        if ada:
            return ada
        rows = self.get_order_items(no_invoice)
        if not rows:
            return None
        nama = str(rows[0].get("Nama_Customer", "")).strip()
        st = self.komisi_untuk(nama)
        if not st:
            return None
        qty = sum(self._f(r.get("Qty")) for r in rows if str(r.get("Status", "")) != "Batal")
        jumlah = round(qty * st["rate"])
        if jumlah <= 0:
            return None
        row = [no_invoice, nama, st["penerima"], qty, st["rate"], jumlah, "Belum", _now_str(), ""]
        self._ws(config.SHEET_KOMISI_CATAT).append_row(row, value_input_option="RAW")
        return dict(zip(SCHEMA[config.SHEET_KOMISI_CATAT], row))

    def get_komisi_belum(self):
        return [r for r in self._komisi_rows() if str(r.get("Status", "")) == "Belum"]

    def _set_komisi_status(self, no_invoice, dari, ke, tgl=""):
        ws = self._ws(config.SHEET_KOMISI_CATAT)
        values = ws.get_all_values()
        h = values[0] if values else []
        if "Status" not in h:
            return None
        cs, cd = h.index("Status"), h.index("Dibayar")
        from gspread.utils import rowcol_to_a1
        for i, row in enumerate(values[1:], start=2):
            if row and row[0] == no_invoice and len(row) > cs and row[cs] == dari:
                ws.batch_update([{"range": rowcol_to_a1(i, cs + 1), "values": [[ke]]},
                                 {"range": rowcol_to_a1(i, cd + 1), "values": [[tgl]]}])
                return dict(zip(h, row))
        return None

    _komisi_lock = threading.Lock()

    def bayar_komisi(self, no_invoice):
        """Tandai komisi invoice ini SUDAH DIBAYAR + catat Kas Keluar 'Komisi'.
        Balikin baris komisinya, atau None kalau gak ada / udah dibayar."""
        with self._komisi_lock:
            r = self._set_komisi_status(no_invoice, "Belum", "Dibayar", _today_str())
            if not r:
                return None
            jumlah = self._f(r.get("Jumlah"))
            ket = f"Komisi {r.get('Penerima') or '-'} ({r.get('Customer')}) {no_invoice}"
            self.add_kas_entry("Keluar", "Komisi", jumlah, keterangan=ket, ref=no_invoice)
            return r

    def batal_komisi(self, no_invoice):
        """Invoice dibalikin ke Pending -> komisi yang belum dibayar dibatalin."""
        return self._set_komisi_status(no_invoice, "Belum", "Batal")

    # ---------------- CEK HARGA (customer / supplier / barang) ----------------

    def cek_harga(self, query):
        """Cari harga berdasarkan nama CUSTOMER (harga terakhir dia beli + harga
        khusus), nama SUPPLIER (harga beli terakhir di PO + Harga_Beli PriceList),
        atau nama BARANG (harga jual & beli PriceList).
        Balikin {"customer": [...], "supplier": [...], "produk": [...]}."""
        q = _norm(query)
        out = {"customer": [], "supplier": [], "produk": []}
        if not q:
            return out
        pl = [p for p in self.get_price_list() if str(p.get("Item_Code", "")).strip()]
        pl_by = {str(p["Item_Code"]).strip().upper(): p for p in pl}

        import difflib

        def cocok(nama):
            n = _norm(nama)
            if not n:
                return False
            if q in n or (n in q and len(n) >= 4):
                return True
            # toleran salah ketik dikit (hippie ~ hippe, basoyen ~ baso yen)
            if len(q) >= 4 and difflib.SequenceMatcher(None, q, n).ratio() >= 0.8:
                return True
            return len(q) >= 4 and difflib.SequenceMatcher(None, q, n[:len(q) + 1]).ratio() >= 0.85

        # --- customer ---
        cust = {}
        for r in self.get_all_orders():
            nm = str(r.get("Nama_Customer", "")).strip()
            if not cocok(nm) or str(r.get("Status", "")) == "Batal":
                continue
            key = _norm(nm)
            c = cust.setdefault(key, {"nama": nm, "items": {}})
            code = str(r.get("Item_Code", "")).strip().upper()
            item = str(r.get("Nama_Item", "")).strip()
            k = code or _norm(item)
            ts = str(r.get("Timestamp", ""))
            lama = c["items"].get(k)
            if lama is None or ts >= lama["tgl"]:
                c["items"][k] = {"nama": item, "harga": self._f(r.get("Harga_Satuan")), "code": code,
                                 "satuan": str(r.get("Satuan", "")), "tgl": ts, "sumber": "terakhir beli",
                                 "inv": str(r.get("No_Invoice", ""))}
        for nm in [str(r.get("Nama", "")).strip() for r in self.get_customers()]:
            if cocok(nm):
                cust.setdefault(_norm(nm), {"nama": nm, "items": {}})
        for r in self._records(self._ws(config.SHEET_HARGA_CUSTOMER)):
            key = _norm(r.get("Customer", ""))
            if key in cust:
                code = str(r.get("Item_Code", "")).strip().upper()
                p = pl_by.get(code, {})
                cust[key]["items"][code] = {"nama": self._label_produk(p) if p else code, "code": code,
                                            "harga": self._f(r.get("Harga_Jual")),
                                            "satuan": str(p.get("Satuan", "")), "tgl": "",
                                            "sumber": "harga khusus", "inv": ""}
        for p in pl:
            khusus = [_norm(x) for x in str(p.get("Khusus_Customer", "")).split(",") if x.strip()]
            for key in cust:
                code = str(p["Item_Code"]).strip().upper()
                if key in khusus and code not in cust[key]["items"]:
                    cust[key]["items"][code] = {"nama": self._label_produk(p), "harga": self._f(p.get("Harga_Jual")), "code": code,
                                                "satuan": str(p.get("Satuan", "")), "tgl": "",
                                                "sumber": "katalog khusus", "inv": ""}
        kom = self.get_komisi_setting()
        for key, c in cust.items():
            c["items"] = sorted(c["items"].values(), key=lambda i: i["nama"].lower())
            c["komisi"] = kom.get(key)
            out["customer"].append(c)

        # --- supplier ---
        sup = {}
        for r in self.get_all_pos():
            nm = str(r.get("Nama_Supplier", "")).strip()
            if not cocok(nm) or str(r.get("Status", "")) == "Batal":
                continue
            s_ = sup.setdefault(_norm(nm), {"nama": nm, "items": {}})
            item = str(r.get("Item", "")).strip()
            ts = str(r.get("Timestamp", ""))
            lama = s_["items"].get(_norm(item))
            if lama is None or ts >= lama["tgl"]:
                s_["items"][_norm(item)] = {"nama": item, "harga": self._f(r.get("Harga_Satuan")),
                                            "satuan": str(r.get("Satuan", "")), "tgl": ts,
                                            "sumber": "PO terakhir", "inv": str(r.get("No_PO", ""))}
        for nm in self.get_supplier_names():
            if cocok(nm):
                sup.setdefault(_norm(nm), {"nama": nm, "items": {}})
        for p in pl:
            key = _norm(p.get("Supplier", ""))
            if key and (key in sup or cocok(p.get("Supplier", ""))):
                s_ = sup.setdefault(key, {"nama": str(p.get("Supplier", "")).strip(), "items": {}})
                lab = self._label_produk(p)
                if _norm(lab) not in s_["items"] and self._f(p.get("Harga_Beli")) > 0:
                    s_["items"][_norm(lab)] = {"nama": lab, "harga": self._f(p.get("Harga_Beli")),
                                               "satuan": str(p.get("Satuan", "")), "tgl": "",
                                               "sumber": "PriceList", "inv": ""}
        for s_ in sup.values():
            s_["items"] = sorted(s_["items"].values(), key=lambda i: i["nama"].lower())
            out["supplier"].append(s_)

        # --- barang (kalau bukan nama customer/supplier) ---
        if not out["customer"] and not out["supplier"]:
            _, rows = self.cari_produk_massal(query)
            for p in rows[:40]:
                out["produk"].append({"code": str(p.get("Item_Code", "")), "nama": self._label_produk(p),
                                      "satuan": str(p.get("Satuan", "")), "jual": self._f(p.get("Harga_Jual")),
                                      "beli": self._f(p.get("Harga_Beli")),
                                      "supplier": str(p.get("Supplier", "") or "")})
        return out

    def set_harga_customer(self, customer, code, harga):
        """Pasang/ubah harga jual KHUSUS 1 customer buat 1 barang (tab HargaCustomer)."""
        ws = self._ws(config.SHEET_HARGA_CUSTOMER)
        code = str(code).strip().upper()
        for i, row in enumerate(ws.get_all_values()[1:], start=2):
            if len(row) > 1 and _norm(row[0]) == _norm(customer) and row[1].strip().upper() == code:
                ws.batch_update([{"range": f"C{i}", "values": [[harga]]}])
                return "ubah"
        ws.append_row([customer, code, harga], value_input_option="RAW")
        return "baru"

    def get_harga_customer(self, nama):
        """{ITEM_CODE: harga khusus} buat 1 customer (tab HargaCustomer)."""
        out = {}
        for r in self._records(self._ws(config.SHEET_HARGA_CUSTOMER)):
            if str(r.get("Customer", "")).strip().lower() == str(nama).strip().lower():
                code = str(r.get("Item_Code", "")).strip().upper()
                try:
                    h = float(r.get("Harga_Jual"))
                except (TypeError, ValueError):
                    continue
                if code and h > 0:
                    out[code] = h
        return out

    def get_link_by_token(self, token):
        for r in self._records(self._ws(config.SHEET_LINKORDER)):
            if str(r.get("Token", "")) == token and str(r.get("Aktif", "")).strip().upper() != "TIDAK":
                return r
        return None

    def get_or_create_link(self, nama):
        for r in self._records(self._ws(config.SHEET_LINKORDER)):
            if str(r.get("Nama_Customer", "")).strip().lower() == nama.strip().lower() \
                    and str(r.get("Aktif", "")).strip().upper() != "TIDAK":
                return str(r["Token"])
        token = uuid.uuid4().hex[:14]
        self._ws(config.SHEET_LINKORDER).append_row([token, nama, "YA", _now_str()], value_input_option="RAW")
        return token

    def add_pesanan_web(self, pid, nama, payload_json):
        self._ws(config.SHEET_PESANANWEB).append_row(
            [pid, _now_str(), nama, payload_json, "Menunggu"], value_input_option="RAW")

    def get_pesanan_web(self, pid):
        for r in self._records(self._ws(config.SHEET_PESANANWEB)):
            if str(r.get("ID", "")) == pid:
                return r
        return None

    def set_pesanan_web_status(self, pid, status):
        ws = self._ws(config.SHEET_PESANANWEB)
        for i, row in enumerate(ws.get_all_values()[1:], start=2):
            if row and row[0] == pid:
                ws.batch_update([{"range": f"E{i}", "values": [[status]]}])
                return True
        return False

    def get_topik_all(self):
        """{kunci: (chat_id, thread_id|None)} dari tab TopikGrup."""
        out = {}
        for r in self._records(self._ws(config.SHEET_TOPIK)):
            k = str(r.get("Kunci", "")).strip()
            if not k:
                continue
            try:
                chat = int(float(str(r.get("Chat_ID", "")).strip()))
            except ValueError:
                continue
            t = str(r.get("Thread_ID", "")).strip()
            out[k] = (chat, int(float(t)) if t else None)
        return out

    def set_topik(self, kunci, chat_id, thread_id):
        ws = self._ws(config.SHEET_TOPIK)
        values = ws.get_all_values()
        for i, row in enumerate(values[1:], start=2):
            if row and row[0] == kunci:
                ws.batch_update([{"range": f"B{i}:C{i}", "values": [[str(chat_id), str(thread_id or "")]]}])
                return
        ws.append_row([kunci, str(chat_id), str(thread_id or "")], value_input_option="RAW")

    def close_reminders_for_ref(self, ref, status="Selesai"):
        """Tutup semua pengingat Aktif buat invoice/PO ini (lunas / dibatalin)."""
        from gspread.utils import rowcol_to_a1
        ws = self._ws(config.SHEET_PENGINGAT)
        values = ws.get_all_values()
        if not values:
            return 0
        headers = values[0]
        c_ref, c_status = headers.index("Ref"), headers.index("Status")
        data = []
        for i, row in enumerate(values[1:], start=2):
            if len(row) > max(c_ref, c_status) and row[c_ref] == ref and row[c_status] == "Aktif":
                data.append({"range": rowcol_to_a1(i, c_status + 1), "values": [[status]]})
        if data:
            ws.batch_update(data)
        return len(data)

    def _safe_close_reminders(self, ref, status):
        try:
            self.close_reminders_for_ref(ref, status)
        except Exception:
            logger.exception("gagal nutup pengingat %s", ref)

    def create_invoice_reminders(self, no_invoice, nama, total, base_date=None):
        """Dipanggil tiap invoice terbit. Customer yang punya hari kontra bon:
        ingetin di hari itu (08.00). Selain itu: ingetin cek pembayaran
        setelah tempo (default 14 hari) dari tanggal invoice."""
        today = _today_date()
        try:
            base = datetime.datetime.strptime(str(base_date)[:10], "%Y-%m-%d").date() if base_date else today
        except ValueError:
            base = today
        st = self.get_tagihan_setting(nama, "customer")
        idx = hari_index((st or {}).get("Hari_Kontra_Bon"))
        if idx is not None:
            due = next_weekday(today, idx)
            return self.add_reminder("kontra_bon", no_invoice, nama, total, due,
                                     f"Kontra bon hari {HARI_ID[idx]}")
        tempo = self.get_tempo(nama, "customer")
        due = max(base + datetime.timedelta(days=tempo), today + datetime.timedelta(days=1))
        return self.add_reminder("bayar_customer", no_invoice, nama, total, due, f"Tempo {tempo} hari")

    def create_po_reminder(self, no_po, nama_supplier, total, base_date=None):
        tempo = self.get_tempo(nama_supplier, "supplier")
        today = _today_date()
        try:
            base = datetime.datetime.strptime(str(base_date)[:10], "%Y-%m-%d").date() if base_date else today
        except ValueError:
            base = today
        due = max(base + datetime.timedelta(days=tempo), today + datetime.timedelta(days=1))
        return self.add_reminder("bayar_supplier", no_po, nama_supplier, total, due, f"Tempo {tempo} hari")

    def backfill_reminders(self):
        """Bikinin pengingat buat invoice Pending & PO Belum Lunas yang belum
        punya pengingat sama sekali. Balikin (jumlah_invoice, jumlah_po)."""
        have = {str(r.get("Ref", "")) for r in self._reminder_records()}
        n_inv = n_po = 0
        seen = set()
        for r in self.get_pending_orders():
            inv = str(r.get("No_Invoice", ""))
            if inv in have or inv in seen:
                continue
            seen.add(inv)
            rows = self.get_order_items(inv)
            total = sum(float(x.get("Subtotal", 0) or 0) for x in rows)
            total += float(rows[0].get("Ongkir", 0) or 0)
            self.create_invoice_reminders(inv, r.get("Nama_Customer", ""), total, str(r.get("Timestamp", ""))[:10])
            n_inv += 1
        seen = set()
        for r in self.get_all_pos():
            po = str(r.get("No_PO", ""))
            if po in have or po in seen or str(r.get("Status", "")) != "Belum Lunas":
                continue
            seen.add(po)
            total = sum(float(x.get("Subtotal", 0) or 0) for x in self.get_po_items(po))
            self.create_po_reminder(po, r.get("Nama_Supplier", ""), total, str(r.get("Timestamp", ""))[:10])
            n_po += 1
        return n_inv, n_po

    # ---------------- KAS ----------------

    def add_kas_entry(self, jenis, kategori, jumlah, keterangan="", ref="", tanggal=None):
        """jenis: 'Masuk' atau 'Keluar'"""
        self._ws(config.SHEET_KAS).append_row(
            [tanggal or _today_str(), jenis, kategori, jumlah, keterangan, ref],
            value_input_option="RAW",
        )

    def get_kas_entries(self, year=None, month=None):
        rows = self._records(self._ws(config.SHEET_KAS))
        if not year or not month:
            return rows
        prefix = f"{year:04d}-{month:02d}"
        return [r for r in rows if str(r.get("Tanggal", "")).startswith(prefix)]

    def get_laporan_bulanan(self, year, month):
        entries = self.get_kas_entries(year, month)
        masuk_by_kategori = {}
        keluar_by_kategori = {}
        total_masuk = 0.0
        total_keluar = 0.0
        for r in entries:
            try:
                jumlah = float(r.get("Jumlah", 0) or 0)
            except ValueError:
                jumlah = 0
            kategori = r.get("Kategori", "Lainnya") or "Lainnya"
            if r.get("Jenis") == "Masuk":
                masuk_by_kategori[kategori] = masuk_by_kategori.get(kategori, 0) + jumlah
                total_masuk += jumlah
            elif r.get("Jenis") == "Keluar":
                keluar_by_kategori[kategori] = keluar_by_kategori.get(kategori, 0) + jumlah
                total_keluar += jumlah
        return {
            "masuk_by_kategori": masuk_by_kategori,
            "keluar_by_kategori": keluar_by_kategori,
            "total_masuk": total_masuk,
            "total_keluar": total_keluar,
            "laba": total_masuk - total_keluar,
        }


_client = None
_client_lock = threading.Lock()


def get_sheets_client() -> "SheetsClient":
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = SheetsClient()
    return _client
