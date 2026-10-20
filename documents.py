"""
Generate Invoice, Surat Jalan, dan Purchase Order sebagai GAMBAR (PNG, buat
preview cepet & gampang di-forward lewat chat) SEKALIGUS PDF (buat di-print
rapi di kertas A4). Tiap fungsi generate_*_image balikin tuple
(png_buffer, pdf_buffer).

Semua dokumen digambar 2x lebih gede (supersampling) biar teksnya tajam di
layar HP maupun pas di-print. Koordinat di kode ini pakai satuan "logis"
(lebar dokumen = 1000), _Canvas yang ngurus ngalikan ke ukuran pixel asli.
"""

import io
import os
import datetime

from PIL import Image, ImageDraw, ImageFont

import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")

WIDTH = 1000          # lebar dokumen (satuan logis)
MARGIN = 50
INNER = WIDTH - 2 * MARGIN
SCALE = 2             # supersampling

INK = (28, 33, 31)
BODY = (72, 82, 77)
MUTED = (118, 128, 122)
ACCENT = (15, 123, 108)
ACCENT_SOFT = (232, 243, 240)
LINE = (214, 220, 216)
LINE_STRONG = (176, 188, 181)
BG = (255, 255, 255)
SOFT_BG = (242, 246, 243)
ZEBRA = (248, 250, 248)
WHITE = (255, 255, 255)

_FONT_FILES = {"reg": "DejaVuSans.ttf", "bold": "DejaVuSans-Bold.ttf"}
_FONT_CACHE = {}


def _font(kind, size):
    key = (kind, size)
    if key not in _FONT_CACHE:
        path = os.path.join(FONT_DIR, _FONT_FILES[kind])
        _FONT_CACHE[key] = ImageFont.truetype(path, int(round(size * SCALE)))
    return _FONT_CACHE[key]


def _tw(text, kind, size):
    """Lebar teks (satuan logis) -- gak butuh canvas, jadi bisa dipake buat
    pra-hitung wrap sebelum gambar dibuat."""
    return _font(kind, size).getlength(str(text)) / SCALE


def rupiah(n):
    try:
        n = int(round(float(n)))
    except (TypeError, ValueError):
        n = 0
    return "Rp" + f"{n:,}".replace(",", ".")


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _fmt_qty(q):
    """5000 -> '5.000', 12.5 -> '12,5' (format angka Indonesia)."""
    q = _to_float(q)
    if abs(q - round(q)) < 1e-9:
        return f"{int(round(q)):,}".replace(",", ".")
    s = f"{q:,.2f}".rstrip("0").rstrip(".")
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def _wrap(text, kind, size, max_width):
    """Wrap teks per kata; kata yang lebih panjang dari kolom dipotong paksa
    per karakter biar gak pernah nabrak kolom sebelah."""
    words = str(text).split()
    lines, current = [], ""

    def flush():
        nonlocal current
        if current:
            lines.append(current)
            current = ""

    for w in words:
        if _tw(w, kind, size) > max_width:
            flush()
            chunk = ""
            for ch in w:
                if _tw(chunk + ch, kind, size) <= max_width:
                    chunk += ch
                else:
                    lines.append(chunk)
                    chunk = ch
            current = chunk
            continue
        trial = f"{current} {w}".strip()
        if _tw(trial, kind, size) <= max_width:
            current = trial
        else:
            flush()
            current = w
    flush()
    return lines or [""]


def _now_tanggal():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    hari = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"][now.weekday()]
    bulan = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
             "Agustus", "September", "Oktober", "November", "Desember"][now.month]
    return f"{hari}, {now.day} {bulan} {now.year}"


