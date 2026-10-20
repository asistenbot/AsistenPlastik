"""
Bot Telegram utama -- Asisten Plastik (Anugerah Sejahtera Sentosa).

Alur order: admin forward/paste chat customer (atau kirim foto chat/nota) ke
bot ini, bot parse pakai AI, tunjukin hasilnya buat dikonfirmasi, begitu OK
langsung disimpen ke Sheets + invoice & surat jalan otomatis kegenerate.
Order masuk KAPAN AJA langsung diproses (gak ada siklus mingguan).

Command lengkap ada di /start.
"""

import functools
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters,
)

import config
import documents
import dotmatrix
from ai_parser import (
    parse_order_text, parse_order_image, parse_po_text, classify_intent,
    parse_order_correction, parse_price_update, parse_price_update_image,
    parse_po_price_fill, parse_pending_order_correction,
)
from sheets_client import get_sheets_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
# Sembunyikan log detail httpx/httpcore supaya token bot tidak tercetak di log
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("asisten-plastik")


# ---------------- HELPERS ----------------

def owner_only(func):
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *a, **kw):
        user = update.effective_user
        if config.OWNER_TELEGRAM_IDS and (not user or user.id not in config.OWNER_TELEGRAM_IDS):
            await update.effective_message.reply_text(
                "Maaf, bot ini cuma buat admin. Chat @userinfobot buat tau ID Telegram kamu, "
                "terus minta admin tambahin ke OWNER_TELEGRAM_IDS."
            )
            return
        return await func(update, context, *a, **kw)
    return wrapper


def rupiah(n):
    return documents.rupiah(n)


def _sheets():
    return get_sheets_client()


def _fill_customer_defaults(parsed, sheets):
    """Kalau order nyebut customer yang udah ada di sheet Customers tapi no HP
    / alamatnya kosong, isi otomatis dari data customer."""
    try:
        cust = sheets.get_customer(parsed.get("nama_customer", ""))
    except Exception:
        logger.exception("gagal cari data customer")
        return
    if not cust:
        return
    for field, col in (("no_hp", "No_HP"), ("alamat", "Alamat")):
        if not (parsed.get(field) or "").strip() and str(cust.get(col, "") or "").strip():
            parsed[field] = str(cust[col]).strip()


_PENDING_KEYS = ("pending_order", "pending_po", "pending_edit", "pending_price_update", "pending_cancel", "pending_cancel_po")


def _has_pending(context):
    return any(context.user_data.get(k) for k in _PENDING_KEYS)


async def _send_text(update, text, reply_markup=None):
    await update.effective_message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
    )


# ---------------- PREVIEW TEXT ----------------

def _valid_tanggal_order(v):
    """'2026-09-28' -> '2026-09-28' kalau format YYYY-MM-DD valid, selain itu ''."""
    import datetime
    try:
        return datetime.datetime.strptime(str(v or "").strip(), "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError:
        return ""


def _order_preview_text(parsed):
    lines = ["*Hasil baca order:*", ""]
    lines.append(f"Customer: *{parsed.get('nama_customer', '-')}*")
    if parsed.get("no_hp"):
        lines.append(f"HP: {parsed['no_hp']}")
    if parsed.get("alamat"):
        lines.append(f"Alamat: {parsed['alamat']}")
    lines.append(f"Metode: {parsed.get('metode', 'Kirim')}")
    if _valid_tanggal_order(parsed.get("tanggal_order")):
        lines.append(f"Tanggal Order: {dotmatrix._tgl_label(_valid_tanggal_order(parsed.get('tanggal_order')))}")
    if parsed.get("no_po_customer"):
        lines.append(f"No. PO Customer: {parsed['no_po_customer']}")
    if parsed.get("tanggal_kirim"):
        lines.append(f"Tanggal Kirim: {parsed['tanggal_kirim']}")
    lines.append("")
    total = 0
    for it in parsed.get("items", []):
        harga = it.get("harga_satuan", 0)
        subtotal = float(it.get("qty", 0)) * float(harga or 0)
        total += subtotal
        flag = "" if it.get("item_code") else " ⚠️ *(produk gak ketemu di katalog, cek lagi)*"
        lines.append(f"• {it.get('nama_item')} x{it.get('qty')} {it.get('satuan', '')} = {rupiah(subtotal)}{flag}")
        if it.get("harga_katalog") is not None:
            lines.append(
                f"   ↳ harga {rupiah(harga)}/{it.get('satuan', '')} dari foto/chat "
                f"(harga katalog {rupiah(it['harga_katalog'])})"
            )
    ongkir = parsed.get("ongkir", 0) or 0
    lines.append("")
    lines.append(f"Subtotal: {rupiah(total)}")
    lines.append(f"Ongkir: {rupiah(ongkir)}")
    lines.append(f"*Total: {rupiah(total + float(ongkir))}*")
    if parsed.get("catatan"):
        lines.append("")
        lines.append(f"📝 Catatan AI: {parsed['catatan']}")
    return "\n".join(lines)


def _po_preview_text(parsed):
    lines = ["*Hasil baca PO ke supplier:*", ""]
    lines.append(f"Supplier: *{parsed.get('nama_supplier', '-')}*")
    lines.append("")
    total = 0
    for it in parsed.get("items", []):
        harga = it.get("harga_satuan", 0) or 0
        subtotal = float(it.get("qty", 0)) * float(harga)
        total += subtotal
        flag = "" if it.get("item_code") else " ⚠️ *(produk gak ketemu di katalog, cek lagi)*"
        lines.append(f"• {it.get('nama_item')} x{it.get('qty')} {it.get('satuan', '')} @ {rupiah(harga)} = {rupiah(subtotal)}{flag}")
    lines.append("")
    lines.append(f"*Total belanja: {rupiah(total)}*")
    if parsed.get("catatan"):
        lines.append("")
        lines.append(f"📝 Catatan AI: {parsed['catatan']}")
    return "\n".join(lines)


def _item_label(row):
    """Nama barang buat ditampilin di invoice/surat jalan/PO -- gabungin Nama
    sama Deskripsi dari PriceList (misal 'Sablon 1 Sisi' vs 'Sablon 2 Sisi')
    kalau ada, soalnya ada produk yang Nama-nya SAMA PERSIS tapi beda varian
    sablon/keterangan (dibedain lewat Item_Code & Deskripsi aja). 'POLOS'
    gak ditampilin biar gak nambah noise di barang yang emang polosan."""
    nama = row.get("Nama", "") or ""
    deskripsi = str(row.get("Deskripsi", "") or "").strip()
    if deskripsi and deskripsi.upper() != "POLOS":
        return f"{nama} ({deskripsi})"
    return nama


def _resolve_po_items_with_catalog(parsed_items, sheets):
    """Setelah AI baca teks PO, cocokin ULANG tiap item ke katalog PriceList
    (via item_code yang dikasih AI, atau find_product kalau item_code kosong)
    supaya nama_item & satuan-nya PERSIS sama kayak di katalog -- bukan hasil
    AI nulis ulang/gabung sendiri ukuran barang dari singkatan admin (ini
    yang bikin bug "90 100kg" kebaca jadi ukuran "90 x100" padahal 100kg itu
    qty). Harga yang udah kebaca AI (baik dari teks eksplisit maupun histori
    katalog) tetap dipakai kalau > 0; kalau masih 0 dan produknya ketemu di
    katalog, coba isi dari Harga_Beli katalog sebagai fallback terakhir."""
    price_map = sheets.get_price_map()
    resolved = []
    for it in parsed_items:
        code = (it.get("item_code") or "").strip().upper()
        row = price_map.get(code) if code else None
        if row is None:
            row = sheets.find_product(it.get("nama_item", ""))
        harga = it.get("harga_satuan", 0) or 0
        try:
            harga = float(harga)
        except (TypeError, ValueError):
            harga = 0
        if row is not None:
            if not harga:
                try:
                    harga = float(row.get("Harga_Beli", 0) or 0)
                except (TypeError, ValueError):
                    harga = 0
            resolved.append({
                "item_code": row["Item_Code"],
                "nama_item": _item_label(row),
                "satuan": row.get("Satuan", it.get("satuan", "")),
                "harga_satuan": harga,
                "qty": it.get("qty", 0),
            })
        else:
            resolved.append({
                "item_code": "",
                "nama_item": it.get("nama_item", "?"),
                "satuan": it.get("satuan", ""),
                "harga_satuan": harga,
                "qty": it.get("qty", 0),
            })
    return resolved


def _harga_dari_dokumen(it):
    """Harga per satuan yang kebaca jelas dari foto/chat (>0), atau None."""
    try:
        h = float(it.get("harga_satuan"))
    except (TypeError, ValueError):
        return None
    return h if h > 0 else None


def _resolve_items_with_price(parsed_items, sheets):
    """Isi ulang item yang item_code-nya kosong dengan hasil find_product.
    Harga default-nya dari PriceList (bukan tebakan AI). Pengecualian: kalau
    foto/chat menyebut jelas harga per satuan (misal nota/invoice customer),
    harga itu dipakai, dan harga katalog disimpan di 'harga_katalog' buat
    ditampilin di preview kalau beda."""
    resolved = []
    for it in parsed_items:
        code = (it.get("item_code") or "").strip()
        row = None
        if code:
            row = sheets.get_price_map().get(code.upper())
        if row is None:
            row = sheets.find_product(it.get("nama_item", ""))
        harga_doc = _harga_dari_dokumen(it)
        if row is not None:
            harga_kat = row.get("Harga_Jual", 0)
            item = {
                "item_code": row["Item_Code"],
                "nama_item": _item_label(row),
                "kategori": row.get("Kategori", ""),
                "satuan": row.get("Satuan", it.get("satuan", "")),
                "harga_satuan": harga_doc if harga_doc is not None else harga_kat,
                "qty": it.get("qty", 0),
            }
            try:
                if harga_doc is not None and float(harga_kat or 0) != harga_doc:
                    item["harga_katalog"] = harga_kat
            except (TypeError, ValueError):
                pass
            resolved.append(item)
        else:
            resolved.append({
                "item_code": "",
                "nama_item": it.get("nama_item", "?"),
                "kategori": "",
                "satuan": it.get("satuan", ""),
                "harga_satuan": harga_doc if harga_doc is not None else 0,
                "qty": it.get("qty", 0),
            })
    return resolved


# ---------------- COMMANDS ----------------

HELP_TEXT = f"""Halo! Ini *Asisten {config.BUSINESS_NAME}* 👋

*Cara pakai (order customer):*
Tinggal paste/forward chat order customer ke sini, atau kirim fotonya
(screenshot chat / nota tulisan tangan). Bot bakal baca & bikinin invoice +
surat jalan otomatis, tinggal dikonfirmasi dulu.

*Gak usah apal command!* Boleh langsung nanya santai kayak "utang ke
siapa aja masih ada", "piutang berapa sih", "kas bulan ini gimana",
"si Budi udah bayar", "bayar utang ke CV Sumber 500rb" -- bot bakal ngerti
sendiri.

*Salah ketik pas bikin order?* Tinggal chat lagi abis invoice muncul,
misal "edit Grandia Hotel" (kalau nama customernya salah), "alamatnya
salah, harusnya Jl. Melati No. 5", atau "qty-nya jadi 25 pack" -- bot
bakal nanya konfirmasi dulu, begitu di-OK invoice & surat jalannya
otomatis dicetak ulang. Default-nya ngedit order yang PALING BARU; kalau
mau invoice lain, sebutin nomor invoice-nya, misal "invoice
INV-20260828-001 no HP-nya ganti 08123456789".

*Pengingat otomatis:* tiap invoice terbit, bot ngingetin jam 08.00 buat
kontra bon (sesuai hari kontra bon customer) lalu cek pembayaran 14 hari
kemudian; tiap PO dibuka, bot ngingetin bayar supplier sesuai tempo. Tinggal
pencet tombol Sudah / Belum. Lihat jadwalnya: /pengingat. Hari kontra bon &
tempo diatur di tab PengaturanTagihan (Google Sheets).

*Order-nya gak jadi / mau dihapus total?* Bilang aja "hapus order Grandia
Hotel" atau "batalin invoice INV-20260828-001" -- bot nanya konfirmasi
dulu, begitu di-OK order ditandai Batal (datanya tetep ada buat histori,
tapi otomatis keluar dari piutang).

*Mau update harga jual/beli produk?* Tinggal bilang aja, misal "harga
tulip naik jadi 17000" atau "update harga TUL-01 jadi 16500" -- bot
nunjukin dulu harga lama → baru buat dikonfirmasi, begitu di-OK langsung
keupdate di PriceList Google Sheets. Kalau harga barunya dari daftar harga
supplier yang difoto, kirim fotonya dengan CAPTION yang jelas (misal
"update harga beli dari foto ini" atau "daftar harga supplier baru"), bot
bakal baca semua barang di foto sekaligus (dianggap harga BELI/modal) --
tanpa caption yang jelas, foto dianggap ORDER customer (biar aman).

Command di bawah ini cadangan aja kalau mau lebih pasti/cepat:
/pricelist — lihat daftar harga produk
/invoice <no invoice atau nama customer> — cetak ulang invoice
/suratjalan <no invoice atau nama customer> — cetak ulang surat jalan
/dokumen <no invoice atau nama customer> — cetak ulang invoice + surat jalan
(kalau customer punya banyak invoice, bot kasih daftar buat dipilih)
/lunas <no invoice atau nama customer> — tandai order sudah dibayar
/pengingat — lihat jadwal pengingat (kontra bon, tagihan, bayar supplier)
/piutang — rekap tagihan customer yang belum lunas

/po — bikin Purchase Order (belanja) ke supplier
/bayarutang <nama supplier> <jumlah> — catat pembayaran ke supplier
/utang — rekap utang ke semua supplier

/kas masuk <jumlah> <keterangan> — catat uang masuk di luar penjualan
/kas keluar <jumlah> <keterangan> — catat uang keluar (operasional dll)
/laporanbulanan [YYYY-MM] — laporan kas & laba rugi bulanan

/batal — batalin order/PO yang lagi nunggu konfirmasi
"""


@owner_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_text(update, HELP_TEXT)


@owner_only
async def groupid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(f"Chat ID: `{update.effective_chat.id}`", parse_mode=ParseMode.MARKDOWN)


async def _do_pricelist(update):
    text = _sheets().get_pricelist_text()
    await _send_text(update, text or "Belum ada produk di PriceList.")


@owner_only
async def pricelist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _do_pricelist(update)


@owner_only
async def batal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("pending_order", None)
    context.user_data.pop("pending_po", None)
    context.user_data.pop("pending_edit", None)
    context.user_data.pop("pending_price_update", None)
    context.user_data.pop("pending_cancel", None)
    context.user_data.pop("awaiting", None)
    await update.effective_message.reply_text("Oke, dibatalin.")


async def _do_piutang(update):
    summary = _sheets().get_piutang_summary()
    if not summary:
        await update.effective_message.reply_text("Gak ada piutang, semua customer udah lunas 🎉")
        return
    lines = ["*Piutang customer (belum lunas):*", ""]
    total = 0
    for nama, jumlah in sorted(summary.items(), key=lambda x: -x[1]):
        lines.append(f"• {nama}: {rupiah(jumlah)}")
        total += jumlah
    lines.append("")
    lines.append(f"*Total piutang: {rupiah(total)}*")
    await _send_text(update, "\n".join(lines))


@owner_only
async def piutang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _do_piutang(update)


async def _do_utang(update):
    summary = _sheets().get_utang_summary()
    if not summary:
        await update.effective_message.reply_text("Gak ada utang ke supplier saat ini 🎉")
        return
    lines = ["*Utang ke supplier (belum lunas):*", ""]
    total = 0
    for nama, jumlah in sorted(summary.items(), key=lambda x: -x[1]):
        lines.append(f"• {nama}: {rupiah(jumlah)}")
        total += jumlah
    lines.append("")
    lines.append(f"*Total utang: {rupiah(total)}*")
    await _send_text(update, "\n".join(lines))


@owner_only
async def utang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _do_utang(update)


async def _do_lunas(update, key):
    if not key:
        await update.effective_message.reply_text("Invoice/customer mana yang mau ditandai lunas?")
        return
    sheets = _sheets()
    no_invoice = key if key.upper().startswith(config.INVOICE_PREFIX) else sheets.get_latest_invoice_for_customer(key)
    if not no_invoice:
        await update.effective_message.reply_text(f"Gak ketemu order buat '{key}'.")
        return
    total = sheets.mark_order_lunas(no_invoice)
    if total is None:
        await update.effective_message.reply_text(f"Invoice {no_invoice} gak ketemu.")
        return
    sheets.add_kas_entry("Masuk", "Penjualan", total, keterangan=f"Pelunasan {no_invoice}", ref=no_invoice)
    await update.effective_message.reply_text(
        f"✅ {no_invoice} ditandai *Lunas* ({rupiah(total)}), udah dicatat ke Kas Masuk.",
        parse_mode=ParseMode.MARKDOWN,
    )


async def _ask_lunas(update, key):
    """Lunas dari chat bebas: konfirmasi dulu biar gak salah catat."""
    if not key:
        await update.effective_message.reply_text("Invoice/customer mana yang mau ditandai lunas?")
        return
    sheets = _sheets()
    inv = key if key.upper().startswith(config.INVOICE_PREFIX) else await _pilih_invoice(
        update, key, "lpick", "Pilih yang udah dibayar:", hanya_pending=True)
    if not inv:
        return
    rows = sheets.get_order_items(inv)
    if not rows:
        await update.effective_message.reply_text(f"Gak ketemu order buat '{key}'.")
        return
    if str(rows[0].get("Status", "")) == "Lunas":
        await update.effective_message.reply_text(f"{inv} udah Lunas.")
        return
    total = 0.0
    for r in rows:
        try:
            total += float(r.get("Subtotal", 0) or 0)
        except (TypeError, ValueError):
            pass
    try:
        total += float(rows[0].get("Ongkir", 0) or 0)
    except (TypeError, ValueError):
        pass
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Ya, udah bayar (Lunas)", callback_data=f"lunasok:{inv}"),
                                InlineKeyboardButton("❌ Batal", callback_data="lunasno")]])
    await update.effective_message.reply_text(
        f"{rows[0].get('Nama_Customer','')} - {inv} ({rupiah(total)})\n"
        "Beneran udah BAYAR / duitnya masuk? (kontra bon belum dihitung lunas)", reply_markup=kb)


