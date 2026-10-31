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
        "Harga_Jual", "Harga_Beli", "Khusus_Customer", "Supplier", "Isi_Bal", "Stok_Min",
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
                             "Ref", "Status", "Diputuskan_Oleh", "Diputuskan_Waktu"],
    config.SHEET_PENERIMAAN: ["No_PO", "Status", "Batch", "Staff", "Waktu", "Catatan"],
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
_CACHE_TTL = 20  # detik; hemat kuota baca Google Sheets (maks 60 baca/menit)


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
        val = getattr(self._ws, name)(*a, **kw)
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
        """get_all_records, tapi kolom No_HP/Item_Code selalu dipaksa jadi
        teks (lihat _TEXT_ONLY_COLUMNS) biar angka 0 di depan gak ilang."""
        headers = SCHEMA.get(ws.title) or ws.row_values(1)
        ignore = self._numericise_ignore_for(headers)
        return ws.get_all_records(default_blank="", numericise_ignore=ignore)

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

    def add_purchase_order(self, nama_supplier, items):
        """items: list of dict {nama_item, qty, satuan, harga_satuan}.
        Nulis 1 baris per item dgn No_PO yang sama, status Belum Lunas,
        dan otomatis nambah entry 'Utang Baru' ke UtangSupplier.
        Balikin (no_po, total)."""
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
        for r in self._records(self._ws(config.SHEET_UTANG_SUPPLIER)):
            if str(r.get("Nama_Supplier", "")).strip().lower() != nama_supplier.strip().lower():
                continue
            try:
                jumlah = float(r.get("Jumlah", 0) or 0)
            except ValueError:
                jumlah = 0
            if r.get("Jenis") == "Utang Baru":
                total += jumlah
            elif r.get("Jenis") in ("Pembayaran", "Batal PO"):
                total -= jumlah
        return total

    def _add_utang_entry(self, nama_supplier, no_po, jenis, jumlah, catatan=""):
        saldo = self._get_saldo_utang(nama_supplier)
        saldo_baru = saldo + jumlah if jenis == "Utang Baru" else saldo - jumlah
        self._ws(config.SHEET_UTANG_SUPPLIER).append_row(
            [_today_str(), nama_supplier, no_po, jenis, jumlah, saldo_baru, catatan],
            value_input_option="RAW",
        )
        return saldo_baru

    def bayar_utang(self, nama_supplier, jumlah, catatan=""):
        """Catat pembayaran ke supplier. Balikin sisa utang setelah dibayar."""
        with self._lock:
            saldo_baru = self._add_utang_entry(nama_supplier, "", "Pembayaran", jumlah, catatan)
        return saldo_baru

    def get_utang_summary(self):
        """dict nama_supplier -> sisa utang (cuma yang > 0)"""
        names = set()
        for r in self._records(self._ws(config.SHEET_UTANG_SUPPLIER)):
            nama = str(r.get("Nama_Supplier", "")).strip()
            if nama:
                names.add(nama)
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
        out = []
        for r in produk:
            code = str(r["Item_Code"]).strip()
            ms = sorted(by_item.get(code.upper(), []), key=lambda m: str(m.get("Waktu", "")))
            hit = [m for m in ms if m.get("Jenis") == "Hitung"]
            stok, t0 = None, ""
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
                        "isi_bal": self._f(r.get("Isi_Bal")), "min": mn, "stok": stok, "status": status})
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
                 e.get("satuan", ""), ref, "Menunggu", "", ""] for i, e in enumerate(entries)]
        self._ws(config.SHEET_PENGAJUAN).append_rows(rows, value_input_option="RAW")
        return batch

    def get_pengajuan(self, status=None, staff=None):
        rows = self._records(self._ws(config.SHEET_PENGAJUAN))
        if status:
            rows = [r for r in rows if r.get("Status") == status]
        if staff:
            rows = [r for r in rows if str(r.get("Staff", "")) == staff]
        return rows

    def decide_pengajuan(self, batch, approve, oleh="owner"):
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

    def get_penerimaan_map(self):
        """{no_po: baris terakhir yang statusnya BUKAN Ditolak} -> Menunggu / Diterima."""
        out = {}
        for r in self._records(self._ws(config.SHEET_PENERIMAAN)):
            if str(r.get("Status", "")) == "Ditolak":
                continue
            out[str(r.get("No_PO", ""))] = r
        return out

    def get_po_untuk_terima(self, hanya_belum=True, limit=40):
        """PO + item (dicocokin ke PriceList) buat dicek staff gudang."""
        produk = [p for p in self.get_price_list() if str(p.get("Item_Code", "")).strip()]
        terima = self.get_penerimaan_map()
        by = {}
        for r in self._po_terbuka_rows():
            no = str(r["No_PO"]).strip()
            d = by.setdefault(no, {"po": no, "supplier": str(r.get("Nama_Supplier", "")),
                                   "tgl": str(r.get("Timestamp", ""))[:10], "items": []})
            p = self._cocok_produk(r.get("Item", ""), produk)
            try:
                qty = float(r.get("Qty") or 0)
            except (TypeError, ValueError):
                qty = 0.0
            sat = str(r.get("Satuan", "") or "")
            try:
                isi = float((p or {}).get("Isi_Bal") or 0)
            except (TypeError, ValueError):
                isi = 0.0
            unit = "bal" if (p and isi > 0 and sat.strip().lower() == "bal") else "sat"
            d["items"].append({"nama": str(r.get("Item", "")), "qty": qty, "satuan": sat,
                               "kandidat": self._kandidat(r.get("Item", ""), produk, p),
                               "code": str(p["Item_Code"]).strip() if p else "", "unit": unit,
                               "satuan_stok": str((p or {}).get("Satuan", "") or sat)})
        out = []
        for d in sorted(by.values(), key=lambda d: d["po"], reverse=True):
            t = terima.get(d["po"])
            d["status_terima"] = str(t.get("Status", "")) if t else ""
            if hanya_belum and d["status_terima"] == "Diterima":
                continue
            out.append(d)
        return out[:limit]

    def add_penerimaan(self, no_po, batch, staff, catatan=""):
        self._ws(config.SHEET_PENERIMAAN).append_row(
            [no_po, "Menunggu", batch, staff, _now_str(), catatan], value_input_option="RAW")

    def set_penerimaan_status(self, batch, status):
        ws = self._ws(config.SHEET_PENERIMAAN)
        for i, row in enumerate(ws.get_all_values()[1:], start=2):
            if len(row) > 2 and row[2] == batch:
                ws.batch_update([{"range": f"B{i}", "values": [[status]]}])
                return True
        return False

    def po_banding(self, no_po, diterima):
        """Bandingin PO vs yang diterima. diterima: {item_code: qty_satuan_stok}.
        Balikin list {nama, pesan, terima, satuan, selisih} (satuan stok)."""
        produk = [p for p in self.get_price_list() if str(p.get("Item_Code", "")).strip()]
        out, dipakai = [], set()
        for r in self._po_terbuka_rows():
            if str(r["No_PO"]).strip() != no_po:
                continue
            p = self._cocok_produk(r.get("Item", ""), produk)
            try:
                qty = float(r.get("Qty") or 0)
            except (TypeError, ValueError):
                qty = 0.0
            sat = str(r.get("Satuan", "") or "")
            code = str(p["Item_Code"]).strip().upper() if p else ""
            try:
                isi = float((p or {}).get("Isi_Bal") or 0)
            except (TypeError, ValueError):
                isi = 0.0
            if p and isi > 0 and sat.strip().lower() == "bal":
                qty, sat = qty * isi, str(p.get("Satuan", "") or sat)
            got = float(diterima.get(code, 0)) if code else 0.0
            if code:
                dipakai.add(code)
            out.append({"nama": str(r.get("Item", "")), "pesan": qty, "terima": got, "satuan": sat,
                        "selisih": got - qty})
        for code, got in diterima.items():
            if code not in dipakai:
                out.append({"nama": code, "pesan": 0, "terima": got, "satuan": "", "selisih": got})
        return out

    # permintaan barang (staff minta owner order)
    def add_permintaan(self, staff, entries):
        ts = _now_str()
        rows = []
        for e in entries:
            rows.append(["Q" + uuid.uuid4().hex[:6].upper(), ts, staff, e["item_code"], e.get("nama", ""),
                         e["qty"], e.get("satuan", ""), e.get("catatan", ""), "Baru"])
        self._ws(config.SHEET_PERMINTAAN).append_rows(rows, value_input_option="RAW")
        return len(rows)

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
