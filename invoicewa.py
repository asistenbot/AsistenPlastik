"""Invoice versi WhatsApp: gambar PNG yang rapi & enak dilihat di HP
(beda dari invoice dot matrix yang buat diprint)."""

import datetime
import io
import os

from PIL import Image, ImageDraw, ImageFont

import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(BASE_DIR, "fonts")
S = 2                      # supersampling (lebar akhir 1600px)
W = 800                    # lebar logis

BG = (243, 245, 249)
CARD = (255, 255, 255)
INK = (26, 34, 51)
MUTED = (107, 116, 136)
LINE = (230, 233, 240)
BLUE = (67, 97, 238)
BLUE_SOFT = (238, 241, 254)
GREEN, GREEN_BG = (21, 128, 61), (231, 247, 236)
AMBER, AMBER_BG = (146, 64, 14), (254, 243, 199)
NOTE_BG = (255, 248, 225)

BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
         "September", "Oktober", "November", "Desember"]
_FC = {}


def _f(w, size):
    key = (w, size)
    if key not in _FC:
        nama = {500: "PlusJakartaSans-500.ttf", 700: "PlusJakartaSans-700.ttf", 800: "PlusJakartaSans-800.ttf"}[w]
        try:
            _FC[key] = ImageFont.truetype(os.path.join(FONT_DIR, nama), int(size * S))
        except OSError:
            _FC[key] = ImageFont.truetype(os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf" if w > 500 else "DejaVuSans.ttf"),
                                          int(size * S))
    return _FC[key]