async def _do_kontrabon(update, key, raw_text=""):
    """Kontra bon: tampilin tombol Sudah/Belum, BUKAN lunas."""
    import datetime
    import re
    sheets = _sheets()
    key = (key or "").strip()
    if not key:
        key = re.sub(r"(?i)\b(sudah|udah|belum|blm|sdh|di|ke)?\s*kontra\s*-?\s*bon\w*", " ", raw_text or "").strip()
    if not key:
        await update.effective_message.reply_text("Kontra bon customer yang mana?")
        return
    kl = key.lower()
    rems = [r for r in sheets.get_active_reminders()
            if r.get("Jenis") == "kontra_bon" and kl in str(r.get("Nama", "")).lower()]
    if not rems:
        inv = key if key.upper().startswith(config.INVOICE_PREFIX) else sheets.get_latest_invoice_for_customer(key)
        rows = sheets.get_order_items(inv) if inv else []
        if not rows:
            await update.effective_message.reply_text(f"Gak ketemu order buat '{key}'.")
            return
        if str(rows[0].get("Status", "")) != "Pending":
            await update.effective_message.reply_text(f"{inv} statusnya {rows[0].get('Status')}, gak perlu kontra bon.")
            return
        total = sum(float(r.get("Subtotal", 0) or 0) for r in rows) + float(rows[0].get("Ongkir", 0) or 0)
        rid = sheets.add_reminder("kontra_bon", inv, rows[0].get("Nama_Customer", ""), total,
                                  _wib_now().date(), "Manual dari chat")
        rems = [sheets.get_reminder(rid)]
    by_nama = {}
    for rem in rems:
        by_nama.setdefault(rem.get("Nama", ""), []).append(rem)
    for group in by_nama.values():
        text, kb = _kb_list_message(group) if len(group) > 1 else _reminder_message(group[0])
        await update.effective_message.reply_text(text, reply_markup=kb)


@owner_only
async def batallunas_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = " ".join(context.args) if context.args else ""
    if not key.upper().startswith(config.INVOICE_PREFIX):
        await update.effective_message.reply_text("Pakai nomor invoice: /batallunas INV-20260806-1287")
        return
    total = _sheets().unmark_order_lunas(key.upper())
    if total is None:
        await update.effective_message.reply_text(f"Invoice {key} gak ketemu.")
        return
    await update.effective_message.reply_text(
        f"↩️ {key.upper()} dibalikin ke Pending ({rupiah(total)}), catatan Kas Masuk-nya dihapus. "
        "Pengingat cek pembayaran dipasang lagi.")


@owner_only
async def lunas_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _ask_lunas(update, " ".join(context.args) if context.args else "")


_DOC_LABEL = {"inv": "Invoice", "sj": "Surat Jalan", "both": "Invoice + Surat Jalan"}


async def _kirim_dokumen(update, context, no_invoice, kind):
    if kind in ("inv", "both"):
        await _kirim_invoice(update, context, no_invoice)
    if kind in ("sj", "both"):
        await _kirim_surat_jalan(update, context, no_invoice)


