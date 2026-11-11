"""PDF Surat Tagihan (A4) buat dikirim ke customer: daftar invoice yang udah jatuh tempo."""

import datetime
import io
import os

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import config

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
         "September", "Oktober", "November", "Desember"]

INK = (26 / 255, 34 / 255, 51 / 255)
MUTED = (107 / 255, 116 / 255, 136 / 255)
LINE = (230 / 255, 233 / 255, 240 / 255)
BLUE = (67 / 255, 97 / 255, 238 / 255)
BLUE_SOFT = (238 / 255, 241 / 255, 254 / 255)
ROW = (247 / 255, 248 / 255, 252 / 255)
RED = (190 / 255, 18 / 255, 60 / 255)

_REG = False


def _fonts():
    global _REG
    if _REG:
        return
    for w in (500, 700, 800):
        pdfmetrics.registerFont(TTFont(f"PJS{w}", os.path.join(BASE_DIR, "fonts", f"PlusJakartaSans-{w}.ttf")))
    _REG = True


def rp(n):
    return "Rp" + f"{round(n):,}".replace(",", ".")


def tgl(s):
    try:
        d = datetime.datetime.strptime(str(s)[:10], "%Y-%m-%d")
        return f"{d.day} {BULAN[d.month]} {d.year}"
    except ValueError:
        return str(s or "-")


def tgl_pendek(s):
    try:
        d = datetime.datetime.strptime(str(s)[:10], "%Y-%m-%d")
        return d.strftime("%d-%m-%Y")
    except ValueError:
        return str(s or "-")