class _Canvas:
    """Pembungkus ImageDraw yang kerja di satuan logis (x SCALE otomatis)."""

    def __init__(self, height):
        self.img = Image.new("RGB", (WIDTH * SCALE, int(height * SCALE)), BG)
        self.d = ImageDraw.Draw(self.img)

    def text(self, x, y_mid, s, kind="reg", size=15, fill=INK, align="l"):
        anchor = {"l": "lm", "r": "rm", "c": "mm"}[align]
        self.d.text((x * SCALE, y_mid * SCALE), str(s), font=_font(kind, size), fill=fill, anchor=anchor)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, radius=0, width=1):
        box = [x0 * SCALE, y0 * SCALE, x1 * SCALE, y1 * SCALE]
        w = max(1, int(round(width * SCALE)))
        if radius:
            self.d.rounded_rectangle(box, radius=int(round(radius * SCALE)), fill=fill, outline=outline, width=w)
        else:
            self.d.rectangle(box, fill=fill, outline=outline, width=w)

    def line(self, x0, y0, x1, y1, fill=LINE, width=1):
        self.d.line([(x0 * SCALE, y0 * SCALE), (x1 * SCALE, y1 * SCALE)], fill=fill, width=int(width * SCALE))

    def finish(self, bottom):
        return self.img.crop((0, 0, WIDTH * SCALE, int(bottom * SCALE)))


# ---------------------------------------------------------------- bagian2

_LOGO_CACHE = {}


def _logo():
    if "img" not in _LOGO_CACHE:
        try:
            _LOGO_CACHE["img"] = Image.open(os.path.join(BASE_DIR, "logo_doc.png")).convert("RGB")
        except Exception:
            _LOGO_CACHE["img"] = None
    return _LOGO_CACHE["img"]


def _header(cv, doc_title, doc_number, tanggal):
    cv.rect(0, 0, WIDTH, 12, fill=ACCENT)
    logo = _logo()
    title_x = MARGIN
    if logo is not None:
        lh = 92
        lw = int(round(logo.width * lh / logo.height))
        cv.img.paste(logo.resize((lw * SCALE, lh * SCALE), Image.LANCZOS), (MARGIN * SCALE, 30 * SCALE))
        title_x = MARGIN + lw + 28
        cv.line(title_x - 14, 38, title_x - 14, 118, LINE_STRONG, 1.5)
    cv.text(title_x, 66, doc_title, "bold", 34 if logo is not None else 38, ACCENT)
    cv.rect(title_x, 98, title_x + 64, 102, fill=ACCENT)
    right = WIDTH - MARGIN
    cv.text(right, 48, "NO. DOKUMEN", "bold", 11.5, MUTED, "r")
    cv.text(right, 70, doc_number, "bold", 20, INK, "r")
    cv.text(right, 98, "TANGGAL", "bold", 11.5, MUTED, "r")
    cv.text(right, 118, tanggal, "reg", 15, BODY, "r")
    cv.line(MARGIN, 142, WIDTH - MARGIN, 142, LINE, 1.5)
    return 168


def _party_block(cv, y, label, nama, no_hp, alamat, max_w=500):
    """Blok nama + HP + alamat di kiri. Balikin y paling bawah blok."""
    cv.text(MARGIN, y, label, "bold", 12, MUTED)
    y += 28
    for line in _wrap(nama, "bold", 22, max_w):
        cv.text(MARGIN, y, line, "bold", 22, INK)
        y += 28
    y += 2
    if no_hp:
        cv.text(MARGIN, y, f"HP: {no_hp}", "reg", 15, BODY)
        y += 23
    if alamat:
        for line in _wrap(alamat, "reg", 15, max_w):
            cv.text(MARGIN, y, line, "reg", 15, BODY)
            y += 23
    return y


