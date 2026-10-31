"""Hitung semua angka laporan buat dashboard owner (murni baca dari Sheets)."""

import datetime

import config

BULAN = ["", "Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        try:
            return float(str(v).replace(".", "").replace(",", "."))
        except ValueError:
            return 0.0


def _wib_today():
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=7)).date()


def _d(s):
    try:
        return datetime.datetime.strptime(str(s)[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _geser_bulan(ym, n):
    y, m = ym
    m += n
    while m > 12:
        y, m = y + 1, m - 12
    while m < 1:
        y, m = y - 1, m + 12
    return y, m


def _top(d, n=8):
    return sorted(d.items(), key=lambda kv: -kv[1])[:n]


def hitung_laporan(sheets, bulan=None):
    """bulan: 'YYYY-MM' (default bulan ini WIB). Balikin dict siap di-JSON."""
    today = _wib_today()
    try:
        y, m = [int(x) for x in str(bulan).split("-")]
        if not 1 <= m <= 12:
            raise ValueError
    except (ValueError, AttributeError):
        y, m = today.year, today.month
    pref = f"{y:04d}-{m:02d}"

    orders = sheets.get_all_orders()
    pos = sheets.get_all_pos()
    utang_rows = sheets._records(sheets._ws(config.SHEET_UTANG_SUPPLIER))
    kas = sheets.get_kas_entries()
    rems = sheets._reminder_records()
    harga_beli = {}
    for p in sheets.get_price_list():
        harga_beli[str(p.get("Item_Code", "")).strip().upper()] = _f(p.get("Harga_Beli"))

    # ---- invoice (gabung baris per No_Invoice, buang Batal) ----
    inv = {}
    for r in orders:
        no = str(r.get("No_Invoice", "")).strip()
        if not no or str(r.get("Status", "")) == "Batal":
            continue
        o = inv.setdefault(no, {"invoice": no, "customer": str(r.get("Nama_Customer", "")),
                                "tgl": str(r.get("Timestamp", ""))[:10], "status": str(r.get("Status", "")),
                                "bayar": str(r.get("Tanggal_Bayar", ""))[:10], "total": 0.0, "hpp": 0.0,
                                "hpp_lengkap": True, "items": []})
        sub, qty = _f(r.get("Subtotal")), _f(r.get("Qty"))
        o["total"] += sub + _f(r.get("Ongkir"))
        hb = harga_beli.get(str(r.get("Item_Code", "")).strip().upper(), 0.0)
        if hb > 0:
            o["hpp"] += hb * qty
        else:
            o["hpp_lengkap"] = False
        o["items"].append({"nama": str(r.get("Nama_Item", "")), "kategori": str(r.get("Kategori", "")) or "Lainnya",
                           "qty": qty, "satuan": str(r.get("Satuan", "")), "subtotal": sub,
                           "hpp": hb * qty if hb > 0 else None})

    # ---- status kontra bon per invoice (dari tab Pengingat) ----
    kb_aktif, kb_selesai, tagih_due = {}, set(), {}
    for r in rems:
        ref, jenis, st = str(r.get("Ref", "")), r.get("Jenis"), str(r.get("Status", ""))
        if jenis == "kontra_bon":
            if st == "Aktif":
                kb_aktif[ref] = str(r.get("Tanggal", ""))[:10]
            elif st == "Selesai":
                kb_selesai.add(ref)
        elif jenis == "bayar_customer" and st == "Aktif":
            tagih_due[ref] = str(r.get("Tanggal", ""))[:10]

    # ---- piutang / tagihan ----
    tagihan, aging = [], {"0-7 hari": 0.0, "8-14 hari": 0.0, "15-30 hari": 0.0, "> 30 hari": 0.0}
    per_cust_piutang = {}
    for o in inv.values():
        if o["status"] != "Pending":
            continue
        tgl = _d(o["tgl"]) or today
        umur = max((today - tgl).days, 0)
        if o["invoice"] in kb_aktif:
            kb, jadwal = "belum", kb_aktif[o["invoice"]]
        elif o["invoice"] in kb_selesai:
            kb, jadwal = "sudah", tagih_due.get(o["invoice"], "")
        else:
            kb, jadwal = "-", tagih_due.get(o["invoice"], "")
        telat = bool(jadwal and jadwal < today.strftime("%Y-%m-%d"))
        tagihan.append({"invoice": o["invoice"], "customer": o["customer"], "tgl": o["tgl"], "umur": umur,
                        "total": o["total"], "kontra_bon": kb, "jadwal": jadwal, "telat": telat})
        k = "0-7 hari" if umur <= 7 else "8-14 hari" if umur <= 14 else "15-30 hari" if umur <= 30 else "> 30 hari"
        aging[k] += o["total"]
        per_cust_piutang[o["customer"]] = per_cust_piutang.get(o["customer"], 0) + o["total"]
    tagihan.sort(key=lambda t: (-t["umur"], t["invoice"]))

    # ---- penjualan bulan terpilih ----
    bln = [o for o in inv.values() if o["tgl"].startswith(pref)]
    omzet = sum(o["total"] for o in bln)
    lunas_bln = sum(o["total"] for o in bln if o["status"] == "Lunas")
    hpp_bln = sum(o["hpp"] for o in bln)
    hpp_ok = all(o["hpp_lengkap"] for o in bln)
    harian, per_cust, per_prod, per_kat, qty_prod = {}, {}, {}, {}, {}
    for o in bln:
        harian[o["tgl"]] = harian.get(o["tgl"], 0) + o["total"]
        per_cust[o["customer"]] = per_cust.get(o["customer"], 0) + o["total"]
        for it in o["items"]:
            per_prod[it["nama"]] = per_prod.get(it["nama"], 0) + it["subtotal"]
            qty_prod[it["nama"]] = (qty_prod.get(it["nama"], ("", 0))[0] or it["satuan"],
                                    qty_prod.get(it["nama"], ("", 0))[1] + it["qty"])
            per_kat[it["kategori"]] = per_kat.get(it["kategori"], 0) + it["subtotal"]
    jml_hari = (datetime.date(*_geser_bulan((y, m), 1), 1) - datetime.date(y, m, 1)).days
    seri_harian = [{"tgl": f"{pref}-{d:02d}", "total": harian.get(f"{pref}-{d:02d}", 0)} for d in range(1, jml_hari + 1)]

    # ---- tren 6 bulan (omzet, kas masuk/keluar) ----
    tren = []
    for i in range(5, -1, -1):
        yy, mm = _geser_bulan((y, m), -i)
        p = f"{yy:04d}-{mm:02d}"
        om = sum(o["total"] for o in inv.values() if o["tgl"].startswith(p))
        km = sum(_f(r.get("Jumlah")) for r in kas if str(r.get("Tanggal", "")).startswith(p) and r.get("Jenis") == "Masuk")
        kk = sum(_f(r.get("Jumlah")) for r in kas if str(r.get("Tanggal", "")).startswith(p) and r.get("Jenis") == "Keluar")
        tren.append({"bulan": f"{BULAN[mm]} {str(yy)[2:]}", "omzet": om, "kas_masuk": km, "kas_keluar": kk})

    # ---- kas bulan terpilih ----
    lap = sheets.get_laporan_bulanan(y, m)
    kas_bln = [r for r in kas if str(r.get("Tanggal", "")).startswith(pref)]
    kas_list = [{"tgl": str(r.get("Tanggal", "")), "jenis": r.get("Jenis", ""), "kategori": r.get("Kategori", ""),
                 "jumlah": _f(r.get("Jumlah")), "ket": str(r.get("Keterangan", ""))}
                for r in sorted(kas_bln, key=lambda r: str(r.get("Tanggal", "")), reverse=True)][:60]
    saldo_kas = sum(_f(r.get("Jumlah")) * (1 if r.get("Jenis") == "Masuk" else -1) for r in kas
                    if r.get("Jenis") in ("Masuk", "Keluar"))

    # ---- utang supplier ----
    po_due = {}
    for r in rems:
        if r.get("Jenis") == "bayar_supplier" and str(r.get("Status", "")) == "Aktif":
            po_due[str(r.get("Ref", ""))] = str(r.get("Tanggal", ""))[:10]
    po = {}
    for r in pos:
        no = str(r.get("No_PO", "")).strip()
        if not no or str(r.get("Status", "")) in ("Batal", "Lunas"):
            continue
        o = po.setdefault(no, {"po": no, "supplier": str(r.get("Nama_Supplier", "")),
                               "tgl": str(r.get("Timestamp", ""))[:10], "total": 0.0})
        o["total"] += _f(r.get("Subtotal"))
    po_list = []
    for o in po.values():
        due = po_due.get(o["po"], "")
        o["jatuh_tempo"] = due
        o["telat"] = bool(due and due < today.strftime("%Y-%m-%d"))
        po_list.append(o)
    po_list.sort(key=lambda o: (o["jatuh_tempo"] or "9999", o["po"]))
    utang = sheets.get_utang_summary()

    stok = []
    try:
        stok = sheets.get_stok_all()
    except Exception:
        pass
    pernah = [s for s in stok if s.get("status") in ("habis", "menipis")]

    # ---- order web yang belum di-approve + invoice yang belum dikirim ----
    import json as _json
    web_menunggu = []
    try:
        for r in sheets._records(sheets._ws(config.SHEET_PESANANWEB)):
            if str(r.get("Status", "")) != "Menunggu":
                continue
            try:
                n_item = len((_json.loads(r.get("Payload") or "{}")).get("items") or [])
            except ValueError:
                n_item = 0
            web_menunggu.append({"id": str(r.get("ID", "")), "waktu": str(r.get("Waktu", ""))[:16],
                                 "nama": str(r.get("Nama", "")), "n_item": n_item})
    except Exception:
        pass
    belum_kirim = []
    try:
        for d in sheets.get_orders_gudang(300):
            if not d["dikirim"]:
                belum_kirim.append({"invoice": d["invoice"], "customer": d["customer"], "tgl": d["tgl"],
                                    "kirim": d["kirim"], "n_item": len(d["items"])})
    except Exception:
        pass

    total_piutang = sum(t["total"] for t in tagihan)
    ringkas = {
        "omzet": omzet, "jml_invoice": len(bln), "lunas": lunas_bln, "belum_lunas": omzet - lunas_bln,
        "laba_kotor": omzet - hpp_bln if bln else 0, "laba_lengkap": hpp_ok,
        "rata_invoice": omzet / len(bln) if bln else 0,
        "total_piutang": total_piutang, "jml_tagihan": len(tagihan),
        "belum_kontra_bon": sum(1 for t in tagihan if t["kontra_bon"] == "belum"),
        "telat": sum(1 for t in tagihan if t["telat"]), "total_telat": sum(t["total"] for t in tagihan if t["telat"]),
        "total_utang": sum(utang.values()), "jml_po_terbuka": len(po_list),
        "po_telat": sum(1 for o in po_list if o["telat"]),
        "kas_masuk": lap["total_masuk"], "kas_keluar": lap["total_keluar"], "kas_laba": lap["laba"],
        "saldo_kas": saldo_kas, "web_menunggu": len(web_menunggu), "belum_kirim": len(belum_kirim),
        "stok_habis": sum(1 for s in stok if s.get("status") == "habis"),
        "stok_menipis": sum(1 for s in stok if s.get("status") == "menipis"),
    }
    return {
        "ok": True, "bulan": pref, "bulan_label": f"{BULAN[m]} {y}", "hari_ini": today.strftime("%Y-%m-%d"),
        "ringkas": ringkas, "tren": tren, "harian": seri_harian,
        "top_customer": [{"nama": k, "total": v} for k, v in _top(per_cust)],
        "top_produk": [{"nama": k, "total": v, "qty": qty_prod[k][1], "satuan": qty_prod[k][0]} for k, v in _top(per_prod)],
        "per_kategori": [{"nama": k, "total": v} for k, v in _top(per_kat, 10)],
        "invoice_bulan": sorted([{"invoice": o["invoice"], "customer": o["customer"], "tgl": o["tgl"],
                                  "total": o["total"], "status": o["status"]} for o in bln],
                                key=lambda o: o["invoice"], reverse=True)[:100],
        "aging": [{"nama": k, "total": v} for k, v in aging.items()],
        "piutang_customer": [{"nama": k, "total": v} for k, v in _top(per_cust_piutang, 15)],
        "tagihan": tagihan, "po_terbuka": po_list,
        "utang_supplier": [{"nama": k, "total": v} for k, v in _top(utang, 20)],
        "kas_masuk_kat": [{"nama": k, "total": v} for k, v in _top(lap["masuk_by_kategori"])],
        "kas_keluar_kat": [{"nama": k, "total": v} for k, v in _top(lap["keluar_by_kategori"])],
        "kas_list": kas_list, "web_list": web_menunggu, "belum_kirim_list": belum_kirim[:40], "stok_bermasalah": len(pernah),
    }
