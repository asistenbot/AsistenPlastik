"""Halaman order online buat customer langganan (mis. Grandia).
Link: <alamat bot>/order/<token>. Customer pilih produk + qty, kirim, dan
ordernya masuk ke Telegram admin buat dikonfirmasi."""

import asyncio
import html
import json
import logging
import uuid

from aiohttp import web

import config

logger = logging.getLogger(__name__)

PAGE = """<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Order - __BIZ__</title><style>
:root{--g:#0f7b6c;--bg:#f4f7f6;--ink:#1c2b28;--mu:#6b7c78;--ln:#dbe4e1}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.4 system-ui,sans-serif}
header{background:var(--g);color:#fff;padding:18px 16px}header h1{margin:0;font-size:20px}header p{margin:4px 0 0;opacity:.9;font-size:14px}
main{max-width:720px;margin:0 auto;padding:12px 12px 120px}
h2{font-size:15px;color:var(--g);margin:20px 4px 6px;text-transform:uppercase;letter-spacing:.04em}
.card{background:#fff;border:1px solid var(--ln);border-radius:12px;padding:6px 12px}
.it{display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid var(--ln)}.it:last-child{border:0}
.it .n{flex:1}.it .n b{display:block;font-weight:600}.it .n span{color:var(--mu);font-size:13px}
.q{display:flex;align-items:center;gap:6px}.q button{width:34px;height:34px;border-radius:50%;border:1px solid var(--g);background:#fff;color:var(--g);font-size:20px}
.q input{width:60px;height:36px;text-align:center;border:1px solid var(--ln);border-radius:8px;font-size:16px}
label{display:block;margin:12px 4px 4px;font-size:14px;color:var(--mu)}
input[type=date],input[type=text],textarea{width:100%;padding:10px;border:1px solid var(--ln);border-radius:8px;font:inherit;background:#fff}
.bar{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid var(--ln);padding:10px 14px;display:flex;align-items:center;gap:12px}
.bar .t{flex:1}.bar .t small{color:var(--mu);display:block;font-size:12px}.bar .t b{font-size:18px}
.bar button{background:var(--g);color:#fff;border:0;border-radius:10px;padding:13px 20px;font-size:16px;font-weight:600}
.bar button:disabled{opacity:.5}.ok{text-align:center;padding:40px 16px}.ok h2{font-size:22px;color:var(--g);text-transform:none}
.wa{display:inline-block;margin-top:14px;background:#25d366;color:#fff;text-decoration:none;padding:14px 22px;border-radius:10px;font-weight:600}
</style></head><body>
<header><h1>Order ke __BIZ__</h1><p>Halo, <b>__NAMA__</b> — pilih barang & jumlahnya, lalu kirim.</p></header>
<main id="m"></main>
<div class="bar" id="bar"><div class="t"><small id="cnt">0 item</small><b id="tot">Rp0</b></div><button id="go" disabled>Kirim Order</button></div>
<script>
const D=__DATA__;const qty={};const rp=n=>'Rp'+Math.round(n).toLocaleString('id-ID');
const m=document.getElementById('m');
const cats={};D.items.forEach(i=>{(cats[i.kategori||'Lainnya']=cats[i.kategori||'Lainnya']||[]).push(i)});
let h='';Object.keys(cats).forEach(c=>{h+='<h2>'+esc(c)+'</h2><div class="card">';cats[c].forEach(i=>{
h+='<div class="it"><div class="n"><b>'+esc(i.nama)+'</b><span>'+rp(i.harga)+' / '+esc(i.satuan)+'</span></div><div class="q"><button data-c="'+esc(i.code)+'" data-d="-1">−</button><input inputmode="decimal" id="q_'+esc(i.code)+'" value="0" data-c="'+esc(i.code)+'"><button data-c="'+esc(i.code)+'" data-d="1">+</button></div></div>'});h+='</div>'});
h+='<h2>Pengiriman</h2><div class="card" style="padding:12px"><label style="margin-top:0">Tanggal kirim</label><input type="date" id="tgl"><label>No. PO Anda (kalau ada)</label><input type="text" id="po"><label>Catatan</label><textarea id="cat" rows="2"></textarea></div>';
m.innerHTML=h;
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}
const P={};D.items.forEach(i=>P[i.code]=i);
function upd(){let t=0,n=0;for(const c in qty){if(qty[c]>0){t+=qty[c]*P[c].harga;n++}}
document.getElementById('cnt').textContent=n+' item';document.getElementById('tot').textContent=rp(t);document.getElementById('go').disabled=n==0}
m.addEventListener('click',e=>{const b=e.target.closest('button');if(!b)return;const c=b.dataset.c,d=+b.dataset.d;
qty[c]=Math.max(0,(qty[c]||0)+d);document.getElementById('q_'+c).value=qty[c];upd()});
m.addEventListener('input',e=>{const c=e.target.dataset.c;if(!c)return;let v=parseFloat(String(e.target.value).replace(',','.'));qty[c]=isFinite(v)&&v>0?v:0;upd()});
document.getElementById('go').onclick=async()=>{const b=document.getElementById('go');b.disabled=true;b.textContent='Mengirim...';
const items=Object.keys(qty).filter(c=>qty[c]>0).map(c=>({code:c,qty:qty[c]}));
try{const r=await fetch(location.pathname,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({items,tanggal_kirim:document.getElementById('tgl').value,no_po:document.getElementById('po').value,catatan:document.getElementById('cat').value})});
const j=await r.json();if(!r.ok||!j.ok)throw new Error(j.error||'Gagal');
document.getElementById('bar').remove();
m.innerHTML='<div class="ok"><h2>✅ Order terkirim</h2><p>Nomor order: <b>'+esc(j.id)+'</b><br>Total '+rp(j.total)+'</p><p>Silakan konfirmasi lewat WhatsApp supaya cepat diproses.</p>'+(j.wa?'<a class="wa" href="'+esc(j.wa)+'">Konfirmasi via WhatsApp</a>':'')+'</div>';
window.scrollTo(0,0)}catch(err){alert('Order gagal terkirim: '+err.message+'. Coba lagi ya.');b.disabled=false;b.textContent='Kirim Order'}};
</script></body></html>"""


