"""Tes alur uang: order -> lunas -> kas, batal, PO -> utang supplier -> bayar, komisi, laporan."""
import config

ITEMS = [
    {"item_code": "TLP-01", "nama_item": "Tulip 15", "kategori": "TULIP", "qty": 10, "satuan": "Pack", "harga_satuan": 18000},
    {"item_code": "SMP-01", "nama_item": "Sampah 60x100", "kategori": "SAMPAH", "qty": 5, "satuan": "KG", "harga_satuan": 20000},
]
TOTAL = 10 * 18000 + 5 * 20000 + 15000   # barang + ongkir


def _order(sheets, nama="Toko Contoh"):
    return sheets.add_order(nama, "0811", "Jl. Contoh", "Kirim", ITEMS, ongkir=15000)


def _status(sheets, inv):
    return {str(r["Status"]) for r in sheets.get_order_items(inv)}


def _kas(tab, jenis):
    return [r for r in tab(config.SHEET_KAS) if r["Jenis"] == jenis]


# ---------- ORDER & PIUTANG ----------

def test_order_baru_masuk_piutang(sheets):
    inv = _order(sheets)
    assert inv.startswith(config.INVOICE_PREFIX)
    assert _status(sheets, inv) == {"Pending"}
    assert sheets.get_piutang_summary() == {"Toko Contoh": TOTAL}


def test_nomor_invoice_gak_dobel(sheets):
    assert _order(sheets) != _order(sheets)


# ---------- LUNAS ----------

def test_lunas_total_benar_dan_keluar_dari_piutang(sheets):
    inv = _order(sheets)
    assert sheets.mark_order_lunas(inv) == TOTAL
    assert _status(sheets, inv) == {"Lunas"}
    assert sheets.get_piutang_summary() == {}


def test_lunas_dua_kali_ditolak(sheets):
    inv = _order(sheets)
    assert sheets.mark_order_lunas(inv) == TOTAL
    assert sheets.mark_order_lunas(inv) is None      # gak boleh ngasih total lagi -> Kas gak dobel


def test_lunas_invoice_gak_ada(sheets):
    assert sheets.mark_order_lunas("INV-TIDAK-ADA") is None


def test_lunas_banyak_kas_masuk_sekali_per_invoice(sheets, tab):
    a, b = _order(sheets), _order(sheets)
    hasil = sheets.lunas_banyak([a, b, a], via="tes")
    assert sorted(h[0] for h in hasil) == sorted([a, b])
    assert sheets.lunas_banyak([a, b]) == []           # diulang: gak ada yang diproses
    masuk = _kas(tab, "Masuk")
    assert len(masuk) == 2
    assert sum(r["Jumlah"] for r in masuk) == 2 * TOTAL


def test_order_batal_gak_bisa_dilunasin(sheets):
    inv = _order(sheets)
    assert sheets.cancel_order(inv) is True
    assert sheets.mark_order_lunas(inv) is None
    assert _status(sheets, inv) == {"Batal"}


# ---------- BATAL LUNAS ----------

def test_batal_lunas_balik_pending_dan_kas_dihapus(sheets, tab):
    inv = _order(sheets)
    sheets.lunas_banyak([inv])
    assert sheets.unmark_order_lunas(inv) == TOTAL
    assert _status(sheets, inv) == {"Pending"}
    assert _kas(tab, "Masuk") == []
    assert sheets.get_piutang_summary() == {"Toko Contoh": TOTAL}


def test_batal_lunas_ke_invoice_pending_gak_ngapa_ngapain(sheets, tab):
    inv = _order(sheets)
    sebelum = len(tab(config.SHEET_PENGINGAT))
    assert sheets.unmark_order_lunas(inv) is None
    assert len(tab(config.SHEET_PENGINGAT)) == sebelum   # gak nambah pengingat dobel


def test_batal_lunas_gak_ngidupin_order_batal(sheets):
    inv = _order(sheets)
    sheets.cancel_order(inv)
    assert sheets.unmark_order_lunas(inv) is None
    assert _status(sheets, inv) == {"Batal"}


# ---------- BATAL ORDER ----------

def test_batal_order_keluar_dari_piutang(sheets):
    inv = _order(sheets)
    assert sheets.cancel_order(inv) is True
    assert sheets.get_piutang_summary() == {}


