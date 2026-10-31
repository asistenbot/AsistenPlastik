"""Panel staff gudang: login ID+password, ajukan stok masuk / hitung stok,
minta barang, tandai pesanan dikirim. Staff TIDAK bisa ngubah stok langsung --
semua pengajuan nunggu disetujui owner."""

import asyncio
import hashlib
import hmac
import html
import logging
import time

from aiohttp import web

import config

logger = logging.getLogger(__name__)

COOKIE = "staff_sess"
SESSION_SECS = 12 * 3600
_gagal = {}  # (ip,id) -> [timestamps]


def _sign(sid, exp):
    msg = f"{sid}|{exp}".encode()
    return hmac.new(config.WEB_SECRET.encode(), msg, hashlib.sha256).hexdigest()


def _make_cookie(sid):
    exp = int(time.time()) + SESSION_SECS
    return f"{sid}|{exp}|{_sign(sid, exp)}"


def _read_cookie(request):
    raw = request.cookies.get(COOKIE, "")
    try:
        sid, exp, sig = raw.split("|")
        if int(exp) < time.time() or not hmac.compare_digest(sig, _sign(sid, exp)):
            return None
        return sid
    except ValueError:
        return None


STAFF_HTML = """<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Panel Gudang</title><style>
:root{--g:#0f7b6c;--bg:#f4f7f6;--ink:#1c2b28;--mu:#6b7c78;--ln:#dbe4e1}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.4 system-ui,sans-serif}
header{background:var(--g);color:#fff;padding:12px 16px;display:flex;align-items:center;gap:10px}header h1{margin:0;font-size:18px;flex:1}
header button{background:rgba(255,255,255,.2);color:#fff;border:0;border-radius:8px;padding:6px 10px}
.tabs{display:flex;background:#fff;border-bottom:1px solid var(--ln);position:sticky;top:0;z-index:5;overflow-x:auto}
.tabs button{flex:1;min-width:84px;padding:11px 6px;border:0;background:none;font-size:14px;font-weight:600;color:var(--mu);border-bottom:3px solid transparent;white-space:nowrap}
.tabs button.on{color:var(--g);border-color:var(--g)}
main{max-width:720px;margin:0 auto;padding:10px 12px 120px}
.login{max-width:360px;margin:60px auto;background:#fff;border:1px solid var(--ln);border-radius:14px;padding:22px}
.login h2{margin:0 0 14px;color:var(--g)}
input,select,textarea{width:100%;padding:11px;border:1px solid var(--ln);border-radius:8px;font:inherit;background:#fff;margin:5px 0}
.btn{background:var(--g);color:#fff;border:0;border-radius:10px;padding:13px 18px;font-size:16px;font-weight:600;width:100%}
.btn:disabled{opacity:.5}.btn.sm{width:auto;padding:9px 14px;font-size:14px}
.card{background:#fff;border:1px solid var(--ln);border-radius:12px;padding:11px 13px;margin:9px 0}
.card b{display:block}.card small,.mu{color:var(--mu);font-size:13px}
.info{background:#e7f5f2;border:1px solid #bfe3dc;border-radius:10px;padding:10px 12px;font-size:14px;margin:8px 0}
.row{display:flex;gap:8px}.row input{flex:1.2;text-align:center;font-size:17px}.row select{flex:1}
.bar{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid var(--ln);padding:10px 14px;display:flex;gap:10px;align-items:center}
.bar .t{flex:1;font-size:14px;color:var(--mu)}.bar .btn{width:auto}
.badge{display:inline-block;font-size:12px;padding:2px 8px;border-radius:10px;margin-left:6px}
.menipis,.Menunggu,.Baru{background:#fff0c9;color:#7a5a00}.habis,.Ditolak{background:#ffd9d6;color:#9a1b12}.aman,.Disetujui,.Dikirim,.Selesai{background:#d9f3e4;color:#14633a}.belum{background:#e8e8e8;color:#555}
.it{margin:10px 0;padding-bottom:10px;border-bottom:1px solid var(--ln)}
.hide{display:none}.err{color:#b3261e;font-size:14px;min-height:20px}
</style></head><body>
<div id="app"></div>
<script>
const $=id=>document.getElementById(id);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>(Math.round(n*100)/100).toLocaleString('id-ID');
let ME=null,D=null,tab='pesanan';const vals={};
async function api(path,body){const r=await fetch('/staff/api/'+path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});
let j={};try{j=await r.json()}catch(_){}return{status:r.status,...j}}
function loginView(msg){$('app').innerHTML='<div class="login"><h2>📦 Panel Gudang</h2><p class="mu">__BIZ__</p><label>ID</label><input id="u" autocapitalize="none" autocomplete="username"><label>Password</label><input id="p" type="password" autocomplete="current-password"><div class="err" id="e">'+esc(msg||'')+'</div><button class="btn" id="b">Masuk</button></div>';
$('b').onclick=async()=>{$('b').disabled=true;const r=await api('login',{id:$('u').value.trim(),password:$('p').value});if(r.ok){ME=r.nama;await boot()}else{loginView(r.error||'Gagal masuk')}};
$('p').onkeydown=e=>{if(e.key=='Enter')$('b').click()}}
function stokTxt(i){if(i.stok===null)return 'belum dihitung';let t=fmt(i.stok)+' '+i.satuan;if(i.isi_bal>0&&i.stok>=i.isi_bal)t+=' (±'+(Math.round(i.stok/i.isi_bal*10)/10)+' bal)';return t}
async function boot(){const r=await api('data');if(r.status==401){loginView();return}D=r;ME=r.nama;shell()}
const TABS=[['pesanan','🚚 Pesanan'],['masuk','📥 Barang Masuk'],['hitung','🧮 Hitung Stok'],['minta','🛒 Minta Barang'],['riwayat','🕘 Riwayat']];
function shell(){$('app').innerHTML='<header><h1>📦 '+esc(ME)+'</h1><button id="out">Keluar</button></header><div class="tabs">'+TABS.map(t=>'<button data-t="'+t[0]+'" class="'+(t[0]==tab?'on':'')+'">'+t[1]+'</button>').join('')+'</div><main id="m"></main><div class="bar hide" id="bar"><div class="t" id="cnt"></div><button class="btn" id="go">Kirim</button></div>';
$('out').onclick=async()=>{await api('logout',{});loginView()};
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{tab=b.dataset.t;for(const k in vals)delete vals[k];shell()});view()}
function view(){const m=$('m');const bar=$('bar');bar.classList.add('hide');
if(tab=='pesanan'){let h='<div class="info">Pesanan customer yang harus disiapkan. Setelah barang keluar gudang, tekan <b>Sudah dikirim</b>.</div>';
D.orders.forEach(o=>{h+='<div class="card"><b>'+esc(o.customer)+' <span class="badge '+(o.dikirim?'Dikirim':'Menunggu')+'">'+(o.dikirim?'Dikirim':'Belum dikirim')+'</span></b><small>'+esc(o.invoice)+' • '+esc(o.tgl)+(o.kirim?' • kirim '+esc(o.kirim):'')+' • '+esc(o.metode)+'</small><div style="margin:6px 0">'+o.items.map(i=>'• '+esc(i.nama)+' — <b>'+esc(i.qty)+' '+esc(i.satuan)+'</b>').join('<br>')+'</div>'+(o.alamat?'<small>📍 '+esc(o.alamat)+'</small><br>':'')+(o.dikirim?'<small>oleh '+esc(o.dikirim_oleh)+' • '+esc(o.dikirim_waktu)+'</small>':'<button class="btn sm" data-k="'+esc(o.invoice)+'">✅ Sudah dikirim</button>')+'</div>'});
m.innerHTML=h||'<p>Belum ada pesanan.</p>';m.querySelectorAll('[data-k]').forEach(b=>b.onclick=async()=>{if(!confirm('Barang untuk '+b.dataset.k+' sudah keluar & dikirim?'))return;b.disabled=true;const r=await api('kirim',{invoice:b.dataset.k});if(r.ok)boot();else alert(r.error||'Gagal')});return}
if(tab=='riwayat'){let h='<div class="info">Pengajuan stok kamu. <b>Menunggu</b> = belum disetujui owner.</div>';
const by={};D.pengajuan.forEach(p=>{(by[p.Batch]=by[p.Batch]||[]).push(p)});Object.keys(by).reverse().forEach(b=>{const L=by[b];h+='<div class="card"><b>'+esc(L[0].Jenis=='Masuk'?'Barang Masuk':'Hitung Stok')+' <span class="badge '+esc(L[0].Status)+'">'+esc(L[0].Status)+'</span></b><small>'+esc(L[0].Waktu)+(L[0].Ref?' • '+esc(L[0].Ref):'')+'</small><div style="margin-top:5px">'+L.map(p=>'• '+esc(p.Nama)+': <b>'+esc(p.Qty)+' '+esc(p.Satuan)+'</b>').join('<br>')+'</div></div>'});
if(D.permintaan.length){h+='<h3>Permintaan barang</h3>'+D.permintaan.map(q=>'<div class="card"><b>'+esc(q.Nama)+': '+esc(q.Qty)+' '+esc(q.Satuan)+' <span class="badge '+esc(q.Status)+'">'+esc(q.Status)+'</span></b><small>'+esc(q.Waktu)+(q.Catatan?' • '+esc(q.Catatan):'')+'</small></div>').join('')}
m.innerHTML=h||'<p>Belum ada riwayat.</p>';return}
const INFO={masuk:'Isi jumlah barang yang BARU DATANG. Akan masuk ke stok setelah disetujui owner.',hitung:'Isi jumlah SEBENARNYA di gudang (stok awal / hitung fisik). Berlaku setelah disetujui owner.',minta:'Pilih barang yang perlu dipesan/ditambah. Owner akan menerima permintaannya.'};
let h='<div class="info">'+INFO[tab]+'</div>'+(tab=='masuk'?'<input id="ref" placeholder="No. PO / asal barang (boleh kosong)">':'')+'<input type="search" id="cari" placeholder="cari barang..."><div id="lst"></div>';m.innerHTML=h;
const draw=()=>{const q=$('cari').value.toLowerCase();$('lst').innerHTML=D.items.filter(i=>(i.nama+' '+i.code+' '+i.kategori).toLowerCase().includes(q)).map(i=>{const v=vals[i.code]||{q:'',u:i.isi_bal>0?'bal':'sat'};
return '<div class="it"><b>'+esc(i.nama)+'<span class="badge '+i.status+'">'+({aman:'aman',menipis:'menipis',habis:'habis',belum:'belum dihitung'})[i.status]+'</span></b><small class="mu">Stok: '+esc(stokTxt(i))+'</small><div class="row"><input inputmode="decimal" placeholder="jumlah" value="'+esc(v.q)+'" data-c="'+esc(i.code)+'"><select data-u="'+esc(i.code)+'">'+(i.isi_bal>0?'<option value="bal"'+(v.u=='bal'?' selected':'')+'>bal (isi '+fmt(i.isi_bal)+')</option>':'')+'<option value="sat"'+(v.u=='sat'?' selected':'')+'>'+esc(i.satuan)+'</option></select></div></div>'}).join('');upd()};
const cnt=()=>Object.keys(vals).filter(c=>vals[c].q!==''&&!isNaN(parseFloat(vals[c].q.replace(',','.')))).length;
const upd=()=>{$('cnt').textContent=cnt()+' barang diisi';$('go').disabled=cnt()==0};
bar.classList.remove('hide');draw();$('cari').oninput=draw;
$('lst').addEventListener('input',e=>{const c=e.target.dataset.c;if(c){vals[c]=vals[c]||{u:'sat'};vals[c].q=e.target.value;upd()}});
$('lst').addEventListener('change',e=>{const c=e.target.dataset.u;if(c){vals[c]=vals[c]||{q:''};vals[c].u=e.target.value}});
$('go').onclick=async()=>{const entries=Object.keys(vals).filter(c=>vals[c].q!==''&&!isNaN(parseFloat(vals[c].q.replace(',','.')))).map(c=>({code:c,qty:parseFloat(vals[c].q.replace(',','.')),unit:vals[c].u}));
$('go').disabled=true;const r=tab=='minta'?await api('permintaan',{entries}):await api('pengajuan',{mode:tab,ref:($('ref')||{}).value||'',entries});
if(r.ok){alert(tab=='minta'?'✅ Permintaan terkirim ke owner':'✅ Terkirim, menunggu persetujuan owner');tab='riwayat';await boot()}else{alert(r.error||'Gagal');$('go').disabled=false}}}
boot();
</script></body></html>"""