async def _lookup_dokumen(update, context, key, kind):
    """Cetak ulang invoice / surat jalan. Kalau yang disebut nomor invoice,
    langsung dikirim. Kalau nama customer dan dia punya >1 invoice, tampilin
    daftar invoice-nya buat dipilih; kalau cuma 1, langsung dikirim."""
    key = (key or "").strip()
    if not key:
        await update.effective_message.reply_text(
            f"Invoice/customer mana yang mau dicetak ulang {_DOC_LABEL[kind]}-nya? "
            "Sebutin nomor invoice atau nama customer."
        )
        return
    if key.upper().startswith(config.INVOICE_PREFIX):
        await _kirim_dokumen(update, context, key, kind)
        return
    invs = _sheets().find_customer_invoices(key)
    if not invs:
        await update.effective_message.reply_text(f"Gak ketemu order buat '{key}'.")
        return
    if len(invs) == 1:
        await _kirim_dokumen(update, context, invs[0]["no_invoice"], kind)
        return
    rows = []
    for d in invs:
        icon = "✅" if d["status"] == "Lunas" else "⏳"
        rows.append([InlineKeyboardButton(
            f"{icon} {d['no_invoice']} • {d['tanggal']} • {rupiah(d['total'])}",
            callback_data=f"doc:{kind}:{d['no_invoice']}",
        )])
    await update.effective_message.reply_text(
        f"{invs[0]['nama']} punya {len(invs)} invoice (terbaru di atas). "
        f"Pilih yang mau dicetak ({_DOC_LABEL[kind]}):  ✅ lunas, ⏳ belum lunas",
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def _do_invoice_lookup(update, context, key):
    await _lookup_dokumen(update, context, key, "inv")


@owner_only
async def invoice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _do_invoice_lookup(update, context, " ".join(context.args) if context.args else "")


async def _do_suratjalan_lookup(update, context, key):
    await _lookup_dokumen(update, context, key, "sj")


@owner_only
async def suratjalan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _do_suratjalan_lookup(update, context, " ".join(context.args) if context.args else "")


@owner_only
async def dokumen_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _lookup_dokumen(update, context, " ".join(context.args) if context.args else "", "both")


# ---------------- TOPIK GRUP ----------------
TOPIK_LABEL = {
    "order": "🛒 Order", "invoice": "🧾 Invoice", "suratjalan": "🚚 Surat Jalan",
    "po": "📦 PO Supplier", "rekap": "📊 Rekap Bulanan", "pengingat": "⏰ Pengingat", "error": "⚠️ Error",
}
_TOPIK_CACHE = {"data": None}


def _topik_map(force=False):
    if force or _TOPIK_CACHE["data"] is None:
        try:
            _TOPIK_CACHE["data"] = _sheets().get_topik_all()
        except Exception:
            logger.exception("gagal baca TopikGrup")
            return _TOPIK_CACHE["data"] or {}
    return _TOPIK_CACHE["data"]


async def _mirror(bot, kunci, skip_chat=None, skip_thread=None, **kw):
    """Salin kiriman ke topik grup yang udah didaftarin (kalau ada).
    kw: text= | document=,filename=,caption= | photo=,caption=. Gagal = diabaikan."""
    target = _topik_map().get(kunci)
    if not target:
        return
    chat, thread = target
    if skip_chat == chat and skip_thread == thread:
        return
    try:
        extra = {"message_thread_id": thread} if thread else {}
        doc = kw.get("document")
        if doc is not None and hasattr(doc, "seek"):
            doc.seek(0)
        if "text" in kw:
            await bot.send_message(chat_id=chat, text=kw["text"], reply_markup=kw.get("reply_markup"), **extra)
        elif doc is not None:
            await bot.send_document(chat_id=chat, document=doc, filename=kw.get("filename"),
                                    caption=kw.get("caption"), **extra)
        elif "photo" in kw:
            await bot.send_photo(chat_id=chat, photo=kw["photo"], caption=kw.get("caption"), **extra)
    except Exception:
        logger.exception("gagal mirror ke topik %s", kunci)


@owner_only
async def topik_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    arg = (context.args[0].lower() if context.args else "")
    if arg in TOPIK_LABEL:
        if update.effective_chat.type == "private":
            await msg.reply_text("Command ini diketik DI DALAM topik grup yang mau didaftarin, bukan di chat pribadi.")
            return
        thread = msg.message_thread_id if getattr(msg, "is_topic_message", False) else None
        _sheets().set_topik(arg, update.effective_chat.id, thread)
        _topik_map(force=True)
        await msg.reply_text(f"✅ Topik ini sekarang jadi tempat {TOPIK_LABEL[arg]}.")
        return
    data = _topik_map(force=True)
    lines = ["Status topik grup:", ""]
    for k, lab in TOPIK_LABEL.items():
        lines.append(f"{'✅' if k in data else '❌'} {lab}  (daftar: /topik {k})")
    lines += ["", "Cara daftar: buka topiknya di grup, ketik /topik <nama> (mis. /topik invoice)."]
    await msg.reply_text("\n".join(lines))


async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    logger.error("error di bot", exc_info=context.error)
    err = f"⚠️ {type(context.error).__name__}: {str(context.error)[:300]}"
    await _mirror(context.bot, "error", text=err)


async def _kirim_dotmatrix(update, judul, nama_dok, pages, txt, pdf, kunci=None):
    """Cukup kirim 1 file PDF kertas 8,5 x 5,5 inch (siap print)."""
    cap = f"{judul} — PDF ukuran kertas 8,5 x 5,5 inch, siap print"
    await update.effective_message.reply_document(document=pdf, filename=f"{nama_dok}.pdf", caption=cap)
    if kunci:
        m = update.effective_message
        await _mirror(m.get_bot(), kunci, skip_chat=update.effective_chat.id,
                      skip_thread=m.message_thread_id if getattr(m, "is_topic_message", False) else None,
                      document=pdf, filename=f"{nama_dok}.pdf", caption=cap)


async def _kirim_invoice(update, context, no_invoice):
    sheets = _sheets()
    rows = sheets.get_order_items(no_invoice)
    if not rows:
        await update.effective_message.reply_text(f"Invoice {no_invoice} gak ketemu.")
        return
    first = rows[0]
    items = [{"nama_item": r["Nama_Item"], "qty": r["Qty"], "satuan": r["Satuan"], "harga_satuan": r["Harga_Satuan"]} for r in rows]
    ongkir = 0
    for r in rows:
        try:
            ongkir += float(r.get("Ongkir", 0) or 0)
        except ValueError:
            pass
    pages, txt, pdf = dotmatrix.generate_invoice_dotmatrix(
        no_invoice, first["Nama_Customer"], first.get("No_HP", ""), first.get("Alamat", ""),
        first.get("Metode", "Kirim"), items, ongkir,
        no_po_customer=first.get("No_PO_Customer", ""),
        tanggal_kirim=first.get("Tanggal_Kirim", ""),
        tanggal=first.get("Timestamp", ""),
    )
    await _kirim_dotmatrix(update, f"Invoice {no_invoice}", no_invoice, pages, txt, pdf, kunci="invoice")


async def _kirim_surat_jalan(update, context, no_invoice):
    sheets = _sheets()
    rows = sheets.get_order_items(no_invoice)
    if not rows:
        await update.effective_message.reply_text(f"Invoice {no_invoice} gak ketemu.")
        return
    first = rows[0]
    items = [{"nama_item": r["Nama_Item"], "qty": r["Qty"], "satuan": r["Satuan"]} for r in rows]
    no_sj = no_invoice.replace(config.INVOICE_PREFIX, config.SURAT_JALAN_PREFIX, 1)
    pages, txt, pdf = dotmatrix.generate_surat_jalan_dotmatrix(
        no_sj, first["Nama_Customer"], first.get("No_HP", ""), first.get("Alamat", ""),
        first.get("Metode", "Kirim"), items, no_invoice_ref=no_invoice,
        no_po_customer=first.get("No_PO_Customer", ""),
        tanggal_kirim=first.get("Tanggal_Kirim", ""),
        tanggal=first.get("Timestamp", ""),
    )
    await _kirim_dotmatrix(update, f"Surat Jalan {no_sj}", no_sj, pages, txt, pdf, kunci="suratjalan")


# ---------------- KAS & LAPORAN ----------------

@owner_only
async def kas_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.effective_message.reply_text(
            "Format: /kas masuk <jumlah> <keterangan>\natau: /kas keluar <jumlah> <keterangan>"
        )
        return
    jenis_raw = context.args[0].lower()
    jenis = "Masuk" if jenis_raw in ("masuk", "in") else "Keluar" if jenis_raw in ("keluar", "out") else None
    if jenis is None:
        await update.effective_message.reply_text("Jenis harus 'masuk' atau 'keluar'.")
        return
    try:
        jumlah = float(context.args[1].replace(".", "").replace(",", ""))
    except ValueError:
        await update.effective_message.reply_text("Jumlah harus angka, contoh: /kas keluar 50000 bayar listrik")
        return
    keterangan = " ".join(context.args[2:]) or "-"
    kategori = "Operasional" if jenis == "Keluar" else "Lainnya"
    _sheets().add_kas_entry(jenis, kategori, jumlah, keterangan=keterangan)
    await update.effective_message.reply_text(f"✅ Kas {jenis.lower()} {rupiah(jumlah)} dicatat ({keterangan}).")


async def _do_bayarutang(update, nama_supplier, jumlah, catatan=""):
    if not nama_supplier or not jumlah:
        await update.effective_message.reply_text("Bayar utang ke supplier siapa, berapa jumlahnya?")
        return
    sisa = _sheets().bayar_utang(nama_supplier, jumlah, catatan)
    _sheets().add_kas_entry("Keluar", "Bayar Supplier", jumlah, keterangan=f"Bayar utang {nama_supplier} {catatan}".strip())
    sisa_text = rupiah(sisa) if sisa > 0 else "Rp0 (lunas)"
    await update.effective_message.reply_text(f"✅ Pembayaran {rupiah(jumlah)} ke *{nama_supplier}* dicatat. Sisa utang: {sisa_text}", parse_mode=ParseMode.MARKDOWN)


@owner_only
async def bayarutang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.effective_message.reply_text("Format: /bayarutang <nama supplier> <jumlah> [catatan]")
        return
    # cara paling gampang: jumlah = angka terakhir yang valid, sisanya nama supplier
    jumlah = None
    jumlah_idx = None
    for i in range(len(context.args) - 1, -1, -1):
        raw = context.args[i].replace(".", "").replace(",", "")
        if raw.isdigit():
            jumlah = float(raw)
            jumlah_idx = i
            break
    if jumlah is None:
        await update.effective_message.reply_text("Gak nemu jumlah uangnya. Format: /bayarutang <nama supplier> <jumlah> [catatan]")
        return
    nama_supplier = " ".join(context.args[:jumlah_idx])
    catatan = " ".join(context.args[jumlah_idx + 1:])
    await _do_bayarutang(update, nama_supplier, jumlah, catatan)


BULAN_NAMA = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
              "Agustus", "September", "Oktober", "November", "Desember"]


def _teks_laporan(year, month):
    lap = _sheets().get_laporan_bulanan(year, month)
    lines = [f"*Laporan Kas — {BULAN_NAMA[month]} {year}*", ""]
    lines.append("Kas Masuk:")
    for kat, val in lap["masuk_by_kategori"].items():
        lines.append(f"  • {kat}: {rupiah(val)}")
    lines.append(f"Total Masuk: {rupiah(lap['total_masuk'])}")
    lines.append("")
    lines.append("Kas Keluar:")
    for kat, val in lap["keluar_by_kategori"].items():
        lines.append(f"  • {kat}: {rupiah(val)}")
    lines.append(f"Total Keluar: {rupiah(lap['total_keluar'])}")
    lines.append("")
    lines.append(f"*Laba/Rugi bersih: {rupiah(lap['laba'])}*")
    return "\n".join(lines)


async def _do_laporanbulanan(update, year, month):
    teks = _teks_laporan(year, month)
    await _send_text(update, teks)
    m = update.effective_message
    await _mirror(m.get_bot(), "rekap", skip_chat=update.effective_chat.id,
                  skip_thread=m.message_thread_id if getattr(m, "is_topic_message", False) else None,
                  text=teks.replace("*", ""))


async def rekap_job(context: ContextTypes.DEFAULT_TYPE):
    """Tiap tanggal 1 (>= jam 08 WIB): kirim rekap bulan lalu otomatis, sekali aja."""
    now = _wib_now()
    if now.day != 1 or now.hour < config.REMINDER_HOUR:
        return
    import datetime
    last = now.replace(day=1) - datetime.timedelta(days=1)
    ref = f"REKAP-{last.year}-{last.month:02d}"
    try:
        sheets = _sheets()
        if any(str(r.get("Ref", "")) == ref for r in sheets._reminder_records()):
            return
        teks = _teks_laporan(last.year, last.month)
        for chat_id in [c for c in config.OWNER_TELEGRAM_IDS if c]:
            try:
                await context.bot.send_message(chat_id=chat_id, text=teks, parse_mode=ParseMode.MARKDOWN)
            except Exception:
                logger.exception("gagal kirim rekap ke %s", chat_id)
        await _mirror(context.bot, "rekap", text=teks.replace("*", ""))
        rid = sheets.add_reminder("rekap", ref, "Rekap Bulanan", 0, now.date(), "Rekap otomatis")
        sheets.update_reminder(rid, Status="Selesai")
    except Exception:
        logger.exception("gagal kirim rekap bulanan")


@owner_only
async def laporanbulanan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import datetime
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
    year, month = now.year, now.month
    if context.args:
        try:
            year, month = [int(x) for x in context.args[0].split("-")]
        except ValueError:
            await update.effective_message.reply_text("Format: /laporanbulanan atau /laporanbulanan 2026-07")
            return
    await _do_laporanbulanan(update, year, month)


# ---------------- ORDER FLOW (teks & foto) ----------------

@owner_only
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.effective_message.text or ""
    awaiting = context.user_data.get("awaiting")

    if awaiting == "po_text":
        context.user_data["awaiting"] = None
        await _process_po_text(update, context, text)
        return

    pending_po = context.user_data.get("pending_po")
    other_pending = any(context.user_data.get(k) for k in _PENDING_KEYS if k != "pending_po")
    if pending_po and not other_pending:
        if await _try_fill_po_price(update, context, pending_po, text):
            return

    pending_order = context.user_data.get("pending_order")
    other_pending_for_order = any(context.user_data.get(k) for k in _PENDING_KEYS if k != "pending_order")
    if pending_order and not other_pending_for_order:
        if await _try_correct_pending_order(update, context, pending_order, text):
            return

    if _has_pending(context):
        await update.effective_message.reply_text(
            "Masih ada order/PO/perubahan yang nunggu konfirmasi di atas. Klik tombolnya dulu, atau /batal buat batalin."
        )
        return

    await _route_text(update, context, text)


async def _route_text(update, context, text):
    """Semua chat bebas (bukan command, bukan lagi nunggu konfirmasi) lewat
    sini dulu -- ditebak dulu maksudnya (order? nanya laporan? bayar utang?)
    pakai AI, biar gak perlu apal command. Kalau gagal nebak / gak yakin,
    default-nya tetep dianggap ORDER customer (paling aman)."""
    try:
        route = classify_intent(text)
    except Exception:
        logger.exception("gagal classify_intent, fallback ke order")
        route = {"intent": "order"}

    intent = route.get("intent", "order")
    import re as _re
    if intent != "order" and _re.search(r"kontra\s*-?\s*bon", text, _re.I):
        intent = "kontra_bon"
    target = (route.get("target") or "").strip()
    bulan = (route.get("bulan") or "").strip()
    jumlah = route.get("jumlah") or 0

    if intent == "report_pricelist":
        await _do_pricelist(update)
    elif intent == "report_piutang":
        await _do_piutang(update)
    elif intent == "report_utang":
        await _do_utang(update)
    elif intent == "report_kas_bulanan":
        import datetime
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=7)
        year, month = now.year, now.month
        if bulan:
            try:
                year, month = [int(x) for x in bulan.split("-")]
            except ValueError:
                pass
        await _do_laporanbulanan(update, year, month)
    elif intent == "kontra_bon":
        await _do_kontrabon(update, target, text)
    elif intent == "mark_lunas":
        await _ask_lunas(update, target)
    elif intent == "bayar_utang":
        await _do_bayarutang(update, target, float(jumlah) if jumlah else 0)
    elif intent == "lihat_invoice":
        await _do_invoice_lookup(update, context, target)
    elif intent == "lihat_suratjalan":
        await _do_suratjalan_lookup(update, context, target)
    elif intent == "edit_order":
        await _do_edit_order(update, context, target, text)
    elif intent == "batal_order":
        await _do_cancel_order(update, context, target)
    elif intent == "batal_po":
        await _do_cancel_po(update, context, target)
    elif intent == "update_harga":
        await _do_update_harga(update, context, text)
    elif intent == "po":
        await _process_po_text(update, context, text)
    elif intent == "lainnya":
        await update.effective_message.reply_text(
            "Hmm, kurang paham maksudnya. Kirim order customer, atau tanya soal "
            "utang/piutang/kas/harga -- ketik /start buat liat semua yang bisa gua bantu."
        )
    else:  # "order" atau intent gak dikenal -> default paling aman
        await _process_order_text(update, context, text)


