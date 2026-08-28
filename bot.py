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
from ai_parser import parse_order_text, parse_order_image, parse_po_text, classify_intent
from sheets_client import get_sheets_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
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


async def _send_text(update, text, reply_markup=None):
    await update.effective_message.reply_text(
        text, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup
    )


# ---------------- PREVIEW TEXT ----------------

def _order_preview_text(parsed):
    lines = ["*Hasil baca order:*", ""]
    lines.append(f"Customer: *{parsed.get('nama_customer', '-')}*")
    if parsed.get("no_hp"):
        lines.append(f"HP: {parsed['no_hp']}")
    if parsed.get("alamat"):
        lines.append(f"Alamat: {parsed['alamat']}")
    lines.append(f"Metode: {parsed.get('metode', 'Kirim')}")
    lines.append("")
    total = 0
    for it in parsed.get("items", []):
        harga = it.get("harga_satuan", 0)
        subtotal = float(it.get("qty", 0)) * float(harga or 0)
        total += subtotal
        flag = "" if it.get("item_code") else " ⚠️ *(produk gak ketemu di katalog, cek lagi)*"
        lines.append(f"• {it.get('nama_item')} x{it.get('qty')} {it.get('satuan', '')} = {rupiah(subtotal)}{flag}")
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
        lines.append(f"• {it.get('nama_item')} x{it.get('qty')} {it.get('satuan', '')} @ {rupiah(harga)} = {rupiah(subtotal)}")
    lines.append("")
    lines.append(f"*Total belanja: {rupiah(total)}*")
    if parsed.get("catatan"):
        lines.append("")
        lines.append(f"📝 Catatan AI: {parsed['catatan']}")
    return "\n".join(lines)


def _resolve_items_with_price(parsed_items, sheets):
    """Isi ulang item yang item_code-nya kosong dengan hasil find_product,
    dan pastikan harga_satuan selalu ambil dari PriceList (bukan tebakan
    AI) supaya harga selalu akurat."""
    resolved = []
    for it in parsed_items:
        code = (it.get("item_code") or "").strip()
        row = None
        if code:
            row = sheets.get_price_map().get(code.upper())
        if row is None:
            row = sheets.find_product(it.get("nama_item", ""))
        if row is not None:
            resolved.append({
                "item_code": row["Item_Code"],
                "nama_item": row["Nama"],
                "kategori": row.get("Kategori", ""),
                "satuan": row.get("Satuan", it.get("satuan", "")),
                "harga_satuan": row.get("Harga_Jual", 0),
                "qty": it.get("qty", 0),
            })
        else:
            resolved.append({
                "item_code": "",
                "nama_item": it.get("nama_item", "?"),
                "kategori": "",
                "satuan": it.get("satuan", ""),
                "harga_satuan": 0,
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
sendiri. Command di bawah ini cadangan aja kalau mau lebih pasti/cepat:
/pricelist — lihat daftar harga produk
/invoice <no invoice atau nama customer> — cetak ulang invoice
/suratjalan <no invoice atau nama customer> — cetak ulang surat jalan
/lunas <no invoice atau nama customer> — tandai order sudah dibayar
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


@owner_only
async def lunas_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _do_lunas(update, " ".join(context.args) if context.args else "")


async def _do_invoice_lookup(update, context, key):
    if not key:
        await update.effective_message.reply_text("Invoice/customer mana yang mau dicetak ulang?")
        return
    sheets = _sheets()
    no_invoice = key if key.upper().startswith(config.INVOICE_PREFIX) else sheets.get_latest_invoice_for_customer(key)
    if not no_invoice:
        await update.effective_message.reply_text(f"Gak ketemu order buat '{key}'.")
        return
    await _kirim_invoice(update, context, no_invoice)


@owner_only
async def invoice_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _do_invoice_lookup(update, context, " ".join(context.args) if context.args else "")


async def _do_suratjalan_lookup(update, context, key):
    if not key:
        await update.effective_message.reply_text("Invoice/customer mana yang mau dicetak ulang surat jalannya?")
        return
    sheets = _sheets()
    no_invoice = key if key.upper().startswith(config.INVOICE_PREFIX) else sheets.get_latest_invoice_for_customer(key)
    if not no_invoice:
        await update.effective_message.reply_text(f"Gak ketemu order buat '{key}'.")
        return
    await _kirim_surat_jalan(update, context, no_invoice)


@owner_only
async def suratjalan_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _do_suratjalan_lookup(update, context, " ".join(context.args) if context.args else "")


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
    img = documents.generate_invoice_image(
        no_invoice, first["Nama_Customer"], first.get("No_HP", ""), first.get("Alamat", ""),
        first.get("Metode", "Kirim"), items, ongkir,
    )
    await update.effective_message.reply_photo(photo=img, caption=f"Invoice {no_invoice}")


async def _kirim_surat_jalan(update, context, no_invoice):
    sheets = _sheets()
    rows = sheets.get_order_items(no_invoice)
    if not rows:
        await update.effective_message.reply_text(f"Invoice {no_invoice} gak ketemu.")
        return
    first = rows[0]
    items = [{"nama_item": r["Nama_Item"], "qty": r["Qty"], "satuan": r["Satuan"]} for r in rows]
    no_sj = no_invoice.replace(config.INVOICE_PREFIX, config.SURAT_JALAN_PREFIX, 1)
    img = documents.generate_surat_jalan_image(
        no_sj, first["Nama_Customer"], first.get("No_HP", ""), first.get("Alamat", ""),
        first.get("Metode", "Kirim"), items, no_invoice_ref=no_invoice,
    )
    await update.effective_message.reply_photo(photo=img, caption=f"Surat Jalan {no_sj}")


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


async def _do_laporanbulanan(update, year, month):
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
    await _send_text(update, "\n".join(lines))


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

    if context.user_data.get("pending_order") or context.user_data.get("pending_po"):
        await update.effective_message.reply_text(
            "Masih ada order/PO yang nunggu konfirmasi di atas. Klik tombolnya dulu, atau /batal buat batalin."
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
    elif intent == "mark_lunas":
        await _do_lunas(update, target)
    elif intent == "bayar_utang":
        await _do_bayarutang(update, target, float(jumlah) if jumlah else 0)
    elif intent == "lihat_invoice":
        await _do_invoice_lookup(update, context, target)
    elif intent == "lihat_suratjalan":
        await _do_suratjalan_lookup(update, context, target)
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
    context.user_data["pending_order"] = parsed
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Simpan", callback_data="order_confirm"),
        InlineKeyboardButton("❌ Batal", callback_data="order_cancel"),
    ]])
    await _send_text(update, _order_preview_text(parsed), reply_markup=kb)