def _meta_box(cv, y, rows, width=360):
    """Kotak info di kanan (Metode, No. PO Customer, dll). rows = list of
    (label, value, highlight). Balikin y paling bawah kotak."""
    if not rows:
        return y
    pad = 18
    inner_w = width - 2 * pad
    laid = []
    total_h = 2 * pad
    for label, value, hi in rows:
        kind = "bold" if hi else "reg"
        lw = _tw(label, "reg", 13)
        vw = _tw(value, kind, 15)
        if lw + vw + 16 <= inner_w:
            laid.append((label, [value], False, hi))
            total_h += 30
        else:
            vlines = _wrap(value, kind, 15, inner_w)
            laid.append((label, vlines, True, hi))
            total_h += 22 + len(vlines) * 22 + 8
    x0 = WIDTH - MARGIN - width
    cv.rect(x0, y, WIDTH - MARGIN, y + total_h, fill=SOFT_BG, radius=10)
    cy = y + pad
    for label, vlines, stacked, hi in laid:
        kind = "bold" if hi else "reg"
        color = ACCENT if hi else INK
        if not stacked:
            cv.text(x0 + pad, cy + 15, label, "reg", 13, MUTED)
            cv.text(WIDTH - MARGIN - pad, cy + 15, vlines[0], kind, 15, color, "r")
            cy += 30
        else:
            cv.text(x0 + pad, cy + 11, label, "reg", 13, MUTED)
            cy += 22
            for vl in vlines:
                cv.text(x0 + pad, cy + 11, vl, kind, 15, color)
                cy += 22
            cy += 8
    return y + total_h


def _table(cv, y, columns, rows_data, item_idx, item_font=17, line_h=24, min_h=46):
    """Gambar tabel item.
    columns: list of dict {label, w, align ('l','r','c'), key}
    rows_data: list of dict (nilai per key kolom; kolom 'no' otomatis)
    Kolom item (index item_idx) di-wrap otomatis. Balikin y bawah tabel."""
    # header tabel
    cv.rect(MARGIN, y, WIDTH - MARGIN, y + 40, fill=ACCENT, radius=6)
    x = MARGIN
    for col in columns:
        _cell_text(cv, x, col, y + 20, col["label"], "bold", 12.5, WHITE, header=True)
        x += col["w"]
    y += 40

    item_col = columns[item_idx]
    item_w = item_col["w"] - 26
    for i, row in enumerate(rows_data):
        lines = _wrap(row.get(item_col["key"], ""), "reg", item_font, item_w)
        h = max(min_h, 2 * 12 + len(lines) * line_h)
        if i % 2 == 1:
            cv.rect(MARGIN, y, WIDTH - MARGIN, y + h, fill=ZEBRA)
        first_mid = y + 12 + line_h / 2
        x = MARGIN
        for col in columns:
            if col["key"] == "no":
                _cell_text(cv, x, col, first_mid, str(i + 1), "reg", 15, MUTED)
            elif col["key"] == "cek":
                bx = x + col["w"] / 2
                cv.rect(bx - 10, first_mid - 10, bx + 10, first_mid + 10, outline=LINE_STRONG, radius=3, width=1.5)
            elif col is item_col:
                for j, ln in enumerate(lines):
                    cv.text(x + 14, first_mid + j * line_h, ln, "reg", item_font, INK)
            else:
                _cell_text(cv, x, col, first_mid, row.get(col["key"], ""), "reg", 16, INK)
            x += col["w"]
        y += h
        cv.line(MARGIN, y, WIDTH - MARGIN, y, LINE, 1)
    cv.line(MARGIN, y, WIDTH - MARGIN, y, LINE_STRONG, 2)
    return y


def _cell_text(cv, x, col, y_mid, s, kind, size, fill, header=False):
    align = col["align"]
    if align == "r":
        cv.text(x + col["w"] - (14 if col.get("edge") else 8), y_mid, s, kind, size, fill, "r")
    elif align == "c":
        cv.text(x + col["w"] / 2, y_mid, s, kind, size, fill, "c")
    else:
        cv.text(x + (14 if col.get("pad14") else 10), y_mid, s, kind, size, fill, "l")


def _total_block(cv, y, lines, grand_label, grand_value, width=340):
    """Blok total di kanan: baris biasa (label, nilai) + batang TOTAL."""
    x0 = WIDTH - MARGIN - width
    x1 = WIDTH - MARGIN
    for label, val in lines:
        cv.text(x0 + 18, y + 14, label, "reg", 15, BODY)
        cv.text(x1 - 18, y + 14, val, "reg", 15, INK, "r")
        y += 32
    y += 6
    cv.rect(x0, y, x1, y + 50, fill=ACCENT, radius=8)
    cv.text(x0 + 18, y + 25, grand_label, "bold", 16, WHITE)
    cv.text(x1 - 18, y + 25, grand_value, "bold", 22, WHITE, "r")
    return y + 50


