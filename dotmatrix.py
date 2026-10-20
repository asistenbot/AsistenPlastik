"""
Invoice & Surat Jalan versi DOT MATRIX (Epson LX-300, kertas 8,5 x 5,5 inch).

Dua keluaran per dokumen:
  1. File teks polos (80 kolom x 31 baris per halaman, garis tabel pakai
     karakter kotak) -- ini yang di-print.
  2. Gambar preview (simulasi hasil cetak NLQ) -- buat diliat di chat.

Dokumen yang banyak barangnya otomatis lanjut ke halaman berikutnya.
Tiap fungsi generate_*_dotmatrix balikin (list_gambar_png, buffer_teks).
"""

import io
import os
import textwrap

from PIL import Image, ImageDraw, ImageFont

import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_PATH = os.path.join(BASE_DIR, "fonts", "DejaVuSansMono.ttf")

COLS = 80            # kolom per baris (10 cpi x 8 inch)
INNER = COLS - 2     # isi di dalam bingkai
PAGE_LINES = 31      # 5,5 inch x 6 baris/inch = 33, sisain 2 baris buat margin atas/bawah

# ---- ukuran gambar preview (360 dpi, kertas 8,5 x 5,5 inch) ----
CW, LH = 36, 60
PW, PH = int(8.5 * 360), int(5.5 * 360)
MX, MY = int(0.25 * 360), int(0.2 * 360)
GX, GY = 12, 18
RAD = 1.8
PX, PY = CW / (GX + 1), (LH - 12) / GY
BOX = {'─': 'lr', '│': 'ud', '┌': 'rd', '┐': 'ld', '└': 'ur', '┘': 'ul',
       '├': 'udr', '┤': 'udl', '┬': 'lrd', '┴': 'lru', '┼': 'udlr'}
_FONTS = {}


def _font(m):
    if m not in _FONTS:
        _FONTS[m] = ImageFont.truetype(FONT_PATH, int(GY * m * 3.8))
    return _FONTS[m]


# --------------------------------------------------------------- helper teks
def _num(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "0"
    return f"{int(round(v)):,}".replace(",", ".")


def _qty(q):
    try:
        q = float(q)
    except (TypeError, ValueError):
        return str(q)
    if abs(q - round(q)) < 1e-9:
        return f"{int(round(q)):,}".replace(",", ".")
    s = f"{q:,.2f}".rstrip("0").rstrip(".")
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


_BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
          "September", "Oktober", "November", "Desember"]


def _tgl_label(tanggal=None):
    """'2026-09-28 10:00:00' -> '28 September 2026'; kosong/rusak = hari ini (WIB)."""
    import datetime
    try:
        dt = datetime.datetime.strptime(str(tanggal)[:10], "%Y-%m-%d")
    except ValueError:
        dt = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    return f"{dt.day} {_BULAN[dt.month]} {dt.year}"


def _wrap(s, n):
    return textwrap.wrap(str(s or ""), n) or [""]


def _cell(text, w, al):
    text = str(text)
    if al == "l":
        return text.ljust(w)[:w]
    if al == "r":
        return text.rjust(w)[-w:]
    return text.center(w)[:w]


def _row(cells, widths, aligns):
    """Satu baris tabel tanpa garis kotak: kolom dipisah 1 spasi (total 80 kolom)."""
    return " ".join(_cell(c, w, a) for c, w, a in zip(cells, widths, aligns))


def _hl(ch="-"):
    return ch * COLS


# ------------------------------------------------------------ susun halaman
def _party_lines(nama, no_hp, alamat, metode, no_po, tgl_kirim):
    out = []
    nl = _wrap(nama, 70)
    out.append("Kepada : " + nl[0])
    for extra in nl[1:]:
        out.append("         " + extra)
    out.append("HP     : " + str(no_hp or "-"))
    al = _wrap(alamat or "-", 70)
    out.append("Alamat : " + al[0])
    for extra in al[1:3]:
        out.append("         " + extra)
    m = "Metode : " + str(metode or "-")
    if tgl_kirim:
        m = m.ljust(34) + "Tgl Kirim : " + str(tgl_kirim)
    out.append(m)
    if no_po:
        out.append("No. PO : " + str(no_po)[:66])
    return out