async def _process_order_text(update, context, text):
    await update.effective_message.reply_chat_action("typing")
    sheets = _sheets()
    try:
        parsed = parse_order_text(text, sheets.get_price_list(), sheets.get_customer_names())
    except Exception as e:
        logger.exception("gagal parse order teks")
        await update.effective_message.reply_text(f"Waduh, gagal baca order ini: {e}")
        return
    parsed["items"] = _resolve_items_with_price(parsed.get("items", []), sheets)
    _fill_customer_defaults(parsed, sheets)

    # Safety net: kalau AI gak nemu barang order sama sekali, jangan tunjukin
    # preview order kosong (Rp0) dengan tombol Simpan -- bikin bingung dan
    # kalau kepencet malah nyimpen order kosong ke Sheets.
    if not parsed.get("items"):
        msg = "Gak nemu barang order di pesan ini."
        if parsed.get("catatan"):
            msg += f"\n\n📝 {parsed['catatan']}"
        await update.effective_message.reply_text(msg)
        return

    context.user_data["pending_order"] = parsed
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Simpan", callback_data="order_confirm"),
        InlineKeyboardButton("❌ Batal", callback_data="order_cancel"),
    ]])
    await _send_text(update, _order_preview_text(parsed), reply_markup=kb)


_EDIT_FIELD_LABEL = {
    "nama_customer": "Nama Customer", "no_hp": "No HP",
    "alamat": "Alamat", "metode": "Metode",
    "no_po_customer": "No. PO Customer", "tanggal_kirim": "Tanggal Kirim",
    "tanggal_order": "Tanggal Order",
}
_EDIT_FIELD_COLUMN = {
    "nama_customer": "Nama_Customer", "no_hp": "No_HP",
    "alamat": "Alamat", "metode": "Metode",
    "no_po_customer": "No_PO_Customer", "tanggal_kirim": "Tanggal_Kirim",
}


async def _do_edit_order(update, context, target, text):
    sheets = _sheets()

    no_invoice = None
    if target and target.upper().startswith(config.INVOICE_PREFIX):
        no_invoice = target
    elif target:
        no_invoice = await _pilih_invoice(update, target, "epick", "Pilih yang mau diedit:")
        if not no_invoice:
            context.user_data["edit_text"] = text
            return
    if not no_invoice:
        no_invoice = context.user_data.get("last_invoice")
    if not no_invoice:
        await update.effective_message.reply_text(
            "Order/invoice yang mana yang mau diedit? Sebutin nomor invoice-nya "
            "atau nama customernya, contoh: \"invoice INV-20260828-001 nama "
            "customernya salah, harusnya Grandia Hotel\"."
        )
        return

    rows = sheets.get_order_items(no_invoice)
    if not rows:
        await update.effective_message.reply_text(f"Invoice {no_invoice} gak ketemu.")
        return
    first = rows[0]
    items_desc = "\n".join(
        f"  - {r.get('Item_Code','')} | {r.get('Nama_Item','')} | qty {r.get('Qty','')} {r.get('Satuan','')} "
        f"| harga satuan Rp{r.get('Harga_Satuan','')}"
        for r in rows
    )
    current_desc = (
        f"No Invoice: {no_invoice}\n"
        f"Nama Customer: {first.get('Nama_Customer', '')}\n"
        f"No HP: {first.get('No_HP', '')}\n"
        f"Alamat: {first.get('Alamat', '')}\n"
        f"Metode: {first.get('Metode', '')}\n"
        f"No. PO Customer: {first.get('No_PO_Customer', '')}\n"
        f"Tanggal Kirim: {first.get('Tanggal_Kirim', '')}\n"
        f"ITEM DI ORDER INI:\n{items_desc}"
    )
    try:
        corr = parse_order_correction(text, current_desc)
    except Exception as e:
        logger.exception("gagal parse koreksi order")
        await update.effective_message.reply_text(f"Waduh, gagal baca koreksinya: {e}")
        return

    header_fields = {"nama_customer", "no_hp", "alamat", "metode", "no_po_customer", "tanggal_kirim"}
    updates = {
        k: (v or "").strip() for k, v in corr.items()
        if k in header_fields and (v or "").strip()
    }

    item_updates = []
    rows_by_code = {str(r.get("Item_Code", "")).strip().upper(): r for r in rows}
    for it in corr.get("items", []) or []:
        code = (it.get("item_code") or "").strip()
        item_baru_text = (it.get("item_baru") or "").strip()
        qty_baru = it.get("qty_baru") or None
        harga_baru = it.get("harga_satuan_baru") or None
        if not code or (qty_baru is None and harga_baru is None and not item_baru_text):
            continue
        cur_row = rows_by_code.get(code.upper())
        if not cur_row:
            continue

        item_baru = None
        if item_baru_text:
            prod = sheets.find_product(item_baru_text)
            if prod:
                new_harga_jual = prod.get("Harga_Jual") or None
                item_baru = {
                    "found_in_catalog": True,
                    "new_item_code": str(prod.get("Item_Code", "")).strip(),
                    "new_nama": _item_label(prod) or item_baru_text,
                    "new_satuan": prod.get("Satuan", "") or cur_row.get("Satuan", ""),
                    "new_kategori": prod.get("Kategori", "") or cur_row.get("Kategori", ""),
                }
                if harga_baru is None and new_harga_jual:
                    try:
                        harga_baru = float(new_harga_jual)
                    except (TypeError, ValueError):
                        pass
            else:
                # Belum ada di PriceList -- tetep dibolehin, kodenya dibiarin
                # sama kayak sebelumnya (cuma nama/ukurannya yang diganti),
                # biar gak nge-block revisi admin cuma gara-gara produknya
                # belum sempet didaftarin ke katalog.
                item_baru = {
                    "found_in_catalog": False,
                    "new_item_code": code,
                    "new_nama": item_baru_text,
                    "new_satuan": cur_row.get("Satuan", ""),
                    "new_kategori": cur_row.get("Kategori", ""),
                }

        item_updates.append({
            "item_code": code,
            "nama": cur_row.get("Nama_Item", code),
            "satuan": cur_row.get("Satuan", ""),
            "qty_lama": cur_row.get("Qty", ""),
            "qty_baru": qty_baru,
            "harga_lama": cur_row.get("Harga_Satuan", ""),
            "harga_baru": harga_baru,
            "item_baru": item_baru,
        })

    if not updates and not item_updates:
        await update.effective_message.reply_text(
            "Gak nangkep bagian mana yang mau diganti (atau nilainya udah sama "
            "kayak yang kesimpen sekarang). Coba lebih jelas, misal: \"ganti "
            "nama customer jadi Grandia Hotel\" atau \"qty tulip jadi 25 pack\" "
            "atau \"revisi Plastik PE Susu Hippe 30x40 jadi 35x45\"."
        )
        return

    # Kalau yang diganti cuma data customer (no HP / alamat) dan user nyebut
    # NAMA customer (bukan nomor invoice), kemungkinan besar maksudnya data
    # customer-nya, bukan 1 invoice lama -- tawarin update permanen.
    customer_level = (
        bool(target) and not str(target).upper().startswith(config.INVOICE_PREFIX)
        and not item_updates and set(updates) <= {"no_hp", "alamat"}
    )
    nama_cust = (first.get("Nama_Customer", "") or "").strip()
    context.user_data["pending_edit"] = {
        "no_invoice": no_invoice, "updates": updates, "item_updates": item_updates,
        "customer_nama": nama_cust if customer_level else "",
    }
    if customer_level:
        lines = [f"*Mau diganti buat customer {nama_cust}:*", ""]
    else:
        lines = [f"*Mau diganti di {no_invoice}:*", ""]
    for k, v in updates.items():
        lama = first.get(_EDIT_FIELD_COLUMN[k], "") or "-"
        lines.append(f"• {_EDIT_FIELD_LABEL[k]}: {lama} → *{v}*")
    for iu in item_updates:
        ib = iu.get("item_baru")
        if ib:
            lines.append(f"• Barang: {iu['nama']} → *{ib['new_nama']}*")
            if not ib["found_in_catalog"]:
                lines.append(
                    "  ⚠️ _Produk ini belum ada di PriceList, kesimpen manual "
                    "(kode & satuan tetep kaya yang lama)_"
                )
        if iu["qty_baru"] is not None:
            lines.append(f"• Qty {iu['nama']}: {iu['qty_lama']} {iu['satuan']} → *{iu['qty_baru']} {ib['new_satuan'] if ib else iu['satuan']}*")
        if iu["harga_baru"] is not None:
            lines.append(
                f"• Harga satuan {iu['nama']} (order ini aja): "
                f"{rupiah(iu['harga_lama'])} → *{rupiah(iu['harga_baru'])}*"
            )
    if customer_level:
        lines += [
            "",
            f"👤 *Update Customer*: simpan permanen di data customer + invoice "
            f"{nama_cust} yang belum lunas, dan order baru otomatis pakai ini.",
            f"📄 *Cuma Invoice Ini*: cuma {no_invoice} yang berubah.",
        ]
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("👤 Update Customer", callback_data="custupdate_confirm")],
            [InlineKeyboardButton("📄 Cuma Invoice Ini", callback_data="editorder_confirm"),
             InlineKeyboardButton("❌ Batal", callback_data="editorder_cancel")],
        ])
    else:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Simpan Perubahan", callback_data="editorder_confirm"),
            InlineKeyboardButton("❌ Batal", callback_data="editorder_cancel"),
        ]])
    await _send_text(update, "\n".join(lines), reply_markup=kb)


async def _pilih_invoice(update, key, prefix, judul, hanya_pending=False):
    """Resolusi invoice dari nama customer. Balikin no_invoice kalau pasti
    (cuma 1), None kalau gak ada / lagi nampilin pilihan tombol (callback
    `<prefix>:<inv>`)."""
    invs = _sheets().find_customer_invoices(key)
    if hanya_pending:
        invs = [d for d in invs if d["status"] != "Lunas"]
    if not invs:
        await update.effective_message.reply_text(f"Gak ketemu invoice buat '{key}'.")
        return None
    if len(invs) == 1:
        return invs[0]["no_invoice"]
    rows = []
    for d in invs:
        icon = "✅" if d["status"] == "Lunas" else "⏳"
        rows.append([InlineKeyboardButton(f"{icon} {d['no_invoice']} • {d['tanggal']} • {rupiah(d['total'])}",
                                          callback_data=f"{prefix}:{d['no_invoice']}")])
    await update.effective_message.reply_text(
        f"{invs[0]['nama']} punya {len(invs)} invoice. {judul}  (✅ lunas, ⏳ belum lunas)",
        reply_markup=InlineKeyboardMarkup(rows))
    return None


async def _pilih_po(update, key, prefix, judul):
    pos = {}
    for r in _sheets().get_all_pos():
        if str(r.get("Status", "")) == "Batal":
            continue
        if key.lower() not in str(r.get("Nama_Supplier", "")).lower():
            continue
        d = pos.setdefault(str(r.get("No_PO", "")), {"tgl": str(r.get("Timestamp", ""))[:10], "total": 0.0,
                                                    "nama": r.get("Nama_Supplier", "")})
        try:
            d["total"] += float(r.get("Subtotal", 0) or 0)
        except (TypeError, ValueError):
            pass
    if not pos:
        await update.effective_message.reply_text(f"Gak ketemu PO buat '{key}'.")
        return None
    if len(pos) == 1:
        return next(iter(pos))
    items = sorted(pos.items(), key=lambda kv: kv[1]["tgl"], reverse=True)[:8]
    rows = [[InlineKeyboardButton(f"{no} • {d['tgl']} • {rupiah(d['total'])}", callback_data=f"{prefix}:{no}")]
            for no, d in items]
    await update.effective_message.reply_text(f"{items[0][1]['nama']} punya {len(pos)} PO. {judul}",
                                              reply_markup=InlineKeyboardMarkup(rows))
    return None