def _wrap(c, text, font, size, maxw):
    out, cur = [], ""
    for w in str(text or "").split():
        t = (cur + " " + w).strip()
        if pdfmetrics.stringWidth(t, font, size) <= maxw or not cur:
            cur = t
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def buat_pdf(cust, invoices, today=None):
    """cust: {nama, hp, alamat}; invoices: [{invoice, tgl, kirim, jatuh, total}] -> (nama_file, bytes)."""
    _fonts()
    today = today or (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).strftime("%Y-%m-%d")
    W, H = A4
    M = 46
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    no_surat = f"TG-{today.replace('-', '')}-{''.join(ch for ch in cust['nama'].upper() if ch.isalnum())[:6]}"
    c.setTitle(f"Surat Tagihan {cust['nama']}")

    def fill(rgb):
        c.setFillColorRGB(*rgb)

    def header():
        fill(BLUE)
        c.rect(0, H - 120, W, 120, stroke=0, fill=1)
        fill((1, 1, 1))
        c.roundRect(M, H - 86, 46, 46, 11, stroke=0, fill=1)
        fill(BLUE)
        c.setFont("PJS800", 17)
        c.drawCentredString(M + 23, H - 69, "AS")
        fill((1, 1, 1))
        c.setFont("PJS800", 16)
        c.drawString(M + 60, H - 68, config.BUSINESS_NAME)
        fill((1, 1, 1))
        c.setFont("PJS800", 24)
        c.drawRightString(W - M, H - 66, "SURAT TAGIHAN")
        c.setFont("PJS500", 10)
        c.setFillColorRGB(0.84, 0.87, 1)
        c.drawRightString(W - M, H - 84, f"No. {no_surat}  •  {tgl(today)}")

    header()
    y = H - 160
    # kepada
    fill(MUTED)
    c.setFont("PJS700", 9.5)
    c.drawString(M, y, "Kepada Yth.")
    y -= 18
    fill(INK)
    c.setFont("PJS800", 15)
    c.drawString(M, y, cust["nama"])
    c.setFont("PJS500", 10.5)
    fill(MUTED)
    for v in (cust.get("hp"), cust.get("alamat")):
        if str(v or "").strip():
            for ln in _wrap(c, v, "PJS500", 10.5, W / 2):
                y -= 15
                c.drawString(M, y, ln)
    y -= 28
    fill(INK)
    c.setFont("PJS500", 11)
    for ln in _wrap(c, "Dengan hormat, bersama surat ini kami sampaikan tagihan atas invoice berikut "
                       "yang sudah jatuh tempo pembayaran:", "PJS500", 11, W - 2 * M):
        c.drawString(M, y, ln)
        y -= 16
    y -= 8

    cols = [("No", 26, "l"), ("No. Invoice", 128, "l"), ("Tgl invoice", 86, "l"), ("Tgl dikirim", 86, "l"),
            ("Jatuh tempo", 86, "l"), ("Jumlah", W - 2 * M - 26 - 128 - 86 * 3, "r")]

    def thead(y):
        fill(BLUE_SOFT)
        c.roundRect(M, y - 24, W - 2 * M, 28, 7, stroke=0, fill=1)
        fill(BLUE)
        c.setFont("PJS700", 9.5)
        x = M + 10
        for name, w, al in cols:
            if al == "r":
                c.drawRightString(x + w - 20, y - 14, name)
            else:
                c.drawString(x, y - 14, name)
            x += w
        return y - 34

    y = thead(y)
    total = 0.0
    for i, o in enumerate(invoices, start=1):
        if y < 190:
            c.showPage()
            header()
            y = thead(H - 150)
        if i % 2 == 0:
            fill(ROW)
            c.rect(M, y - 9, W - 2 * M, 24, stroke=0, fill=1)
        vals = [str(i), o["invoice"], tgl_pendek(o.get("tgl")), tgl_pendek(o.get("kirim")) if o.get("kirim") else "-",
                tgl_pendek(o.get("jatuh")) if o.get("jatuh") else "-", rp(o["total"])]
        x = M + 10
        for (name, w, al), v in zip(cols, vals):
            telat = name == "Jatuh tempo" and o.get("jatuh") and o["jatuh"] < today
            fill(RED if telat else INK)
            c.setFont("PJS800" if name in ("Jumlah", "No. Invoice") else "PJS500", 10)
            if al == "r":
                c.drawRightString(x + w - 20, y, v)
            else:
                c.drawString(x, y, v)
            x += w
        total += o["total"]
        y -= 24
    y -= 6
    fill(LINE)
    c.rect(M, y, W - 2 * M, 1, stroke=0, fill=1)
    y -= 50
    # total
    fill(BLUE_SOFT)
    c.roundRect(M, y, W - 2 * M, 46, 10, stroke=0, fill=1)
    fill(INK)
    c.setFont("PJS700", 12)
    c.drawString(M + 18, y + 18, f"Total tagihan ({len(invoices)} invoice)")
    fill(BLUE)
    c.setFont("PJS800", 20)
    c.drawRightString(W - M - 18, y + 15, rp(total))
    y -= 30
    # transfer
    fill(MUTED)
    c.setFont("PJS700", 9.5)
    c.drawString(M, y, "Pembayaran mohon ditransfer ke:")
    y -= 22
    fill(INK)
    c.setFont("PJS800", 16)
    c.drawString(M, y, f"{config.BANK_NAME}  {config.BANK_ACCOUNT_NUMBER}")
    y -= 16
    fill(MUTED)
    c.setFont("PJS500", 10.5)
    c.drawString(M, y, "a.n. " + config.BANK_ACCOUNT_NAME)
    y -= 30
    fill(INK)
    c.setFont("PJS500", 10.5)
    for ln in _wrap(c, "Mohon pembayaran dapat segera dilakukan. Jika sudah melakukan pembayaran, mohon abaikan "
                       "surat ini dan kirimkan bukti transfernya kepada kami. Terima kasih atas kerja samanya.",
                    "PJS500", 10.5, W - 2 * M):
        c.drawString(M, y, ln)
        y -= 15
    y -= 26
    c.drawString(W - M - 170, y, "Hormat kami,")
    y -= 60
    c.setFont("PJS800", 11)
    c.drawString(W - M - 170, y, config.BUSINESS_NAME)
    c.showPage()
    c.save()
    nama = f"Tagihan-{''.join(ch for ch in cust['nama'] if ch.isalnum())[:20]}-{today}.pdf"
    return nama, buf.getvalue()