def _build(doc_title, no_dok, ref_line, party, widths, aligns, head, item_groups,
           footer_fn, footer_len):
    """Balikin list halaman. Tiap halaman = (baris_png, baris_txt, judul_besar).
    baris_png: judul besar dikosongin (digambar terpisah, dobel ukuran);
    baris_txt: judul ditulis biasa di baris pertama. Tanpa kotak/bingkai --
    cuma garis pemisah horizontal, isinya full 80 kolom."""
    header_len = 3 + 1 + len(party) + 3      # judul(3) + garis + pihak + garis/kepala/garis tabel
    last_cap = PAGE_LINES - header_len - footer_len
    mid_cap = PAGE_LINES - header_len - 2    # garis tutup + "bersambung"

    groups = [g for g in item_groups]
    pages_items = []
    while True:
        total = sum(len(g) for g in groups)
        if total <= last_cap:
            pages_items.append(groups)
            break
        take, used = [], 0
        while groups and used + len(groups[0]) <= mid_cap:
            used += len(groups[0])
            take.append(groups.pop(0))
        if not take:                         # 1 barang kepanjangan -> paksa
            take.append(groups.pop(0))
        pages_items.append(take)
    n_pages = len(pages_items)

    pages = []
    for pi, gs in enumerate(pages_items):
        last = pi == n_pages - 1
        hal = f"Hal {pi + 1}/{n_pages}" if n_pages > 1 else ""
        name = config.BUSINESS_NAME.upper()

        def build(variant):
            title_txt = doc_title if variant == "txt" else ""
            L = [name.ljust(COLS - len(title_txt)) + title_txt,
                 "No  : " + no_dok,
                 ref_line.ljust(COLS - len(hal)) + hal,
                 _hl("=")]
            L.extend(party)
            L.append(_hl("-"))
            L.append(_row(head, widths, ["c"] * len(widths)))
            L.append(_hl("-"))
            for g in gs:
                L.extend(g)
            if last:
                L.extend(footer_fn(widths, 0))
            else:
                L.append(_hl("-"))
                L.append("... bersambung ke halaman berikutnya")
            return L

        pages.append((build("png"), build("txt"), doc_title))
    return pages


def _item_groups(items, widths, aligns, name_w, kind):
    groups = []
    for i, it in enumerate(items, 1):
        lines = _wrap(it.get("nama_item", ""), name_w)
        g = []
        for j, ln in enumerate(lines):
            first = j == 0
            if kind == "invoice":
                try:
                    sub = float(it.get("qty", 0) or 0) * float(it.get("harga_satuan", 0) or 0)
                except (TypeError, ValueError):
                    sub = 0
                cells = [str(i) if first else "", ln,
                         _qty(it.get("qty", "")) if first else "",
                         it.get("satuan", "") if first else "",
                         _num(it.get("harga_satuan", 0)) if first else "",
                         _num(sub) if first else ""]
            else:
                cells = [str(i) if first else "", ln,
                         _qty(it.get("qty", "")) if first else "",
                         it.get("satuan", "") if first else "",
                         "[  ]" if first else ""]
            g.append(_row(cells, widths, aligns))
        groups.append(g)
    return groups