async def _do_cancel_order(update, context, target):
    sheets = _sheets()

    no_invoice = None
    if target and target.upper().startswith(config.INVOICE_PREFIX):
        no_invoice = target
    elif target:
        no_invoice = await _pilih_invoice(update, target, "cpick", "Pilih yang mau dibatalin:")
        if not no_invoice:
            return
    if not no_invoice:
        no_invoice = context.user_data.get("last_invoice")
    if not no_invoice:
        await update.effective_message.reply_text(
            "Order/invoice yang mana yang mau dibatalin? Sebutin nomor invoice-nya "
            "atau nama customernya."
        )
        return

    rows = sheets.get_order_items(no_invoice)
    if not rows:
        await update.effective_message.reply_text(f"Invoice {no_invoice} gak ketemu.")
        return
    if str(rows[0].get("Status", "")) == "Batal":
        await update.effective_message.reply_text(f"{no_invoice} udah dibatalin sebelumnya.")
        return

    total = 0.0
    for r in rows:
        try:
            total += float(r.get("Subtotal", 0) or 0)
        except ValueError:
            pass
    try:
        total += float(rows[0].get("Ongkir", 0) or 0)
    except ValueError:
        pass

    context.user_data["pending_cancel"] = no_invoice
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Ya, Batalin", callback_data="cancelorder_confirm"),
        InlineKeyboardButton("❌ Jangan Dulu", callback_data="cancelorder_cancel"),
    ]])
    await _send_text(
        update,
        f"Yakin mau batalin *{no_invoice}* ({rows[0].get('Nama_Customer', '-')}, "
        f"total {rupiah(total)})? Order ditandai *Batal* (datanya tetep ada buat "
        "histori, tapi otomatis keluar dari piutang).",
        reply_markup=kb,
    )


async def _do_cancel_po(update, context, target):
    sheets = _sheets()

    no_po = None
    if target and target.upper().startswith(config.PO_PREFIX):
        no_po = target
    elif target:
        no_po = await _pilih_po(update, target, "cpopick", "Pilih PO yang mau dibatalin:")
        if not no_po:
            return
    if not no_po:
        no_po = context.user_data.get("last_po")
    if not no_po:
        await update.effective_message.reply_text(
            "PO yang mana yang mau dibatalin? Sebutin nomor PO-nya atau nama supplier-nya."
        )
        return

    rows = sheets.get_po_items(no_po)
    if not rows:
        await update.effective_message.reply_text(f"PO {no_po} gak ketemu.")
        return
    if str(rows[0].get("Status", "")) == "Batal":
        await update.effective_message.reply_text(f"{no_po} udah dibatalin sebelumnya.")
        return

    total = 0.0
    for r in rows:
        try:
            total += float(r.get("Subtotal", 0) or 0)
        except ValueError:
            pass

    context.user_data["pending_cancel_po"] = no_po
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Ya, Batalin", callback_data="cancelpo_confirm"),
        InlineKeyboardButton("❌ Jangan Dulu", callback_data="cancelpo_cancel"),
    ]])
    await _send_text(
        update,
        f"Yakin mau batalin *{no_po}* ({rows[0].get('Nama_Supplier', '-')}, "
        f"total {rupiah(total)})? PO ditandai *Batal* (datanya tetep ada buat "
        "histori, tapi utang ke supplier ini otomatis dibalikin/dikurangin lagi).",
        reply_markup=kb,
    )


async def _present_price_update(update, context, parsed):
    """Dipake bareng sama chat teks & foto -- ubah hasil parse (list items
    harga_jual/harga_beli baru, + usulan barang baru yang belum ada di
    katalog) jadi preview + tombol konfirmasi."""
    sheets = _sheets()
    price_map = sheets.get_price_map()
    used_codes = set(price_map.keys())
    resolved = []
    new_items = []
    not_found = []
    for it in parsed.get("items", []):
        code = (it.get("item_code") or "").strip().upper()
        row = price_map.get(code) if code else None
        if row is None:
            row = sheets.find_product(it.get("nama_disebut", ""))
        if row is not None:
            harga_jual_baru = it.get("harga_jual") or 0
            harga_beli_baru = it.get("harga_beli") or 0
            nama_baru = (it.get("nama_baru") or "").strip()
            if nama_baru and nama_baru.strip().lower() == str(row.get("Nama", "")).strip().lower():
                nama_baru = ""  # sama persis kayak sekarang, bukan perubahan beneran
            if harga_jual_baru or harga_beli_baru or nama_baru:
                resolved.append({
                    "item_code": row["Item_Code"],
                    "nama": row["Nama"],
                    "harga_jual_lama": row.get("Harga_Jual", 0),
                    "harga_beli_lama": row.get("Harga_Beli", 0),
                    "harga_jual_baru": harga_jual_baru or None,
                    "harga_beli_baru": harga_beli_baru or None,
                    "nama_baru": nama_baru or None,
                })
            continue
        # Item ini gak ketemu di katalog -- kalau AI ngasih usulan kode/
        # kategori/satuan yang valid, tawarin sebagai PRODUK BARU (bukan
        # cuma dilewatin) supaya admin gak perlu input manual belakangan.
        nama_disebut = it.get("nama_disebut") or "?"
        kode_baru = (it.get("item_code_baru") or "").strip().upper()
        kategori_baru = (it.get("kategori_baru") or "").strip()
        satuan_baru = (it.get("satuan_baru") or "").strip()
        harga_beli_new = it.get("harga_beli") or 0
        if kode_baru and kategori_baru in config.CATEGORIES and satuan_baru in config.UNITS:
            final_kode = kode_baru
            suffix = 2
            while final_kode in used_codes:
                final_kode = f"{kode_baru}{suffix}"[:10]
                suffix += 1
            used_codes.add(final_kode)
            new_items.append({
                "item_code": final_kode,
                "nama": nama_disebut,
                "kategori": kategori_baru,
                "satuan": satuan_baru,
                "harga_beli": harga_beli_new,
            })
        else:
            not_found.append(nama_disebut)

    if not resolved and not new_items:
        msg = "Gak nemu perubahan harga atau barang baru yang jelas dari pesan/foto ini."
        if not_found:
            msg += " Barang yang gak ketemu di katalog: " + ", ".join(not_found) + "."
        if parsed.get("catatan"):
            msg += f"\n\n📝 {parsed['catatan']}"
        await update.effective_message.reply_text(msg)
        return

    nama_supplier = (parsed.get("nama_supplier") or "").strip()
    context.user_data["pending_price_update"] = {
        "items": resolved, "new_items": new_items, "nama_supplier": nama_supplier,
    }
    lines = []
    if nama_supplier:
        lines.append(f"*Dari daftar harga {nama_supplier}:*")
        lines.append("")
    if resolved:
        lines.append("*Mau diubah di PriceList:*")
        for r in resolved:
            if r.get("nama_baru"):
                lines.append(f"• ({r['item_code']}) Nama/ukuran: {r['nama']} → *{r['nama_baru']}*")
            if r["harga_jual_baru"]:
                lines.append(f"• {r['nama']} ({r['item_code']}) — harga jual: {rupiah(r['harga_jual_lama'])} → *{rupiah(r['harga_jual_baru'])}*")
            if r["harga_beli_baru"]:
                lines.append(f"• {r['nama']} ({r['item_code']}) — harga beli: {rupiah(r['harga_beli_lama'])} → *{rupiah(r['harga_beli_baru'])}*")
        lines.append("")
    if new_items:
        lines.append("*🆕 Barang baru yang bisa ditambahin ke katalog:*")
        for n in new_items:
            lines.append(
                f"• {n['nama']} — kode *{n['item_code']}*, {n['kategori']}/{n['satuan']}, "
                f"harga beli {rupiah(n['harga_beli'])}"
            )
        lines.append("")
        lines.append("_Harga jual barang baru default Rp0 dulu -- inget diisi manual abis ini kesimpen (\"harga <kode> jadi <angka>\")._")
    if not_found:
        lines.append("")
        lines.append("⚠️ Gak ketemu di katalog & gak ada usulan barang baru yang jelas, dilewatin: " + ", ".join(not_found))
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Simpan", callback_data="priceupdate_confirm"),
        InlineKeyboardButton("❌ Batal", callback_data="priceupdate_cancel"),
    ]])
    await _send_text(update, "\n".join(lines).strip(), reply_markup=kb)


async def _do_update_harga(update, context, text):
    sheets = _sheets()
    await update.effective_message.reply_chat_action("typing")
    try:
        parsed = parse_price_update(text, sheets.get_price_list())
    except Exception as e:
        logger.exception("gagal parse update harga")
        await update.effective_message.reply_text(f"Waduh, gagal baca perubahan harganya: {e}")
        return
    await _present_price_update(update, context, parsed)


async def _process_price_photo(update, context):
    sheets = _sheets()
    await update.effective_message.reply_chat_action("typing")
    photo = update.effective_message.photo[-1]
    file = await photo.get_file()
    image_bytes = bytes(await file.download_as_bytearray())
    caption = (update.effective_message.caption or "").strip()
    try:
        parsed = parse_price_update_image(image_bytes, "image/jpeg", sheets.get_price_list(), caption=caption)
    except Exception as e:
        logger.exception("gagal parse foto price list")
        await update.effective_message.reply_text(f"Waduh, gagal baca foto daftar harga ini: {e}")
        return
    await _present_price_update(update, context, parsed)


async def _process_order_photo(update, context):
    sheets = _sheets()
    await update.effective_message.reply_chat_action("typing")
    photo = update.effective_message.photo[-1]
    file = await photo.get_file()
    image_bytes = bytes(await file.download_as_bytearray())
    try:
        parsed = parse_order_image(image_bytes, "image/jpeg", sheets.get_price_list(), sheets.get_customer_names())
    except Exception as e:
        logger.exception("gagal parse order foto")
        await update.effective_message.reply_text(f"Waduh, gagal baca foto ini: {e}")
        return
    parsed["items"] = _resolve_items_with_price(parsed.get("items", []), sheets)
    _fill_customer_defaults(parsed, sheets)

    # Safety net: kalau AI gak nemu barang order sama sekali (misal fotonya
    # ternyata price list/dokumen lain, bukan order customer), JANGAN
    # tunjukin preview order kosong (Rp0) dengan tombol Simpan -- itu bikin
    # bingung dan kalau kepencet malah nyimpen order kosong ke Sheets. Kasih
    # tau langsung apa yang kebaca AI-nya, tanpa bikin pending_order.
    if not parsed.get("items"):
        msg = "Gak nemu barang order di foto ini."
        if parsed.get("catatan"):
            msg += f"\n\n📝 {parsed['catatan']}"
        msg += (
            "\n\nKalau ini sebenernya daftar harga dari supplier, kirim ulang "
            "fotonya dengan caption yang jelas, misal \"update harga beli dari "
            "foto ini\"."
        )
        await update.effective_message.reply_text(msg)
        return

    context.user_data["pending_order"] = parsed
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Simpan", callback_data="order_confirm"),
        InlineKeyboardButton("❌ Batal", callback_data="order_cancel"),
    ]])
    await _send_text(update, _order_preview_text(parsed), reply_markup=kb)