def _num(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return 0.0


def rp(n):
    return "Rp" + f"{round(n):,}".replace(",", ".")


def _qty(q):
    q = _num(q)
    return f"{int(q):,}".replace(",", ".") if q == int(q) else f"{q:g}".replace(".", ",")


def _tgl(s):
    s = str(s or "").strip()
    try:
        d = datetime.datetime.strptime(s[:10], "%Y-%m-%d")
        return f"{d.day} {BULAN[d.month]} {d.year}"
    except ValueError:
        return s


class _C:
    def __init__(self, h):
        self.im = Image.new("RGB", (W * S, h * S), BG)
        self.d = ImageDraw.Draw(self.im)

    def rect(self, x, y, w, h, fill, r=0, outline=None):
        self.d.rounded_rectangle([x * S, y * S, (x + w) * S, (y + h) * S], radius=r * S, fill=fill,
                                 outline=outline, width=S if outline else 0)

    def text(self, x, y, s, w, size, fill, anchor="la"):
        self.d.text((x * S, y * S), s, font=_f(w, size), fill=fill, anchor=anchor)

    def tw(self, s, w, size):
        return self.d.textlength(s, font=_f(w, size)) / S

    def wrap(self, s, w, size, maxw):
        out, cur = [], ""
        for word in str(s or "").split():
            t = (cur + " " + word).strip()
            if self.tw(t, w, size) <= maxw or not cur:
                cur = t
            else:
                out.append(cur)
                cur = word
        if cur:
            out.append(cur)
        return out or [""]


def _layout(c, rows, draw=True):
    """Gambar invoice. Balikin tinggi total (logis). draw=False cuma ngitung."""
    f = rows[0]
    inv = str(f.get("No_Invoice", ""))
    lunas = str(f.get("Status", "")) == "Lunas"
    X, CW = 28, W - 56                  # kartu putih
    P = 36                              # padding dalam kartu
    y = 28
    # ---- header biru ----
    HH = 168
    if draw:
        c.rect(X, y, CW, HH + 30, BLUE, r=26)
        c.rect(X, y + HH, CW, 40, CARD)               # potong lengkung bawah
        # logo
        c.rect(X + P, y + 30, 52, 52, (255, 255, 255), r=14)
        c.text(X + P + 26, y + 56, "AS", 800, 20, BLUE, "mm")
        c.text(X + P + 66, y + 36, config.BUSINESS_NAME, 800, 19, (255, 255, 255))
        c.text(X + P + 66, y + 62, "Invoice penjualan", 500, 14, (210, 219, 255))
        c.text(X + CW - P, y + 34, "INVOICE", 800, 30, (255, 255, 255), "ra")
        c.text(X + P, y + 112, inv, 800, 22, (255, 255, 255))
        c.text(X + P, y + 142, "Tanggal  " + _tgl(f.get("Timestamp", "")), 500, 15, (210, 219, 255))
        pill = "LUNAS" if lunas else "BELUM DIBAYAR"
        pw = c.tw(pill, 800, 13) + 30
        c.rect(X + CW - P - pw, y + 118, pw, 34, GREEN_BG if lunas else AMBER_BG, r=17)
        c.text(X + CW - P - pw / 2, y + 135, pill, 800, 13, GREEN if lunas else AMBER, "mm")
    y += HH
    top_card = y
    y += 30
    # ---- kepada + info ----
    colw = (CW - 2 * P - 24) / 2
    lx, rx = X + P, X + P + colw + 24
    ly = y
    if draw:
        c.text(lx, ly, "Ditagihkan kepada", 700, 13, MUTED)
    ly += 24
    for ln in c.wrap(f.get("Nama_Customer", ""), 800, 20, colw):
        if draw:
            c.text(lx, ly, ln, 800, 20, INK)
        ly += 28
    for val in (f.get("No_HP", ""), f.get("Alamat", "")):
        for ln in (c.wrap(val, 500, 15, colw) if str(val or "").strip() else []):
            if draw:
                c.text(lx, ly, ln, 500, 15, MUTED)
            ly += 22
    info = [("Metode", str(f.get("Metode", "") or "-"))]
    if str(f.get("Tanggal_Kirim", "") or "").strip():
        info.append(("Tanggal kirim", _tgl(f.get("Tanggal_Kirim"))))
    if str(f.get("No_PO_Customer", "") or "").strip():
        info.append(("No. PO", str(f.get("No_PO_Customer"))))
    ry = y
    for k, v in info:
        if draw:
            c.text(rx, ry + 3, k, 500, 14, MUTED)
            c.text(rx + colw, ry, v, 800, 16, INK, "ra")
            c.rect(rx, ry + 32, colw, 1, LINE)
        ry += 44
    y = max(ly, ry) + 18
    # ---- barang ----
    if draw:
        c.rect(X + P - 12, y, CW - 2 * P + 24, 38, BG, r=10)
        c.text(X + P, y + 19, "Barang", 700, 13, MUTED, "lm")
        c.text(X + CW - P, y + 19, "Jumlah", 700, 13, MUTED, "rm")
    y += 50
    sub = 0.0
    namew = CW - 2 * P - 170
    for i, r in enumerate(rows):
        q, h = _num(r.get("Qty")), _num(r.get("Harga_Satuan"))
        st = q * h
        sub += st
        lines = c.wrap(r.get("Nama_Item", ""), 700, 17, namew)
        if draw:
            for k, ln in enumerate(lines):
                c.text(X + P, y + k * 24, ln, 700, 17, INK)
            c.text(X + CW - P, y, rp(st), 800, 17, INK, "ra")
            c.text(X + P, y + len(lines) * 24 + 2, f"{_qty(q)} {r.get('Satuan', '')}  ×  {rp(h)}", 500, 15, MUTED)
        y += len(lines) * 24 + 32
        if i < len(rows) - 1:
            if draw:
                c.rect(X + P, y, CW - 2 * P, 1, LINE)
            y += 16
    y += 10
    # ---- total ----
    ongkir = sum(_num(r.get("Ongkir")) for r in rows)
    if draw:
        c.rect(X + P, y, CW - 2 * P, 1, LINE)
    y += 18
    for k, v in (("Subtotal", sub), ("Ongkir", ongkir)):
        if k == "Ongkir" and not v:
            continue
        if draw:
            c.text(X + CW - P - 200, y, k, 500, 16, MUTED, "ra")
            c.text(X + CW - P, y, rp(v), 700, 16, INK, "ra")
        y += 30
    y += 6
    if draw:
        c.rect(X + P, y, CW - 2 * P, 84, BLUE_SOFT, r=18)
        c.text(X + P + 22, y + 42, "Total tagihan", 700, 17, INK, "lm")
        c.text(X + CW - P - 22, y + 42, rp(sub + ongkir), 800, 30, BLUE, "rm")
    y += 84 + 22
    # ---- catatan ----
    cat = str(f.get("Catatan", "") or "").strip()
    if cat:
        cl = c.wrap(cat, 500, 15, CW - 2 * P - 44)
        hh = 46 + len(cl) * 22
        if draw:
            c.rect(X + P, y, CW - 2 * P, hh, NOTE_BG, r=16)
            c.text(X + P + 22, y + 16, "Catatan", 700, 13, AMBER)
            for k, ln in enumerate(cl):
                c.text(X + P + 22, y + 38 + k * 22, ln, 500, 15, INK)
        y += hh + 18
    # ---- transfer ----
    if not lunas:
        if draw:
            c.rect(X + P, y, CW - 2 * P, 104, CARD, r=18, outline=LINE)
            c.text(X + P + 22, y + 18, "Pembayaran via transfer", 700, 13, MUTED)
            norek = config.BANK_ACCOUNT_NUMBER
            c.text(X + P + 22, y + 42, f"{config.BANK_NAME}  {norek}", 800, 24, INK)
            c.text(X + P + 22, y + 76, "a.n. " + config.BANK_ACCOUNT_NAME, 500, 15, MUTED)
        y += 104 + 18
    # ---- penutup ----
    y += 6
    if draw:
        c.text(W / 2, y, "Terima kasih atas kepercayaan Anda", 700, 15, MUTED, "ma")
    y += 44
    return y, top_card


def generate_invoice_wa(sheets, no_invoice):
    """Balikin (nama_file, bytes PNG) atau None."""
    rows = sheets.get_order_items(no_invoice)
    if not rows:
        return None
    hitung = _C(10)
    tinggi, _ = _layout(hitung, rows, draw=False)
    c = _C(int(tinggi + 28))
    # kartu putih dulu, baru isinya
    c.rect(28, 28, W - 56, tinggi - 28, CARD, r=26)
    _layout(c, rows, draw=True)
    buf = io.BytesIO()
    c.im.save(buf, "PNG", optimize=True)
    return f"{no_invoice}.png", buf.getvalue()