def _item_label(row):
    nama = str(row.get("Nama", "") or "")
    desk = str(row.get("Deskripsi", "") or "").strip()
    if desk and desk.upper() != "POLOS" and desk.lower() not in nama.lower():
        return f"{nama} - {desk}"
    return nama


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def make_web_app(sheets_getter, on_order):
    """on_order(pid, parsed) -> coroutine, dipanggil tiap order masuk."""

    async def health(request):
        return web.Response(text="Asisten Plastik aktif.")

    async def form(request):
        token = request.match_info["token"]
        sheets = sheets_getter()
        link = await asyncio.to_thread(sheets.get_link_by_token, token)
        if not link:
            return web.Response(status=404, text="Link order tidak valid / sudah dinonaktifkan.")
        rows = await asyncio.to_thread(sheets.get_price_list)
        items = []
        for r in rows:
            code = str(r.get("Item_Code", "")).strip()
            if not code or _num(r.get("Harga_Jual")) <= 0:
                continue
            items.append({"code": code, "nama": _item_label(r), "kategori": r.get("Kategori", ""),
                          "satuan": r.get("Satuan", ""), "harga": _num(r.get("Harga_Jual"))})
        data = json.dumps({"items": items}).replace("</", "<\\/")
        page = (PAGE.replace("__DATA__", data)
                    .replace("__NAMA__", html.escape(str(link.get("Nama_Customer", ""))))
                    .replace("__BIZ__", html.escape(config.BUSINESS_NAME)))
        return web.Response(text=page, content_type="text/html", charset="utf-8")

    async def submit(request):
        token = request.match_info["token"]
        sheets = sheets_getter()
        try:
            link = await asyncio.to_thread(sheets.get_link_by_token, token)
            if not link:
                return web.json_response({"ok": False, "error": "Link tidak valid"}, status=404)
            body = await request.json()
            req = body.get("items") or []
            if not isinstance(req, list) or not req or len(req) > 80:
                return web.json_response({"ok": False, "error": "Belum ada barang dipilih"}, status=400)
            pmap = await asyncio.to_thread(sheets.get_price_map)
            items, total = [], 0.0
            for it in req:
                code = str(it.get("code", "")).strip().upper()
                qty = _num(it.get("qty"))
                row = pmap.get(code)
                if row is None or qty <= 0 or qty > 100000:
                    continue
                harga = _num(row.get("Harga_Jual"))
                total += qty * harga
                items.append({"item_code": row["Item_Code"], "nama_item": _item_label(row),
                              "kategori": row.get("Kategori", ""), "satuan": row.get("Satuan", ""),
                              "harga_satuan": harga, "qty": qty})
            if not items:
                return web.json_response({"ok": False, "error": "Barang tidak valid"}, status=400)
            nama = str(link.get("Nama_Customer", ""))
            cust = await asyncio.to_thread(sheets.get_customer, nama) or {}
            parsed = {
                "nama_customer": nama, "no_hp": str(cust.get("No_HP", "") or ""),
                "alamat": str(cust.get("Alamat", "") or ""), "metode": "Kirim", "items": items, "ongkir": 0,
                "no_po_customer": str(body.get("no_po", ""))[:60],
                "tanggal_kirim": str(body.get("tanggal_kirim", ""))[:10],
                "catatan": str(body.get("catatan", ""))[:300], "_web": True,
            }
            pid = "W" + uuid.uuid4().hex[:6].upper()
            await asyncio.to_thread(sheets.add_pesanan_web, pid, nama, json.dumps(parsed, ensure_ascii=False))
            try:
                await on_order(pid, parsed)
            except Exception:
                logger.exception("gagal notif order web ke Telegram")
            wa = ""
            if config.ADMIN_WA:
                from urllib.parse import quote
                wa = "https://wa.me/" + config.ADMIN_WA + "?text=" + quote(
                    f"Halo, saya dari {nama}. Order online {pid} sudah dikirim, mohon dikonfirmasi. Terima kasih.")
            return web.json_response({"ok": True, "id": pid, "total": total, "wa": wa})
        except Exception:
            logger.exception("gagal proses order web")
            return web.json_response({"ok": False, "error": "Server bermasalah"}, status=500)

    app = web.Application(client_max_size=256 * 1024)
    app.router.add_get("/", health)
    app.router.add_get("/order/{token}", form)
    app.router.add_post("/order/{token}", submit)
    return app


async def start_web(sheets_getter, on_order):
    runner = web.AppRunner(make_web_app(sheets_getter, on_order))
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.WEB_PORT)
    await site.start()
    logger.info("Web order jalan di port %s", config.WEB_PORT)
    return runner