@owner_only
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _has_pending(context):
        await update.effective_message.reply_text(
            "Masih ada order/PO/perubahan yang nunggu konfirmasi. Klik tombolnya dulu, atau /batal buat batalin."
        )
        return

    # Kalau foto ini dikirim dengan CAPTION (keterangan) yang jelas maksudnya
    # bukan order (misal "update harga dari foto ini"), pakai itu buat
    # nebak maksud fotonya. Tanpa caption / caption gak jelas -> default
    # dianggap ORDER (paling aman, order customer gak boleh kelewat).
    caption = (update.effective_message.caption or "").strip()
    intent = "order"
    if caption:
        try:
            route = classify_intent(caption)
            intent = route.get("intent", "order")
        except Exception:
            logger.exception("gagal classify_intent dari caption foto, fallback ke order")
            intent = "order"

    if intent == "update_harga":
        await _process_price_photo(update, context)
        return

    await _process_order_photo(update, context)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("doc:"):
        try:
            _, kind, no_invoice = data.split(":", 2)
        except ValueError:
            return
        if kind not in _DOC_LABEL:
            return
        await query.edit_message_text(f"Oke, ngirim {_DOC_LABEL[kind]} {no_invoice}...")
        await _kirim_dokumen(update, context, no_invoice, kind)
        return

    if data.startswith(("cpick:", "cpopick:", "lpick:", "epick:")):
        kind, val = data.split(":", 1)
        await query.edit_message_text(f"Oke, {val} dipilih.")
        if kind == "epick":
            await _do_edit_order(update, context, val, context.user_data.pop("edit_text", ""))
        elif kind == "cpick":
            await _do_cancel_order(update, context, val)
        elif kind == "cpopick":
            await _do_cancel_po(update, context, val)
        else:
            await _ask_lunas(update, val)
        return

    if data == "lunasno":
        await query.edit_message_text("Oke, gak jadi ditandai lunas.")
        return
    if data.startswith("lunasok:"):
        inv = data.split(":", 1)[1]
        sheets = _sheets()
        rows = sheets.get_order_items(inv)
        if not rows or str(rows[0].get("Status", "")) != "Pending":
            await query.edit_message_text(f"{inv} udah gak Pending, gak diubah.")
            return
        total = sheets.mark_order_lunas(inv)
        sheets.add_kas_entry("Masuk", "Penjualan", total, keterangan=f"Pelunasan {inv}", ref=inv)
        await query.edit_message_text(f"✅ {inv} ditandai Lunas ({rupiah(total)}), udah dicatat ke Kas Masuk.")
        return

    if data.startswith("rm:"):
        await _handle_reminder_callback(update, context, data)
        return

    if data == "order_cancel":
        context.user_data.pop("pending_order", None)
        await query.edit_message_text("Order dibatalin.")
        return

    if data.startswith("wo_no:"):
        pid = data.split(":", 1)[1]
        sheets = _sheets()
        row = sheets.get_pesanan_web(pid)
        if not row or str(row.get("Status", "")) != "Menunggu":
            await query.edit_message_text(f"Order online {pid} udah diproses sebelumnya.")
            return
        sheets.set_pesanan_web_status(pid, "Ditolak")
        await query.edit_message_text(f"❌ Order online {pid} ditolak. Kabarin customernya via WA ya.")
        return

    if data.startswith("wo_ok:"):
        import json as _json
        pid = data.split(":", 1)[1]
        sheets = _sheets()
        row = sheets.get_pesanan_web(pid)
        if not row or str(row.get("Status", "")) != "Menunggu":
            await query.edit_message_text(f"Order online {pid} udah diproses sebelumnya.")
            return
        sheets.set_pesanan_web_status(pid, "Diproses")
        context.user_data["pending_order"] = _json.loads(row["Payload"])
        data = "order_confirm"

    if data == "order_confirm":
        parsed = context.user_data.pop("pending_order", None)
        if not parsed:
            await query.edit_message_text("Order-nya udah gak ada / kadaluarsa, coba kirim ulang.")
            return
        sheets = _sheets()
        no_invoice = sheets.add_order(
            parsed.get("nama_customer", "-"), parsed.get("no_hp", ""), parsed.get("alamat", ""),
            parsed.get("metode", "Kirim"), parsed["items"], ongkir=parsed.get("ongkir", 0) or 0,
            no_po_customer=parsed.get("no_po_customer", "") or "",
            tanggal_kirim=parsed.get("tanggal_kirim", "") or "",
            tanggal_order=_valid_tanggal_order(parsed.get("tanggal_order")),
        )
        context.user_data["last_invoice"] = no_invoice
        await query.edit_message_text(f"✅ Order disimpan sebagai *{no_invoice}*. Lagi bikin invoice & surat jalan...", parse_mode=ParseMode.MARKDOWN)
        try:
            rows = sheets.get_order_items(no_invoice)
            tot = sum(float(r.get("Subtotal", 0) or 0) for r in rows) + float(rows[0].get("Ongkir", 0) or 0)
            await _mirror(query.get_bot(), "order",
                          text=f"🛒 Order baru {no_invoice}\n{rows[0].get('Nama_Customer','')} • {len(rows)} item • {rupiah(tot)}")
        except Exception:
            logger.exception("gagal mirror order")
        await _kirim_invoice(update, context, no_invoice)
        await _kirim_surat_jalan(update, context, no_invoice)
        if parsed.get("_web"):
            try:
                img, kpdf = documents.generate_konfirmasi_pesanan(
                    no_invoice, parsed.get("nama_customer", ""), parsed.get("no_hp", ""), parsed.get("alamat", ""),
                    parsed["items"], parsed.get("ongkir", 0) or 0, parsed.get("tanggal_kirim", ""),
                    parsed.get("no_po_customer", ""), parsed.get("catatan", ""))
                await update.effective_chat.send_document(
                    document=kpdf, filename=f"Konfirmasi-{no_invoice}.pdf",
                    caption=f"Konfirmasi Pesanan {no_invoice} — print & kasih ke {parsed.get('nama_customer','')}")
            except Exception:
                logger.exception("gagal bikin konfirmasi pesanan")
        return

    if data == "editorder_cancel":
        context.user_data.pop("pending_edit", None)
        await query.edit_message_text("Gak jadi diedit.")
        return

    if data == "custupdate_confirm":
        pending = context.user_data.pop("pending_edit", None)
        if not pending or not pending.get("customer_nama"):
            await query.edit_message_text("Perubahannya udah gak ada / kadaluarsa, coba ulang.")
            return
        sheets = _sheets()
        nama = pending["customer_nama"]
        ups = pending.get("updates", {})
        n_inv = sheets.update_customer(nama, no_hp=ups.get("no_hp"), alamat=ups.get("alamat"))
        bagian = " & ".join(_EDIT_FIELD_LABEL[k] for k in ("no_hp", "alamat") if ups.get(k))
        await query.edit_message_text(
            f"✅ {bagian} {nama} udah diupdate di data customer"
            + (f" + {n_inv} invoice yang belum lunas." if n_inv else ".")
            + "\nOrder berikutnya otomatis pakai data baru ini."
        )
        return

    if data == "editorder_confirm":
        pending = context.user_data.pop("pending_edit", None)
        if not pending:
            await query.edit_message_text("Perubahannya udah gak ada / kadaluarsa, coba ulang.")
            return
        sheets = _sheets()
        no_invoice = pending["no_invoice"]
        found = bool(sheets.get_order_items(no_invoice))
        if not found:
            await query.edit_message_text(f"Invoice {no_invoice} gak ketemu lagi, mungkin udah berubah.")
            return
        if pending.get("updates"):
            sheets.edit_order_header(no_invoice, pending["updates"])
        for iu in pending.get("item_updates", []):
            ib = iu.get("item_baru")
            if ib:
                sheets.edit_order_item_product(
                    no_invoice, iu["item_code"],
                    new_item_code=ib.get("new_item_code"),
                    new_nama_item=ib.get("new_nama"),
                    new_kategori=ib.get("new_kategori"),
                    new_satuan=ib.get("new_satuan"),
                    qty_baru=iu.get("qty_baru"), harga_baru=iu.get("harga_baru"),
                )
            else:
                sheets.edit_order_item_qty(
                    no_invoice, iu["item_code"],
                    qty_baru=iu.get("qty_baru"), harga_baru=iu.get("harga_baru"),
                )
        context.user_data["last_invoice"] = no_invoice
        await query.edit_message_text(
            f"✅ {no_invoice} udah diupdate. Lagi bikin ulang invoice & surat jalan...",
            parse_mode=ParseMode.MARKDOWN,
        )
        await _kirim_invoice(update, context, no_invoice)
        await _kirim_surat_jalan(update, context, no_invoice)
        return

    if data == "cancelorder_cancel":
        context.user_data.pop("pending_cancel", None)
        await query.edit_message_text("Oke, gak jadi dibatalin.")
        return

    if data == "cancelorder_confirm":
        no_invoice = context.user_data.pop("pending_cancel", None)
        if not no_invoice:
            await query.edit_message_text("Udah gak ada order yang nunggu dibatalin, coba ulang.")
            return
        sheets = _sheets()
        ok = sheets.cancel_order(no_invoice)
        if not ok:
            await query.edit_message_text(f"Invoice {no_invoice} gak ketemu lagi.")
            return
        await query.edit_message_text(f"✅ {no_invoice} udah ditandai *Batal*.", parse_mode=ParseMode.MARKDOWN)
        return

    if data == "cancelpo_cancel":
        context.user_data.pop("pending_cancel_po", None)
        await query.edit_message_text("Oke, gak jadi dibatalin.")
        return

    if data == "cancelpo_confirm":
        no_po = context.user_data.pop("pending_cancel_po", None)
        if not no_po:
            await query.edit_message_text("Udah gak ada PO yang nunggu dibatalin, coba ulang.")
            return
        sheets = _sheets()
        ok, nama_supplier, total = sheets.cancel_po(no_po)
        if not ok:
            await query.edit_message_text(f"PO {no_po} gak ketemu lagi.")
            return
        await query.edit_message_text(
            f"✅ {no_po} udah ditandai *Batal*. Utang ke *{nama_supplier}* otomatis "
            f"dikurangin {rupiah(total)}.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if data == "priceupdate_cancel":
        context.user_data.pop("pending_price_update", None)
        await query.edit_message_text("Gak jadi diubah.")
        return

    if data == "priceupdate_confirm":
        pending = context.user_data.pop("pending_price_update", None)
        if not pending:
            await query.edit_message_text("Perubahannya udah gak ada / kadaluarsa, coba ulang.")
            return
        sheets = _sheets()
        items = pending.get("items", [])
        for r in items:
            if r.get("nama_baru"):
                sheets.rename_product(r["item_code"], new_nama=r["nama_baru"])
            if r.get("harga_jual_baru") or r.get("harga_beli_baru"):
                sheets.update_price(r["item_code"], harga_jual=r["harga_jual_baru"], harga_beli=r["harga_beli_baru"])

        new_items = pending.get("new_items", [])
        added, skipped = [], []
        for n in new_items:
            code = n["item_code"]
            ok = sheets.add_product(
                code, n["nama"], deskripsi="", kategori=n["kategori"], satuan=n["satuan"],
                harga_jual=0, harga_beli=n["harga_beli"],
            )
            if not ok:
                # Kode kebetulan udah kepake pas confirm (jarang -- misal ada
                # yang nambahin manual barengan) -- coba sekali lagi dengan
                # kode alternatif daripada diem-diem gak kesimpen.
                fallback_code = f"{code}X"[:10]
                ok = sheets.add_product(
                    fallback_code, n["nama"], deskripsi="", kategori=n["kategori"], satuan=n["satuan"],
                    harga_jual=0, harga_beli=n["harga_beli"],
                )
                code = fallback_code if ok else code
            (added if ok else skipped).append(f"{n['nama']} ({code})")

        nama_supplier = (pending.get("nama_supplier") or "").strip()
        if nama_supplier:
            sheets.add_supplier_if_new(nama_supplier)

        parts = []
        if items:
            ringkas = ", ".join(r["nama"] for r in items)
            parts.append(f"✅ Harga *{ringkas}* udah diupdate di PriceList.")
        if added:
            parts.append(f"🆕 Barang baru *{', '.join(added)}* udah ditambahin ke PriceList (harga jual masih Rp0, inget diisi manual).")
        if skipped:
            parts.append(f"⚠️ Gagal nambahin: {', '.join(skipped)} -- kode bentrok, tambahin manual.")
        if nama_supplier:
            parts.append(f"Supplier *{nama_supplier}* juga udah dicatat di tab Suppliers.")
        await query.edit_message_text("\n".join(parts), parse_mode=ParseMode.MARKDOWN)
        return

    if data == "po_cancel":
        context.user_data.pop("pending_po", None)
        await query.edit_message_text("PO dibatalin.")
        return

    if data == "po_confirm":
        parsed = context.user_data.pop("pending_po", None)
        if not parsed:
            await query.edit_message_text("PO-nya udah gak ada / kadaluarsa, coba /po lagi.")
            return
        sheets = _sheets()
        no_po, total = sheets.add_purchase_order(parsed.get("nama_supplier", "-"), parsed["items"])
        context.user_data["last_po"] = no_po
        await query.edit_message_text(
            f"✅ PO *{no_po}* disimpan ({rupiah(total)}), otomatis nambah utang ke supplier ini.",
            parse_mode=ParseMode.MARKDOWN,
        )
        img, pdf = documents.generate_po_image(no_po, parsed.get("nama_supplier", "-"), parsed["items"])
        await update.effective_chat.send_photo(photo=img, caption=f"Purchase Order {no_po}")
        await update.effective_chat.send_document(
            document=pdf, filename=f"{no_po}.pdf", caption="Versi PDF (siap print A4)"
        )
        await _mirror(query.get_bot(), "po", skip_chat=update.effective_chat.id, document=pdf,
                      filename=f"{no_po}.pdf", caption=f"Purchase Order {no_po} — {parsed.get('nama_supplier','-')} ({rupiah(total)})")
        return


# ---------------- PO FLOW ----------------

@owner_only
async def po_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting"] = "po_text"
    await update.effective_message.reply_text(
        "Oke, ketik detail belanjanya dalam 1 pesan. Contoh:\n\n"
        "\"PO ke CV Sumber Plastik Jaya: PP bening 40x60 100kg harga 28050, "
        "tulip putih 30 50kg harga 26000\"\n\n"
        "Boleh bahasa santai, nanti gua baca. Ketik /batal buat batalin."
    )


async def _process_po_text(update, context, text):
    await update.effective_message.reply_chat_action("typing")
    sheets = _sheets()
    try:
        parsed = parse_po_text(text, sheets.get_supplier_names(), sheets.get_price_list())
    except Exception as e:
        logger.exception("gagal parse PO")
        await update.effective_message.reply_text(f"Waduh, gagal baca PO ini: {e}")
        return
    parsed["items"] = _resolve_po_items_with_catalog(parsed.get("items", []), sheets)
    context.user_data["pending_po"] = parsed
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Simpan", callback_data="po_confirm"),
        InlineKeyboardButton("❌ Batal", callback_data="po_cancel"),
    ]])
    await _send_text(update, _po_preview_text(parsed), reply_markup=kb)