# ---------------------------------------------------------------- gambar
class _Page:
    def __init__(self):
        pad = 60
        self.pad = pad
        self.img = Image.new("RGB", (PW + 2 * pad, PH + 2 * pad), (196, 200, 204))
        self.d = ImageDraw.Draw(self.img)
        self.d.rectangle([pad + 8, pad + 10, pad + PW + 8, pad + PH + 10], fill=(170, 174, 178))
        self.d.rectangle([pad, pad, pad + PW, pad + PH], fill=(252, 251, 247))

    def dot(self, x, y):
        self.d.ellipse([x - RAD, y - RAD, x + RAD, y + RAD], fill=(38, 40, 52))

    def glyph(self, ch, col, line, m=1, bold=False):
        ox = self.pad + MX + col * CW
        oy = self.pad + MY + line * LH
        if ch in BOX:
            fl = BOX[ch]
            cx, cy = ox + CW / 2, oy + 30

            def seg(x0, y0, x1, y1):
                n = max(1, int(max(abs(x1 - x0), abs(y1 - y0)) / 2.6))
                for i in range(n + 1):
                    self.dot(x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n)
            if 'l' in fl: seg(ox, cy, cx, cy)
            if 'r' in fl: seg(cx, cy, ox + CW, cy)
            if 'u' in fl: seg(cx, oy, cx, cy)
            if 'd' in fl: seg(cx, cy, cx, oy + LH)
            return
        if ch == " ":
            return
        gx, gy = GX * m, GY * m
        mk = Image.new("L", (gx * 4, gy * 4), 0)
        ImageDraw.Draw(mk).text((gx * 2, gy * 3.1), ch, font=_font(m), fill=255, anchor="ms")
        mk = mk.resize((gx, gy), Image.BOX)
        for r in range(gy):
            for c in range(gx):
                if mk.getpixel((c, r)) > 80:
                    x = ox + (c + 0.5) * PX + PX * 0.5
                    y = oy + 6 + (r + 0.5) * PY
                    self.dot(x, y)
                    if bold:
                        self.dot(x + 2.2, y)

    def text(self, col, line, s, m=1, bold=False):
        for i, ch in enumerate(s):
            self.glyph(ch, col + i * m, line, m, bold)

    def png(self):
        im = self.img.resize((self.img.width // 2, self.img.height // 2), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        buf.seek(0)
        return buf


def _render(lines, title):
    p = _Page()
    for li, s in enumerate(lines):
        bold_line = li == 0
        for ci, ch in enumerate(s):
            p.glyph(ch, ci, li, 1, bold_line)
    # judul besar (2x lebar & tinggi) di kanan atas
    col = COLS - 2 * len(title)
    p.text(col, 0, title, 2, True)
    return p.png()


def _finish(pages):
    pngs = [_render(png_lines, title) for png_lines, _, title in pages]
    txt = "\r\n\f".join("\r\n".join(l.rstrip() for l in txt_lines) for _, txt_lines, _ in pages) + "\r\n"
    return pngs, io.BytesIO(txt.encode("utf-8"))


# ------------------------------------------------------------ public API
def generate_invoice_dotmatrix(no_invoice, nama_customer, no_hp, alamat, metode, items,
                               ongkir=0, no_po_customer="", tanggal_kirim="", tanggal=None):
    widths = [3, 33, 8, 6, 11, 14]            # + 5 spasi = 80 kolom
    aligns = ["c", "l", "r", "l", "r", "r"]
    head = ["NO", "NAMA BARANG", "QTY", "SAT", "HARGA(Rp)", "SUBTOTAL(Rp)"]
    sub = 0.0
    for it in items:
        try:
            sub += float(it.get("qty", 0) or 0) * float(it.get("harga_satuan", 0) or 0)
        except (TypeError, ValueError):
            pass
    try:
        ongkir = float(ongkir or 0)
    except (TypeError, ValueError):
        ongkir = 0.0
    groups = _item_groups(items, widths, aligns, widths[1], "invoice")

    def footer(widths_, _n):
        def tot(label, val):
            return (f"{label:<9}: " + ("Rp " + _num(val)).rjust(15)).rjust(COLS)
        return [_hl("-"),
                tot("Subtotal", sub), tot("Ongkir", ongkir), tot("TOTAL", sub + ongkir),
                _hl("="),
                f"Transfer : {config.BANK_NAME} {config.BANK_ACCOUNT_NUMBER} a.n. {config.BANK_ACCOUNT_NAME}",
                "Terima kasih atas kepercayaan Anda."]

    party = _party_lines(nama_customer, no_hp, alamat, metode, no_po_customer, tanggal_kirim)
    pages = _build("INVOICE", no_invoice, "Tgl : " + _tgl_label(tanggal),
                   party, widths, aligns, head, groups, footer, 7)
    return _finish(pages)


def generate_surat_jalan_dotmatrix(no_surat_jalan, nama_customer, no_hp, alamat, metode, items,
                                   no_invoice_ref=None, no_po_customer="", tanggal_kirim="", tanggal=None):
    widths = [3, 53, 9, 7, 4]                 # + 4 spasi = 80 kolom
    aligns = ["c", "l", "r", "l", "c"]
    head = ["NO", "NAMA BARANG", "QTY", "SAT", "CEK"]
    groups = _item_groups(items, widths, aligns, widths[1], "sj")
    n_items = len(items)

    def footer(widths_, _n):
        return [_hl("-"),
                f"Total jenis barang : {n_items}",
                "Mohon periksa jumlah dan kondisi barang saat diterima.",
                "Dikirim oleh,".ljust(22) + " " * 34 + "Diterima oleh,".ljust(24),
                "", "",
                "(____________________)".ljust(22) + " " * 34 + "(____________________)"]

    tgl = _tgl_label(tanggal)
    ref = (f"Ref : {no_invoice_ref}   " if no_invoice_ref else "") + f"Tgl : {tgl}"
    party = _party_lines(nama_customer, no_hp, alamat, metode, no_po_customer, tanggal_kirim)
    pages = _build("SURAT JALAN", no_surat_jalan, ref, party, widths, aligns, head,
                   groups, footer, 7)
    return _finish(pages)