def test_order_lunas_gak_bisa_langsung_dibatalin(sheets, tab):
    inv = _order(sheets)
    sheets.lunas_banyak([inv])
    assert sheets.cancel_order(inv) is False           # harus batal lunas dulu
    assert _status(sheets, inv) == {"Lunas"}
    assert len(_kas(tab, "Masuk")) == 1


# ---------- PO & UTANG SUPPLIER ----------

PO_ITEMS = [{"nama_item": "Tulip 15", "qty": 100, "satuan": "Pack", "harga_satuan": 15000}]
PO_TOTAL = 100 * 15000


def test_po_baru_jadi_utang(sheets):
    no_po, total = sheets.add_purchase_order("Supplier Contoh", PO_ITEMS)
    assert total == PO_TOTAL
    assert sheets.get_utang_summary() == {"Supplier Contoh": PO_TOTAL}


def test_bayar_po_utang_nol_kas_keluar_sekali(sheets, tab):
    no_po, _ = sheets.add_purchase_order("Supplier Contoh", PO_ITEMS)
    assert sheets.bayar_po(no_po, "tes") == ("Supplier Contoh", PO_TOTAL)
    assert sheets.bayar_po(no_po, "tes") is None        # gak bisa dibayar dua kali
    assert sheets.get_utang_summary() == {}
    keluar = _kas(tab, "Keluar")
    assert len(keluar) == 1 and keluar[0]["Jumlah"] == PO_TOTAL
    assert {str(r["Status"]) for r in sheets.get_po_items(no_po)} == {"Lunas"}


def test_batal_po_utang_balik_nol(sheets):
    no_po, _ = sheets.add_purchase_order("Supplier Contoh", PO_ITEMS)
    found, nama, total = sheets.cancel_po(no_po)
    assert (found, total) == (True, PO_TOTAL)
    assert sheets.get_utang_summary() == {}
    assert sheets.cancel_po(no_po)[0] is False          # batal dua kali: gak dobel ngurangin


def test_po_lunas_gak_bisa_dibatalin(sheets):
    no_po, _ = sheets.add_purchase_order("Supplier Contoh", PO_ITEMS)
    sheets.bayar_po(no_po, "tes")
    assert sheets.cancel_po(no_po)[0] is False
    assert sheets.get_utang_summary() == {}             # utang gak jadi minus
    assert {str(r["Status"]) for r in sheets.get_po_items(no_po)} == {"Lunas"}


def test_dua_po_bayar_satu_sisa_satu(sheets):
    a, _ = sheets.add_purchase_order("Supplier Contoh", PO_ITEMS)
    sheets.add_purchase_order("Supplier Contoh", PO_ITEMS)
    sheets.bayar_po(a, "tes")
    assert sheets.get_utang_summary() == {"Supplier Contoh": PO_TOTAL}


# ---------- KOMISI ----------

def test_komisi_dicatat_pas_lunas_dan_dibayar_sekali(sheets, tab):
    sheets.set_komisi("Toko Contoh", 500, "Pak Contoh")
    inv = _order(sheets)
    sheets.lunas_banyak([inv])
    belum = sheets.get_komisi_belum()
    assert len(belum) == 1 and belum[0]["Jumlah"] == 15 * 500     # qty 10 + 5
    assert sheets.bayar_komisi(inv) is not None
    assert sheets.bayar_komisi(inv) is None
    komisi = [r for r in _kas(tab, "Keluar") if r["Kategori"] == "Komisi"]
    assert len(komisi) == 1 and komisi[0]["Jumlah"] == 15 * 500


def test_batal_lunas_ngebatalin_komisi_yang_belum_dibayar(sheets):
    sheets.set_komisi("Toko Contoh", 500, "Pak Contoh")
    inv = _order(sheets)
    sheets.lunas_banyak([inv])
    sheets.unmark_order_lunas(inv)
    assert sheets.get_komisi_belum() == []


# ---------- LAPORAN ----------

def test_laporan_bulanan_laba(sheets):
    sheets.add_kas_entry("Masuk", "Penjualan", 500000, tanggal="2026-10-05")
    sheets.add_kas_entry("Keluar", "Operasional", 120000, tanggal="2026-10-09")
    sheets.add_kas_entry("Masuk", "Penjualan", 999999, tanggal="2026-11-01")   # bulan lain
    lap = sheets.get_laporan_bulanan(2026, 10)
    assert (lap["total_masuk"], lap["total_keluar"], lap["laba"]) == (500000, 120000, 380000)