def _bank_box(cv, y, width=470):
    cv.rect(MARGIN, y, MARGIN + width, y + 118, fill=ACCENT_SOFT, radius=10)
    cv.text(MARGIN + 20, y + 26, "PEMBAYARAN VIA TRANSFER", "bold", 11.5, ACCENT)
    cv.text(MARGIN + 20, y + 54, config.BANK_NAME, "bold", 17, INK)
    cv.text(MARGIN + 20, y + 84, config.BANK_ACCOUNT_NUMBER, "bold", 24, INK)
    cv.text(MARGIN + 20 + _tw(config.BANK_ACCOUNT_NUMBER, "bold", 24) + 14, y + 86,
            f"a.n. {config.BANK_ACCOUNT_NAME}", "reg", 15, BODY)
    return y + 118


def _footer(cv, y, text):
    cv.line(MARGIN, y, WIDTH - MARGIN, y, LINE, 1)
    cv.text(WIDTH / 2, y + 26, text, "reg", 13.5, MUTED, "c")
    return y + 26 + 24


def _to_pdf(img):
    """Taruh dokumen di kertas A4 (150 dpi) dengan margin wajar. Kalau
    dokumennya kepanjangan buat 1 halaman A4 (banyak item), halamannya
    diperpanjang ngikutin dokumen -- gak diperkecil sampai susah dibaca."""
    dpi = 150
    page_w, page_h = int(8.27 * dpi), int(11.69 * dpi)
    pad = 48
    target_w = page_w - 2 * pad
    ratio = target_w / img.width
    doc = img.resize((target_w, max(1, int(img.height * ratio))), Image.Resampling.LANCZOS)
    height = max(page_h, doc.height + 2 * pad)
    page = Image.new("RGB", (page_w, height), BG)
    page.paste(doc, (pad, pad))
    buf = io.BytesIO()
    page.save(buf, format="PDF", resolution=dpi)
    buf.seek(0)
    return buf


def _output(cv, bottom):
    img = cv.finish(bottom)
    png_buf = io.BytesIO()
    img.save(png_buf, format="PNG", optimize=True)
    png_buf.seek(0)
    return png_buf, _to_pdf(img)


def _canvas_for(rows_n, extra=0):
    # tinggi awal dibikin lega, hasil akhirnya di-crop pas ke isi dokumen
    return _Canvas(1500 + rows_n * 120 + extra)


# ---------------------------------------------------------------- dokumen

def generate_invoice_image(no_invoice, nama_customer, no_hp, alamat, metode, items, ongkir=0,
                            no_po_customer="", tanggal_kirim=""):
    """items: list of dict {nama_item, qty, satuan, harga_satuan}.
    no_po_customer/tanggal_kirim opsional -- ditampilin kalau ada."""
    cv = _canvas_for(len(items), extra=len(alamat or "") * 2)
    y = _header(cv, "INVOICE", no_invoice, _now_tanggal())

    left_end = _party_block(cv, y, "DITAGIHKAN KEPADA", nama_customer, no_hp, alamat)
    meta = [("Metode", metode or "-", False)]
    if no_po_customer:
        meta.append(("No. PO Customer", no_po_customer, False))
    if tanggal_kirim:
        meta.append(("Tanggal Kirim", tanggal_kirim, True))
    right_end = _meta_box(cv, y - 6, meta)
    y = max(left_end, right_end) + 26

    columns = [
        {"label": "NO", "w": 44, "align": "c", "key": "no"},
        {"label": "ITEM", "w": 392, "align": "l", "key": "nama_item", "pad14": True},
        {"label": "QTY", "w": 80, "align": "r", "key": "qty"},
        {"label": "SATUAN", "w": 70, "align": "l", "key": "satuan"},
        {"label": "HARGA", "w": 130, "align": "r", "key": "harga"},
        {"label": "SUBTOTAL", "w": 184, "align": "r", "key": "subtotal", "edge": True},
    ]
    rows, total = [], 0.0
    for it in items:
        qty = _to_float(it.get("qty"))
        harga = _to_float(it.get("harga_satuan"))
        total += qty * harga
        rows.append({
            "nama_item": it.get("nama_item", ""), "qty": _fmt_qty(qty), "satuan": it.get("satuan", ""),
            "harga": rupiah(harga), "subtotal": rupiah(qty * harga),
        })
    y = _table(cv, y, columns, rows, item_idx=1)

    y += 26
    ongkir_f = _to_float(ongkir)
    bank_end = _bank_box(cv, y)
    totals_end = _total_block(
        cv, y, [("Subtotal", rupiah(total)), ("Ongkir", rupiah(ongkir_f))],
        "TOTAL", rupiah(total + ongkir_f),
    )
    y = max(bank_end, totals_end) + 34
    y = _footer(cv, y, "Terima kasih atas kepercayaan Anda.")
    return _output(cv, y + 10)