async def _try_fill_po_price(update, context, pending, text):
    """Kalau ada pending_po yang punya item harga masih 0, coba baca pesan
    susulan admin (mis. "harga 18870") sebagai jawaban buat ngisi harga itu.
    Balikin True kalau berhasil kepasangin & preview baru udah dikirim,
    False kalau pesan gak nyambung sama sekali (biar fallback ke pesan
    "masih ada pending" yang lama)."""
    items = pending.get("items", [])
    missing_idx = [i for i, it in enumerate(items) if not it.get("harga_satuan")]
    if not missing_idx:
        return False
    try:
        result = parse_po_price_fill(text, items)
    except Exception:
        logger.exception("gagal parse po price fill")
        return False
    updates = (result or {}).get("updates") or []
    applied = []
    for u in updates:
        idx = u.get("index")
        harga = u.get("harga_satuan")
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            continue
        if harga is None:
            continue
        try:
            harga = float(harga)
        except (TypeError, ValueError):
            continue
        if 0 <= idx < len(items) and harga > 0:
            items[idx]["harga_satuan"] = harga
            applied.append(items[idx].get("nama_item"))
    if not applied:
        return False
    context.user_data["pending_po"] = pending
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Simpan", callback_data="po_confirm"),
        InlineKeyboardButton("❌ Batal", callback_data="po_cancel"),
    ]])
    await _send_text(
        update,
        f"Oke, harga *{', '.join(applied)}* udah keisi.\n\n" + _po_preview_text(pending),
        reply_markup=kb,
    )
    return True


def _pending_order_desc(parsed):
    items_desc = "\n".join(
        f"  {i}. {it.get('nama_item', '')} | qty {it.get('qty', '')} {it.get('satuan', '')} "
        f"| harga satuan Rp{it.get('harga_satuan', 0)}"
        for i, it in enumerate(parsed.get("items", []))
    )
    return (
        f"Nama Customer: {parsed.get('nama_customer', '')}\n"
        f"No HP: {parsed.get('no_hp', '')}\n"
        f"Alamat: {parsed.get('alamat', '')}\n"
        f"Metode: {parsed.get('metode', '')}\n"
        f"No. PO Customer: {parsed.get('no_po_customer', '')}\n"
        f"Tanggal Kirim: {parsed.get('tanggal_kirim', '')}\n"
        f"Tanggal Order: {parsed.get('tanggal_order', '') or '(hari ini)'}\n"
        f"Ongkir: {parsed.get('ongkir', 0)}\n"
        f"ITEM DI ORDER INI:\n{items_desc}"
    )


async def _try_correct_pending_order(update, context, pending, text):
    """Kalau ada pending_order yang lagi nunggu konfirmasi (BELUM di-Simpan),
    coba baca pesan susulan admin sebagai KOREKSI ke preview ini -- misal
    ganti alamat/qty/harga/tanggal kirim -- sebelum dikonfirmasi. Balikin
    True kalau berhasil match & preview baru udah dikirim, False kalau
    pesan gak nyambung sama sekali (biar fallback ke pesan pending generik
    yang lama)."""
    try:
        corr = parse_pending_order_correction(text, _pending_order_desc(pending))
    except Exception:
        logger.exception("gagal parse koreksi pending order")
        return False
    if not corr.get("matched"):
        return False

    changed = []
    header_updates = corr.get("header_updates") or {}
    for field in ("nama_customer", "no_hp", "alamat", "metode", "no_po_customer", "tanggal_kirim", "tanggal_order"):
        val = (header_updates.get(field) or "").strip()
        if field == "tanggal_order":
            val = _valid_tanggal_order(val)
        if val:
            pending[field] = val
            changed.append(_EDIT_FIELD_LABEL.get(field, field))
    try:
        ongkir_baru = float(header_updates.get("ongkir"))
    except (TypeError, ValueError):
        ongkir_baru = -1
    if ongkir_baru >= 0:
        pending["ongkir"] = ongkir_baru
        changed.append("Ongkir")

    items = pending.get("items", [])
    sheets = _sheets()
    for iu in corr.get("item_updates") or []:
        try:
            idx = int(iu.get("index"))
        except (TypeError, ValueError):
            continue
        if not (0 <= idx < len(items)):
            continue
        item_baru_text = (iu.get("item_baru") or "").strip()
        if item_baru_text:
            nama_lama = items[idx].get("nama_item", "")
            prod = sheets.find_product(item_baru_text)
            if prod:
                items[idx]["item_code"] = str(prod.get("Item_Code", "")).strip()
                items[idx]["nama_item"] = _item_label(prod) or item_baru_text
                items[idx]["kategori"] = prod.get("Kategori", "") or items[idx].get("kategori", "")
                items[idx]["satuan"] = prod.get("Satuan", "") or items[idx].get("satuan", "")
                if iu.get("harga_satuan") is None:
                    harga_jual_baru = prod.get("Harga_Jual") or None
                    if harga_jual_baru:
                        try:
                            items[idx]["harga_satuan"] = float(harga_jual_baru)
                        except (TypeError, ValueError):
                            pass
            else:
                # Belum ada di PriceList -- tetep dibolehin ganti nama/ukurannya
                # aja, kode & satuan dibiarin kaya sebelumnya biar gak nge-block.
                items[idx]["item_code"] = ""
                items[idx]["nama_item"] = item_baru_text
            changed.append(f"Barang {nama_lama} → {items[idx]['nama_item']}")
        if iu.get("qty") is not None:
            try:
                items[idx]["qty"] = float(iu["qty"])
                changed.append(f"Qty {items[idx].get('nama_item', '')}")
            except (TypeError, ValueError):
                pass
        if iu.get("harga_satuan") is not None:
            try:
                items[idx]["harga_satuan"] = float(iu["harga_satuan"])
                changed.append(f"Harga {items[idx].get('nama_item', '')}")
            except (TypeError, ValueError):
                pass

    if not changed:
        return False

    context.user_data["pending_order"] = pending
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Simpan", callback_data="order_confirm"),
        InlineKeyboardButton("❌ Batal", callback_data="order_cancel"),
    ]])
    await _send_text(
        update,
        f"Oke, *{', '.join(changed)}* udah diupdate.\n\n" + _order_preview_text(pending),
        reply_markup=kb,
    )
    return True


# ---------------- MAIN ----------------

# ---------------- PENGINGAT (kontra bon / tagihan / bayar supplier) ----------------

def _wib_now():
    import datetime
    return datetime.datetime.utcnow() + datetime.timedelta(hours=7)


_REM_LABEL = {
    "kontra_bon": "📋 KONTRA BON",
    "bayar_customer": "💰 CEK PEMBAYARAN CUSTOMER",
    "bayar_supplier": "💸 WAKTUNYA BAYAR SUPPLIER",
}


def _reminder_message(rem):
    """Teks + tombol pengingat. Teks polos (tanpa Markdown) biar nama yang
    ada simbolnya gak bikin error."""
    import sheets_client as sc
    jenis, rid = rem.get("Jenis", ""), rem.get("ID", "")
    nama, ref = rem.get("Nama", ""), rem.get("Ref", "")
    jumlah = rem.get("Jumlah", 0)
    tgl = str(rem.get("Tanggal", ""))
    try:
        jadwal = f"{sc.hari_dari_tanggal(tgl)}, {sc.tgl_dmy(tgl)}"
    except ValueError:
        jadwal = tgl
    if jenis == "kontra_bon":
        text = (f"{_REM_LABEL[jenis]}\n\nCustomer: {nama}\nInvoice: {ref} • {rupiah(jumlah)}\n"
                f"Jadwal kontra bon: {jadwal}\n\nUdah di-kontra bon belum?")
        kb = [[InlineKeyboardButton("✅ Sudah kontra bon", callback_data=f"rm:{rid}:kbok"),
               InlineKeyboardButton("⏳ Belum", callback_data=f"rm:{rid}:kbno")]]
    elif jenis == "bayar_customer":
        text = (f"{_REM_LABEL[jenis]}\n\nCustomer: {nama}\nInvoice: {ref} • {rupiah(jumlah)}\n"
                f"Jadwal cek: {jadwal}\n\nUdah bayar belum?")
        kb = [[InlineKeyboardButton("✅ Sudah bayar (Lunas)", callback_data=f"rm:{rid}:payok"),
               InlineKeyboardButton("⏳ Belum", callback_data=f"rm:{rid}:payno")]]
    else:
        text = (f"{_REM_LABEL['bayar_supplier']}\n\nSupplier: {nama}\nPO: {ref} • {rupiah(jumlah)}\n"
                f"Jatuh tempo: {jadwal}\n\nUdah dibayar belum?")
        kb = [[InlineKeyboardButton("✅ Sudah dibayar", callback_data=f"rm:{rid}:supok"),
               InlineKeyboardButton("⏳ Belum", callback_data=f"rm:{rid}:supno")]]
    return text, InlineKeyboardMarkup(kb)


async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    """Dipanggil tiap 10 menit. Kirim pengingat yang udah jatuh tempo, sekali
    per hari per pengingat, mulai jam REMINDER_HOUR WIB. Datanya disimpen di
    tab Pengingat (Google Sheets), jadi aman walau bot direstart."""
    now = _wib_now()
    if now.hour < config.REMINDER_HOUR:
        return
    today = now.strftime("%Y-%m-%d")
    try:
        sheets = _sheets()
        due = sheets.get_due_reminders(today)
    except Exception:
        logger.exception("gagal baca pengingat")
        return
    chat_ids = [c for c in config.OWNER_TELEGRAM_IDS if c]
    groups, singles = {}, []
    for rem in due:
        if rem.get("Jenis") == "kontra_bon":
            groups.setdefault(rem.get("Nama", ""), []).append(rem)
        else:
            singles.append([rem])
    batches = singles + list(groups.values())
    for batch in batches:
        rem = batch[0]
        text, kb = _kb_list_message(batch) if len(batch) > 1 else _reminder_message(rem)
        sent = False
        for chat_id in chat_ids:
            try:
                await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb)
                sent = True
            except Exception:
                logger.exception("gagal kirim pengingat ke %s", chat_id)
        await _mirror(context.bot, "pengingat", text=text, reply_markup=kb)
        if sent:
            try:
                for r in batch:
                    sheets.update_reminder(r["ID"], Terkirim_Tgl=today)
            except Exception:
                logger.exception("gagal nandain pengingat terkirim")


def _kb_list_message(rems):
    """Banyak invoice kontra bon 1 customer: pilih satuan atau semua."""
    rems = rems[:6]
    nama = rems[0].get("Nama", "")
    lines = [f"📋 KONTRA BON — {nama}", ""]
    kb = []
    for r in rems:
        lines.append(f"• {r.get('Ref','')} • {rupiah(r.get('Jumlah',0))}")
        kb.append([InlineKeyboardButton(f"✅ {r.get('Ref','')}", callback_data=f"rm:{r['ID']}:kbm")])
    ids = ",".join(r["ID"] for r in rems)
    kb.append([InlineKeyboardButton("✅ Kontra bon semua", callback_data=f"rm:{ids}:kball"),
               InlineKeyboardButton("⏳ Belum semua", callback_data=f"rm:{ids}:kbnoall")])
    lines += ["", "Pilih invoice yang udah di-kontra bon (atau semua):"]
    return "\n".join(lines), InlineKeyboardMarkup(kb)