def add_staff_routes(app, sheets_getter, notify):
    """notify(kind, data) -> coroutine; ngabarin owner via Telegram."""

    async def _auth(request):
        sid = _read_cookie(request)
        if not sid:
            return None
        return await asyncio.to_thread(sheets_getter().get_staff_info, sid)

    async def page(request):
        return web.Response(text=STAFF_HTML.replace("__BIZ__", html.escape(config.BUSINESS_NAME)),
                            content_type="text/html", charset="utf-8",
                            headers={"Cache-Control": "no-store"})

    async def login(request):
        try:
            body = await request.json()
        except Exception:
            return web.json_response({"ok": False, "error": "Permintaan salah"}, status=400)
        sid = str(body.get("id", "")).strip().lower()[:40]
        key = (request.headers.get("X-Forwarded-For", request.remote or "-").split(",")[0].strip(), sid)
        now = time.time()
        _gagal[key] = [t for t in _gagal.get(key, []) if now - t < 600]
        if len(_gagal[key]) >= 5:
            return web.json_response({"ok": False, "error": "Terlalu banyak percobaan, tunggu 10 menit"}, status=429)
        st = await asyncio.to_thread(sheets_getter().verify_staff, sid, str(body.get("password", "")))
        if not st:
            _gagal[key].append(now)
            return web.json_response({"ok": False, "error": "ID atau password salah"}, status=401)
        resp = web.json_response({"ok": True, "nama": st["nama"]})
        resp.set_cookie(COOKIE, _make_cookie(st["id"]), max_age=SESSION_SECS, httponly=True,
                        secure=True, samesite="Lax", path="/staff")
        return resp

    async def logout(request):
        resp = web.json_response({"ok": True})
        resp.del_cookie(COOKIE, path="/staff")
        return resp

    async def data(request):
        st = await _auth(request)
        if not st:
            return web.json_response({"ok": False}, status=401)
        sheets = sheets_getter()
        from stokweb import _stok_items
        items = await asyncio.to_thread(_stok_items, sheets)
        orders = await asyncio.to_thread(sheets.get_orders_gudang, 40)
        peng = await asyncio.to_thread(sheets.get_pengajuan, None, st["id"])
        perm = await asyncio.to_thread(sheets.get_permintaan, st["id"], None, 30)
        peng = sorted(peng, key=lambda p: str(p.get("Waktu", "")))[-120:]
        return web.json_response({"ok": True, "nama": st["nama"], "items": items, "orders": orders,
                                  "pengajuan": peng, "permintaan": perm})

    async def _entries(sheets, body):
        from stokweb import _stok_items
        produk = {str(p["code"]).upper(): p for p in await asyncio.to_thread(_stok_items, sheets)}
        out = []
        for e in (body.get("entries") or [])[:200]:
            p = produk.get(str(e.get("code", "")).strip().upper())
            try:
                qty = float(e.get("qty"))
            except (TypeError, ValueError):
                continue
            if p is None or qty < 0 or qty > 1_000_000:
                continue
            if e.get("unit") == "bal":
                if p["isi_bal"] <= 0:
                    continue
                qty *= p["isi_bal"]
            out.append({"item_code": p["code"], "nama": p["nama"], "qty": qty, "satuan": p["satuan"]})
        return out

    async def pengajuan(request):
        st = await _auth(request)
        if not st:
            return web.json_response({"ok": False, "error": "Login dulu"}, status=401)
        body = await request.json()
        mode = body.get("mode")
        if mode not in ("masuk", "hitung"):
            return web.json_response({"ok": False, "error": "Mode salah"}, status=400)
        sheets = sheets_getter()
        ents = await _entries(sheets, body)
        if mode == "masuk":
            ents = [e for e in ents if e["qty"] > 0]
        if not ents:
            return web.json_response({"ok": False, "error": "Belum ada jumlah yang valid"}, status=400)
        ref = str(body.get("ref", ""))[:60] if mode == "masuk" else ""
        jenis = "Masuk" if mode == "masuk" else "Hitung"
        batch = await asyncio.to_thread(sheets.add_pengajuan, st["nama"], jenis, ents, ref)
        try:
            await notify("pengajuan", {"batch": batch, "staff": st["nama"], "jenis": jenis, "ents": ents, "ref": ref})
        except Exception:
            logger.exception("gagal notif pengajuan")
        return web.json_response({"ok": True, "batch": batch})

    async def permintaan(request):
        st = await _auth(request)
        if not st:
            return web.json_response({"ok": False, "error": "Login dulu"}, status=401)
        body = await request.json()
        sheets = sheets_getter()
        ents = [e for e in await _entries(sheets, body) if e["qty"] > 0]
        if not ents:
            return web.json_response({"ok": False, "error": "Belum ada jumlah yang valid"}, status=400)
        await asyncio.to_thread(sheets.add_permintaan, st["nama"], ents)
        try:
            await notify("permintaan", {"staff": st["nama"], "ents": ents})
        except Exception:
            logger.exception("gagal notif permintaan")
        return web.json_response({"ok": True})

    async def kirim(request):
        st = await _auth(request)
        if not st:
            return web.json_response({"ok": False, "error": "Login dulu"}, status=401)
        body = await request.json()
        inv = str(body.get("invoice", ""))[:40]
        sheets = sheets_getter()
        orders = await asyncio.to_thread(sheets.get_order_items, inv)
        if not orders or str(orders[0].get("Status", "")) == "Batal":
            return web.json_response({"ok": False, "error": "Pesanan tidak ditemukan"}, status=404)
        await asyncio.to_thread(sheets.set_pengiriman, inv, st["nama"])
        try:
            await notify("kirim", {"invoice": inv, "customer": orders[0].get("Nama_Customer", ""), "staff": st["nama"]})
        except Exception:
            logger.exception("gagal notif kirim")
        return web.json_response({"ok": True})

    app.router.add_get("/staff", page)
    app.router.add_post("/staff/api/login", login)
    app.router.add_post("/staff/api/logout", logout)
    app.router.add_get("/staff/api/data", data)
    app.router.add_post("/staff/api/pengajuan", pengajuan)
    app.router.add_post("/staff/api/permintaan", permintaan)
    app.router.add_post("/staff/api/kirim", kirim)