def generate_surat_jalan_image(no_surat_jalan, nama_customer, no_hp, alamat, metode, items,
                                no_invoice_ref=None, no_po_customer="", tanggal_kirim=""):
    """items: list of dict {nama_item, qty, satuan} -- TANPA harga, buat kurir.
    no_po_customer/tanggal_kirim opsional -- ditampilin kalau ada."""
    cv = _canvas_for(len(items), extra=len(alamat or "") * 2)
    y = _header(cv, "SURAT JALAN", no_surat_jalan, _now_tanggal())

    left_end = _party_block(cv, y, "KEPADA", nama_customer, no_hp, alamat)
    meta = [("Metode", metode or "-", False)]
    if no_invoice_ref:
        meta.append(("Ref. Invoice", no_invoice_ref, False))
    if no_po_customer:
        meta.append(("Ref. PO Customer", no_po_customer, False))
    if tanggal_kirim:
        meta.append(("Tanggal Kirim", tanggal_kirim, True))
    right_end = _meta_box(cv, y - 6, meta)
    y = max(left_end, right_end) + 26

    columns = [
        {"label": "NO", "w": 44, "align": "c", "key": "no"},
        {"label": "ITEM", "w": 576, "align": "l", "key": "nama_item", "pad14": True},
        {"label": "QTY", "w": 110, "align": "r", "key": "qty"},
        {"label": "SATUAN", "w": 90, "align": "l", "key": "satuan"},
        {"label": "CEK", "w": 80, "align": "c", "key": "cek"},
    ]
    rows = [{
        "nama_item": it.get("nama_item", ""), "qty": _fmt_qty(it.get("qty")), "satuan": it.get("satuan", ""),
    } for it in items]
    y = _table(cv, y, columns, rows, item_idx=1, item_font=18, line_h=25, min_h=50)

    y += 24
    cv.text(MARGIN, y + 10, f"Total jenis barang: {len(items)}", "bold", 15, INK)
    cv.text(WIDTH - MARGIN, y + 10, "Mohon periksa jumlah & kondisi barang saat diterima.", "reg", 13.5, MUTED, "r")
    y += 44

    # tanda tangan
    block_w = 360
    left_x0, right_x0 = MARGIN + 20, WIDTH - MARGIN - 20 - block_w
    for x0, title in ((left_x0, "Dikirim oleh,"), (right_x0, "Diterima oleh,")):
        cv.text(x0 + block_w / 2, y + 10, title, "bold", 15, INK, "c")
        line_y = y + 110
        cv.line(x0, line_y, x0 + block_w, line_y, INK, 1.2)
        cv.text(x0 + block_w / 2, line_y + 18, "Nama jelas & tanggal", "reg", 12.5, MUTED, "c")
    y += 110 + 40
    y = _footer(cv, y, "Terima kasih atas kepercayaan Anda.")
    return _output(cv, y + 10)