def _kontrabon_done(sheets, rem):
    import datetime
    nama, ref, jumlah = rem.get("Nama", ""), rem.get("Ref", ""), rem.get("Jumlah", 0)
    today = _wib_now().date()
    sheets.update_reminder(rem["ID"], Status="Selesai")
    tempo = sheets.get_tempo(nama, "customer")
    due = today + datetime.timedelta(days=tempo)
    sheets.add_reminder("bayar_customer", ref, nama, jumlah, due, "Cek pembayaran setelah kontra bon")
    return tempo, due


async def _handle_kb_multi(update, context, data):
    import datetime
    import sheets_client as sc
    query = update.callback_query
    _, ids, act = data.split(":", 2)
    sheets = _sheets()
    today = _wib_now().date()
    rems = [r for r in (sheets.get_reminder(i) for i in ids.split(",")) if r and str(r.get("Status", "")) == "Aktif"]
    if not rems:
        await query.edit_message_text("Pengingat ini udah ditangani.")
        return
    if act == "kbnoall":
        for r in rems:
            sheets.update_reminder(r["ID"], Tanggal=today + datetime.timedelta(days=1))
        await query.edit_message_text(f"⏳ Oke. {rems[0].get('Nama','')} gua ingetin lagi besok jam {config.REMINDER_HOUR:02d}.00.")
        return
    if act == "kball":
        done = []
        for r in rems:
            tempo, due = _kontrabon_done(sheets, r)
            done.append(r.get("Ref", ""))
        await query.edit_message_text(
            f"✅ Kontra bon {rems[0].get('Nama','')} tercatat ({len(done)} invoice):\n" + "\n".join(done) +
            f"\nCek pembayaran {tempo} hari lagi: {sc.hari_dari_tanggal(due)}, {sc.tgl_dmy(due)}.")
        return


async def _handle_reminder_callback(update, context, data):
    import datetime
    import sheets_client as sc
    query = update.callback_query
    try:
        _, rid, act = data.split(":", 2)
    except ValueError:
        return
    if act in ("kball", "kbnoall"):
        await _handle_kb_multi(update, context, data)
        return
    sheets = _sheets()
    rem = sheets.get_reminder(rid)
    if not rem or str(rem.get("Status", "")) != "Aktif":
        await query.edit_message_text("Pengingat ini udah ditangani / udah gak aktif.")
        return
    nama, ref, jumlah = rem.get("Nama", ""), rem.get("Ref", ""), rem.get("Jumlah", 0)
    today = _wib_now().date()
    besok = today + datetime.timedelta(days=1)

    if act in ("kbno", "payno", "supno"):
        sheets.update_reminder(rid, Tanggal=besok)
        await query.edit_message_text(f"⏳ Oke. {nama} ({ref}) gua ingetin lagi besok jam {config.REMINDER_HOUR:02d}.00.")
        return

    if act in ("kbok", "kbm"):
        tempo, due = _kontrabon_done(sheets, rem)
        msg = (f"✅ Kontra bon {nama} ({ref}) tercatat.\n"
               f"Gua ingetin cek pembayaran {tempo} hari lagi: {sc.hari_dari_tanggal(due)}, {sc.tgl_dmy(due)}.")
        if act == "kbm":
            sisa = [r for r in sheets.get_active_reminders()
                    if r.get("Jenis") == "kontra_bon" and r.get("Nama") == nama]
            if sisa:
                text, kb = _kb_list_message(sisa)
                await query.edit_message_text(msg + "\n\n" + text, reply_markup=kb)
                return
        await query.edit_message_text(msg)
        return

    if act == "payok":
        rows = sheets.get_order_items(ref)
        status = str(rows[0].get("Status", "")) if rows else ""
        if not rows or status in ("Lunas", "Batal"):
            sheets.close_reminders_for_ref(ref, "Selesai" if status == "Lunas" else "Batal")
            await query.edit_message_text(f"{ref} udah {status or 'gak ketemu'}, pengingatnya ditutup.")
            return
        total = sheets.mark_order_lunas(ref)
        sheets.add_kas_entry("Masuk", "Penjualan", total, keterangan=f"Pelunasan {ref}", ref=ref)
        await query.edit_message_text(f"✅ {ref} ({nama}) ditandai Lunas {rupiah(total)}, udah dicatat ke Kas Masuk.")
        return

    if act == "supok":
        rows = sheets.get_po_items(ref)
        status = str(rows[0].get("Status", "")) if rows else ""
        if not rows or status in ("Lunas", "Batal"):
            sheets.close_reminders_for_ref(ref, "Selesai" if status == "Lunas" else "Batal")
            await query.edit_message_text(f"{ref} udah {status or 'gak ketemu'}, pengingatnya ditutup.")
            return
        total = sum(float(r.get("Subtotal", 0) or 0) for r in rows)
        sisa = sheets.bayar_utang(nama, total, f"Pelunasan {ref}")
        sheets.add_kas_entry("Keluar", "Bayar Supplier", total, keterangan=f"Bayar utang {nama} {ref}", ref=ref)
        sheets.mark_po_lunas(ref)
        sisa_text = rupiah(sisa) if sisa > 0 else "Rp0"
        await query.edit_message_text(
            f"✅ {ref} ke {nama} ({rupiah(total)}) ditandai lunas, udah dicatat ke Kas Keluar.\n"
            f"Sisa utang ke {nama}: {sisa_text}"
        )
        return


@owner_only
async def pengingat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/pengingat = daftar pengingat yang aktif. /pengingat sync = bikinin
    pengingat buat invoice/PO lama yang belum lunas tapi belum punya."""
    import sheets_client as sc
    sheets = _sheets()
    if context.args and context.args[0].lower() == "sync":
        n_inv, n_po = sheets.backfill_reminders()
        await update.effective_message.reply_text(
            f"✅ Selesai: {n_inv} pengingat invoice & {n_po} pengingat PO baru dibuat "
            f"(buat yang belum lunas & belum punya pengingat)."
        )
        return
    rems = sheets.get_active_reminders()
    if not rems:
        await update.effective_message.reply_text(
            "Belum ada pengingat aktif. Pengingat otomatis dibuat tiap invoice/PO baru.\n"
            "Mau bikinin buat invoice & PO lama yang belum lunas? Ketik: /pengingat sync"
        )
        return
    label = {"kontra_bon": "Kontra bon", "bayar_customer": "Cek bayar", "bayar_supplier": "Bayar supplier"}
    lines = [f"*Pengingat aktif ({len(rems)}):*", ""]
    for r in rems[:30]:
        tgl = str(r.get("Tanggal", ""))
        try:
            when = f"{sc.hari_dari_tanggal(tgl)[:3]} {sc.tgl_dmy(tgl)}"
        except ValueError:
            when = tgl
        lines.append(f"• {when} — {label.get(r.get('Jenis'), r.get('Jenis'))}: {r.get('Nama')} ({r.get('Ref')}) {rupiah(r.get('Jumlah', 0))}")
    if len(rems) > 30:
        lines.append(f"... dan {len(rems) - 30} lainnya")
    lines.append("")
    lines.append(f"Pengingat dikirim tiap hari jam {config.REMINDER_HOUR:02d}.00 WIB. Hari kontra bon & tempo bayar bisa diedit di tab PengaturanTagihan (Google Sheets).")
    await _send_text(update, "\n".join(lines))


async def _notify_web_order(app, pid, parsed):
    """Order dari halaman web customer -> preview + tombol di Telegram admin."""
    text = "🌐 ORDER ONLINE (" + pid + ")\n\n" + _order_preview_text(parsed).replace("*", "")
    if parsed.get("catatan"):
        text += f"\n📝 Catatan: {parsed['catatan']}"
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Simpan & buat dokumen", callback_data=f"wo_ok:{pid}"),
                                InlineKeyboardButton("❌ Tolak", callback_data=f"wo_no:{pid}")]])
    for chat_id in [c for c in config.OWNER_TELEGRAM_IDS if c]:
        try:
            await app.bot.send_message(chat_id=chat_id, text=text, reply_markup=kb)
        except Exception:
            logger.exception("gagal kirim order web ke %s", chat_id)
    await _mirror(app.bot, "order", text=text, reply_markup=kb)


@owner_only
async def importgrandia_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from data_grandia import PRODUK_GRANDIA
    n, skip = _sheets().add_products_bulk(PRODUK_GRANDIA)
    await update.effective_message.reply_text(
        f"✅ {n} produk kantong sampah Tulip masuk ke PriceList (khusus Grandia)"
        + (f", {skip} dilewat karena kodenya udah ada." if skip else "."))


@owner_only
async def linkorder_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nama = " ".join(context.args).strip() if context.args else ""
    if not nama:
        await update.effective_message.reply_text("Format: /linkorder Grandia")
        return
    sheets = _sheets()
    cust = sheets.get_customer(nama)
    if not cust:
        norm = lambda x: "".join(str(x).lower().split())
        cands = [c for c in sheets.get_customer_names() if norm(nama) in norm(c)]
        if len(cands) == 1:
            nama = cands[0]
        elif not cands:
            await update.effective_message.reply_text(
                f"Customer '{nama}' belum ada di sheet Customers. Bikin dulu (kirim 1 order atas namanya) lalu ulangi.")
            return
        else:
            await update.effective_message.reply_text("Ada beberapa yang mirip: " + ", ".join(cands) + ". Tulis nama lengkapnya.")
            return
    token = sheets.get_or_create_link(nama)
    if not config.PUBLIC_BASE_URL:
        await update.effective_message.reply_text(
            "Link-nya udah dibikin, tapi alamat publik bot belum aktif. Nyalain Public Domain di Railway "
            "(Settings → Networking → Generate Domain), lalu ketik /linkorder lagi.")
        return
    await update.effective_message.reply_text(
        f"🔗 Link order {nama}:\n{config.PUBLIC_BASE_URL}/order/{token}\n\n"
        "Kirim link ini ke dia. Order yang masuk muncul di Telegram buat lu konfirmasi.")


async def on_startup(app: Application):
    # panggil sekali biar SheetsClient nyiapin skema tab kalau belum ada
    _sheets()
    try:
        import webapp
        app.bot_data["web_runner"] = await webapp.start_web(
            _sheets, lambda pid, parsed: _notify_web_order(app, pid, parsed))
    except Exception:
        logger.exception("web order gagal jalan (bot Telegram tetap jalan)")
    logger.info("Asisten Plastik siap jalan.")


def main():
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN belum diisi di environment variables.")

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).post_init(on_startup).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("groupid", groupid_cmd))
    app.add_handler(CommandHandler("pricelist", pricelist_cmd))
    app.add_handler(CommandHandler("topik", topik_cmd))
    app.add_handler(CommandHandler("linkorder", linkorder_cmd))
    app.add_handler(CommandHandler("importgrandia", importgrandia_cmd))
    app.add_error_handler(error_handler)
    app.add_handler(CommandHandler("lunas", lunas_cmd))
    app.add_handler(CommandHandler("batallunas", batallunas_cmd))
    app.add_handler(CommandHandler("invoice", invoice_cmd))
    app.add_handler(CommandHandler("suratjalan", suratjalan_cmd))
    app.add_handler(CommandHandler("dokumen", dokumen_cmd))
    app.add_handler(CommandHandler("piutang", piutang_cmd))
    app.add_handler(CommandHandler("po", po_cmd))
    app.add_handler(CommandHandler("bayarutang", bayarutang_cmd))
    app.add_handler(CommandHandler("utang", utang_cmd))
    app.add_handler(CommandHandler("kas", kas_cmd))
    app.add_handler(CommandHandler("laporanbulanan", laporanbulanan_cmd))
    app.add_handler(CommandHandler("batal", batal_cmd))
    app.add_handler(CommandHandler("pengingat", pengingat_cmd))

    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    if app.job_queue is None:
        logger.error("JobQueue gak aktif -- pengingat gak jalan. Pastikan requirements pakai python-telegram-bot[job-queue].")
    else:
        app.job_queue.run_repeating(reminder_job, interval=600, first=45)
        app.job_queue.run_repeating(rekap_job, interval=3600, first=120)

    logger.info("Starting polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