@owner_only
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("pending_order") or context.user_data.get("pending_po"):
        await update.effective_message.reply_text(
            "Masih ada order/PO yang nunggu konfirmasi. Klik tombolnya dulu, atau /batal buat batalin."
        )
        return
    await update.effective_message.reply_chat_action("typing")
    photo = update.effective_message.photo[-1]
    file = await photo.get_file()
    image_bytes = bytes(await file.download_as_bytearray())
    sheets = _sheets()
    try:
        parsed = parse_order_image(image_bytes, "image/jpeg", sheets.get_price_list(), sheets.get_customer_names())
    except Exception as e:
        logger.exception("gagal parse order foto")
        await update.effective_message.reply_text(f"Waduh, gagal baca foto ini: {e}")
        return
    parsed["items"] = _resolve_items_with_price(parsed.get("items", []), sheets)
    context.user_data["pending_order"] = parsed
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Simpan", callback_data="order_confirm"),
        InlineKeyboardButton("❌ Batal", callback_data="order_cancel"),
    ]])
    await _send_text(update, _order_preview_text(parsed), reply_markup=kb)


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "order_cancel":
        context.user_data.pop("pending_order", None)
        await query.edit_message_text("Order dibatalin.")
        return

    if data == "order_confirm":
        parsed = context.user_data.pop("pending_order", None)
        if not parsed:
            await query.edit_message_text("Order-nya udah gak ada / kadaluarsa, coba kirim ulang.")
            return
        sheets = _sheets()
        no_invoice = sheets.add_order(
            parsed.get("nama_customer", "-"), parsed.get("no_hp", ""), parsed.get("alamat", ""),
            parsed.get("metode", "Kirim"), parsed["items"], ongkir=parsed.get("ongkir", 0) or 0,
        )
        await query.edit_message_text(f"✅ Order disimpan sebagai *{no_invoice}*. Lagi bikin invoice & surat jalan...", parse_mode=ParseMode.MARKDOWN)
        await _kirim_invoice(update, context, no_invoice)
        await _kirim_surat_jalan(update, context, no_invoice)
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
        await query.edit_message_text(
            f"✅ PO *{no_po}* disimpan ({rupiah(total)}), otomatis nambah utang ke supplier ini.",
            parse_mode=ParseMode.MARKDOWN,
        )
        img = documents.generate_po_image(no_po, parsed.get("nama_supplier", "-"), parsed["items"])
        await update.effective_chat.send_photo(photo=img, caption=f"Purchase Order {no_po}")
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
        parsed = parse_po_text(text, sheets.get_supplier_names())
    except Exception as e:
        logger.exception("gagal parse PO")
        await update.effective_message.reply_text(f"Waduh, gagal baca PO ini: {e}")
        return
    context.user_data["pending_po"] = parsed
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Simpan", callback_data="po_confirm"),
        InlineKeyboardButton("❌ Batal", callback_data="po_cancel"),
    ]])
    await _send_text(update, _po_preview_text(parsed), reply_markup=kb)


# ---------------- MAIN ----------------

async def on_startup(app: Application):
    # panggil sekali biar SheetsClient nyiapin skema tab kalau belum ada
    _sheets()
    logger.info("Asisten Plastik siap jalan.")


def main():
    if not config.TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN belum diisi di environment variables.")

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).post_init(on_startup).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("groupid", groupid_cmd))
    app.add_handler(CommandHandler("pricelist", pricelist_cmd))
    app.add_handler(CommandHandler("lunas", lunas_cmd))
    app.add_handler(CommandHandler("invoice", invoice_cmd))
    app.add_handler(CommandHandler("suratjalan", suratjalan_cmd))
    app.add_handler(CommandHandler("piutang", piutang_cmd))
    app.add_handler(CommandHandler("po", po_cmd))
    app.add_handler(CommandHandler("bayarutang", bayarutang_cmd))
    app.add_handler(CommandHandler("utang", utang_cmd))
    app.add_handler(CommandHandler("kas", kas_cmd))
    app.add_handler(CommandHandler("laporanbulanan", laporanbulanan_cmd))
    app.add_handler(CommandHandler("batal", batal_cmd))

    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("Starting polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