def generate_po_image(no_po, nama_supplier, items):
    """items: list of dict {nama_item, qty, satuan, harga_satuan}"""
    cv = _canvas_for(len(items))
    y = _header(cv, "PURCHASE ORDER", no_po, _now_tanggal())

    y = _party_block(cv, y, "KEPADA SUPPLIER", nama_supplier, "", "", max_w=WIDTH - 2 * MARGIN) + 26

    columns = [
        {"label": "NO", "w": 44, "align": "c", "key": "no"},
        {"label": "ITEM", "w": 392, "align": "l", "key": "nama_item", "pad14": True},
        {"label": "QTY", "w": 80, "align": "r", "key": "qty"},
        {"label": "SATUAN", "w": 70, "align": "l", "key": "satuan"},
        {"label": "HARGA", "w": 130, "align": "r", "key": "harga"},
        {"label": "SUBTOTAL", "w": 184, "align": "r", "key": "subtotal", "edge": True},
    ]
    rows, total = [], 0.0
    for it in items:
        qty = _to_float(it.get("qty"))
        harga = _to_float(it.get("harga_satuan"))
        total += qty * harga
        rows.append({
            "nama_item": it.get("nama_item", ""), "qty": _fmt_qty(qty), "satuan": it.get("satuan", ""),
            "harga": rupiah(harga), "subtotal": rupiah(qty * harga),
        })
    y = _table(cv, y, columns, rows, item_idx=1)

    y += 26
    y = _total_block(cv, y, [], "TOTAL", rupiah(total)) + 34
    y = _footer(cv, y, "Mohon konfirmasi ketersediaan barang. Terima kasih.")
    return _output(cv, y + 10)


def generate_konfirmasi_pesanan(no_invoice, nama_customer, no_hp, alamat, items, ongkir=0,
                                tanggal_kirim="", no_po_customer="", catatan=""):
    """Dokumen 'Konfirmasi Pesanan' (berwarna, PDF) buat dicetak & dikasih ke
    customer setelah order online masuk."""
    cv = _canvas_for(len(items), extra=60)
    y = _header(cv, "KONFIRMASI PESANAN", no_invoice, _now_tanggal())
    y = _party_block(cv, y, "PEMESAN", nama_customer, no_hp, alamat, max_w=WIDTH - 2 * MARGIN) + 20
    for label, val in (("Tanggal Kirim", tanggal_kirim), ("No. PO Customer", no_po_customer)):
        if val:
            cv.text(MARGIN, y + 10, f"{label}: {val}", "bold", 15, INK)
            y += 30
    y += 6
    columns = [
        {"label": "NO", "w": 44, "align": "c", "key": "no"},
        {"label": "ITEM", "w": 392, "align": "l", "key": "nama_item", "pad14": True},
        {"label": "QTY", "w": 80, "align": "r", "key": "qty"},
        {"label": "SATUAN", "w": 70, "align": "l", "key": "satuan"},
        {"label": "HARGA", "w": 130, "align": "r", "key": "harga"},
        {"label": "SUBTOTAL", "w": 184, "align": "r", "key": "subtotal", "edge": True},
    ]
    rows, total = [], 0.0
    for it in items:
        qty = _to_float(it.get("qty"))
        harga = _to_float(it.get("harga_satuan"))
        total += qty * harga
        rows.append({"nama_item": it.get("nama_item", ""), "qty": _fmt_qty(qty), "satuan": it.get("satuan", ""),
                     "harga": rupiah(harga), "subtotal": rupiah(qty * harga)})
    y = _table(cv, y, columns, rows, item_idx=1) + 26
    lines = []
    if ongkir:
        lines.append(("Subtotal", rupiah(total)))
        lines.append(("Ongkir", rupiah(_to_float(ongkir))))
    y = _total_block(cv, y, lines, "TOTAL", rupiah(total + _to_float(ongkir))) + 30
    if catatan:
        for ln in _wrap("Catatan: " + str(catatan), "reg", 14, WIDTH - 2 * MARGIN)[:3]:
            cv.text(MARGIN, y, ln, "reg", 14, BODY)
            y += 22
        y += 10
    y = _footer(cv, y, "Mohon konfirmasi pesanan ini via WhatsApp. Terima kasih.")
    return _output(cv, y + 10)
