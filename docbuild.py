"""Bikin PDF invoice / surat jalan (kertas dot matrix 8,5x5,5 inch) buat halaman web."""

import config
import dotmatrix


def _ongkir(rows):
    total = 0.0
    for r in rows:
        try:
            total += float(r.get("Ongkir", 0) or 0)
        except (TypeError, ValueError):
            pass
    return total


def _hasil(sheets, no_invoice, kind):
    """(nama, pages, txt, pdf) atau None."""
    rows = sheets.get_order_items(no_invoice)
    if not rows:
        return None
    first = rows[0]
    common = dict(no_po_customer=first.get("No_PO_Customer", ""), tanggal_kirim=first.get("Tanggal_Kirim", ""),
                  tanggal=first.get("Timestamp", ""), catatan=str(first.get("Catatan", "") or ""))
    if kind == "inv":
        items = [{"nama_item": r["Nama_Item"], "qty": r["Qty"], "satuan": r["Satuan"],
                  "harga_satuan": r["Harga_Satuan"]} for r in rows]
        pages, txt, pdf = dotmatrix.generate_invoice_dotmatrix(
            no_invoice, first["Nama_Customer"], first.get("No_HP", ""), first.get("Alamat", ""),
            first.get("Metode", "Kirim"), items, _ongkir(rows), **common)
        return no_invoice, pages, txt, pdf
    items = [{"nama_item": r["Nama_Item"], "qty": r["Qty"], "satuan": r["Satuan"]} for r in rows]
    nama = no_invoice.replace(config.INVOICE_PREFIX, config.SURAT_JALAN_PREFIX, 1)
    pages, txt, pdf = dotmatrix.generate_surat_jalan_dotmatrix(
        nama, first["Nama_Customer"], first.get("No_HP", ""), first.get("Alamat", ""),
        first.get("Metode", "Kirim"), items, no_invoice_ref=no_invoice, **common)
    return nama, pages, txt, pdf


BARIS_HALAMAN = 33   # 5,5 inch x 6 baris/inch
ATAS = 2             # baris kosong di atas (biar kop gak kepotong)


def bangun_txt(sheets, no_invoice, kind):
    """File teks polos buat 'mode teks' (Generic / Text Only): printer pakai huruf
    bawaannya sendiri -> tajam & cepat. Tiap halaman PERSIS 33 baris (tanpa form
    feed) biar halaman berikutnya pas mulai di lembar berikutnya."""
    import unicodedata
    h = _hasil(sheets, no_invoice, kind)
    if not h:
        return None
    nama, _, txt, _ = h
    txt.seek(0)
    out = []
    for halaman in txt.read().decode("utf-8").split("\f"):
        txt_lines = halaman.replace("\r\n", "\n").strip("\n").split("\n")
        lines = [""] * ATAS
        for ln in txt_lines:
            ln = ln.replace("─", "-").replace("═", "=").replace("×", "x")
            ln = unicodedata.normalize("NFKD", ln).encode("ascii", "replace").decode()
            lines.append(ln.rstrip()[:80])
        lines = lines[:BARIS_HALAMAN] + [""] * max(0, BARIS_HALAMAN - len(lines))
        out += lines
    return f"{nama}.txt", ("\r\n".join(out) + "\r\n").encode("ascii")


def bangun_pdf(sheets, no_invoice, kind):
    """kind: 'inv' | 'sj'. Balikin (nama_file, bytes) atau None kalau invoice gak ada."""
    rows = sheets.get_order_items(no_invoice)
    if not rows:
        return None
    first = rows[0]
    common = dict(no_po_customer=first.get("No_PO_Customer", ""), tanggal_kirim=first.get("Tanggal_Kirim", ""),
                  tanggal=first.get("Timestamp", ""), catatan=str(first.get("Catatan", "") or ""))
    if kind == "inv":
        items = [{"nama_item": r["Nama_Item"], "qty": r["Qty"], "satuan": r["Satuan"],
                  "harga_satuan": r["Harga_Satuan"]} for r in rows]
        _, _, pdf = dotmatrix.generate_invoice_dotmatrix(
            no_invoice, first["Nama_Customer"], first.get("No_HP", ""), first.get("Alamat", ""),
            first.get("Metode", "Kirim"), items, _ongkir(rows), **common)
        nama = no_invoice
    else:
        items = [{"nama_item": r["Nama_Item"], "qty": r["Qty"], "satuan": r["Satuan"]} for r in rows]
        nama = no_invoice.replace(config.INVOICE_PREFIX, config.SURAT_JALAN_PREFIX, 1)
        _, _, pdf = dotmatrix.generate_surat_jalan_dotmatrix(
            nama, first["Nama_Customer"], first.get("No_HP", ""), first.get("Alamat", ""),
            first.get("Metode", "Kirim"), items, no_invoice_ref=no_invoice, **common)
    pdf.seek(0)
    return f"{nama}.pdf", pdf.read()
