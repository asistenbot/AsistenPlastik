"""Halaman stok gudang (input pegawai) + dashboard stok (owner)."""

import asyncio
import html
import json
import logging

from aiohttp import web

import config

logger = logging.getLogger(__name__)

GUDANG_HTML = """<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Stok Gudang</title><style>
:root{--g:#0f7b6c;--bg:#f4f7f6;--ink:#1c2b28;--mu:#6b7c78;--ln:#dbe4e1}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.4 system-ui,sans-serif}
header{background:var(--g);color:#fff;padding:14px 16px}header h1{margin:0;font-size:19px}
.tabs{display:flex;background:#fff;border-bottom:1px solid var(--ln);position:sticky;top:0;z-index:5}
.tabs button{flex:1;padding:12px 4px;border:0;background:none;font-size:15px;font-weight:600;color:var(--mu);border-bottom:3px solid transparent}
.tabs button.on{color:var(--g);border-color:var(--g)}
main{max-width:720px;margin:0 auto;padding:10px 12px 130px}
.info{background:#e7f5f2;border:1px solid #bfe3dc;border-radius:10px;padding:10px 12px;font-size:14px;margin:8px 0}
input[type=text],input[type=search],select{width:100%;padding:10px;border:1px solid var(--ln);border-radius:8px;font:inherit;background:#fff}
.it{background:#fff;border:1px solid var(--ln);border-radius:12px;padding:10px 12px;margin:8px 0}
.it b{display:block}.it small{color:var(--mu)}
.row{display:flex;gap:8px;margin-top:8px}.row input{flex:1.2;padding:10px;border:1px solid var(--ln);border-radius:8px;font-size:17px;text-align:center}.row select{flex:1}
.bar{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid var(--ln);padding:10px 14px;display:flex;gap:10px;align-items:center}
.bar .t{flex:1;font-size:14px;color:var(--mu)}.bar button{background:var(--g);color:#fff;border:0;border-radius:10px;padding:13px 20px;font-size:16px;font-weight:600}
.bar button:disabled{opacity:.5}.badge{display:inline-block;font-size:12px;padding:2px 8px;border-radius:10px;margin-left:6px}
.menipis{background:#fff0c9;color:#7a5a00}.habis{background:#ffd9d6;color:#9a1b12}.aman{background:#d9f3e4;color:#14633a}.belum{background:#e8e8e8;color:#555}
.lbl{font-size:13px;color:var(--mu);margin:10px 2px 4px}
</style></head><body>
<header><h1>📦 Stok Gudang — __BIZ__</h1></header>
<div class="tabs"><button id="t_hitung" class="on">Hitung / Stok Awal</button><button id="t_masuk">Barang Masuk</button><button id="t_lihat">Lihat Stok</button></div>
<main>
<div class="info" id="info"></div>
<div class="lbl">Nama kamu</div><input type="text" id="oleh" placeholder="mis. Budi">
<div id="extra"></div>
<div class="lbl">Cari barang</div><input type="search" id="cari" placeholder="ketik nama / ukuran...">
<div id="list"></div></main>
<div class="bar" id="bar"><div class="t" id="cnt">0 barang diisi</div><button id="go" disabled>Simpan</button></div>
<script>
const TOKEN=location.pathname.split('/')[2];let D=[],mode='hitung';const vals={};
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>(Math.round(n*100)/100).toLocaleString('id-ID');
function stokTxt(i){if(i.stok===null)return 'belum dihitung';let t=fmt(i.stok)+' '+i.satuan;if(i.isi_bal>0&&i.stok>=i.isi_bal){const b=Math.floor(i.stok/i.isi_bal),s=i.stok-b*i.isi_bal;t+=' ('+b+' bal'+(s>0?' + '+fmt(s)+' '+i.satuan:'')+')'}return t}
const INFO={hitung:'Isi jumlah SEBENARNYA yang ada di gudang sekarang (hitung fisik). Dipakai buat stok awal & koreksi. Barang yang gak diisi gak berubah.',masuk:'Isi jumlah barang yang BARU DATANG. Stok akan ditambah.',lihat:'Stok terkini semua barang.'};
function render(){const q=document.getElementById('cari').value.toLowerCase();document.getElementById('info').textContent=INFO[mode];
const ex=document.getElementById('extra');ex.innerHTML=mode=='masuk'?'<div class="lbl">No. PO / Catatan (boleh kosong)</div><input type="text" id="ref" placeholder="mis. PO-20261028-001 / dari CSB">':'';
let h='';D.filter(i=>(i.nama+' '+i.code+' '+i.kategori).toLowerCase().includes(q)).forEach(i=>{
h+='<div class="it"><b>'+esc(i.nama)+'<span class="badge '+i.status+'">'+({aman:'aman',menipis:'menipis',habis:'habis',belum:'belum dihitung'})[i.status]+'</span></b><small>Stok sekarang: '+esc(stokTxt(i))+'</small>';
if(mode!='lihat'){const v=vals[i.code]||{q:'',u:i.isi_bal>0?'bal':'sat'};
h+='<div class="row"><input inputmode="decimal" placeholder="'+(mode=='hitung'?'jumlah di gudang':'jumlah datang')+'" value="'+esc(v.q)+'" data-c="'+esc(i.code)+'"><select data-u="'+esc(i.code)+'">'+(i.isi_bal>0?'<option value="bal"'+(v.u=='bal'?' selected':'')+'>bal (isi '+fmt(i.isi_bal)+')</option>':'')+'<option value="sat"'+(v.u=='sat'?' selected':'')+'>'+esc(i.satuan)+'</option></select></div>'}
h+='</div>'});document.getElementById('list').innerHTML=h||'<p>Gak ada barang.</p>';
document.getElementById('bar').style.display=mode=='lihat'?'none':'flex';upd()}
function upd(){const n=Object.values(vals).filter(v=>v.q!==''&&!isNaN(parseFloat(v.q.replace(',','.')))).length;document.getElementById('cnt').textContent=n+' barang diisi';document.getElementById('go').disabled=n==0||!document.getElementById('oleh').value.trim()}
document.getElementById('list').addEventListener('input',e=>{const c=e.target.dataset.c;if(c){vals[c]=vals[c]||{u:'sat'};vals[c].q=e.target.value;upd()}});
document.getElementById('list').addEventListener('change',e=>{const c=e.target.dataset.u;if(c){vals[c]=vals[c]||{q:''};vals[c].u=e.target.value}});
document.getElementById('cari').oninput=()=>render();
document.getElementById('oleh').oninput=e=>{try{localStorage.setItem('oleh',e.target.value)}catch(_){}upd()};
try{document.getElementById('oleh').value=localStorage.getItem('oleh')||''}catch(_){}
['hitung','masuk','lihat'].forEach(m=>document.getElementById('t_'+m).onclick=()=>{mode=m;for(const k in vals)delete vals[k];['hitung','masuk','lihat'].forEach(x=>document.getElementById('t_'+x).classList.toggle('on',x==m));render()});
async function load(){const r=await fetch('/gudang/'+TOKEN+'/data');const j=await r.json();D=j.items;render()}
document.getElementById('go').onclick=async()=>{const b=document.getElementById('go');b.disabled=true;b.textContent='Menyimpan...';
const entries=Object.keys(vals).filter(c=>vals[c].q!==''&&!isNaN(parseFloat(vals[c].q.replace(',','.')))).map(c=>({code:c,qty:parseFloat(vals[c].q.replace(',','.')),unit:vals[c].u}));
const ref=document.getElementById('ref');
try{const r=await fetch('/gudang/'+TOKEN,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({mode,oleh:document.getElementById('oleh').value.trim(),ref:ref?ref.value:'',entries})});
const j=await r.json();if(!r.ok||!j.ok)throw new Error(j.error||'Gagal');alert('✅ Tersimpan ('+j.n+' barang)');for(const k in vals)delete vals[k];await load()}catch(err){alert('Gagal menyimpan: '+err.message)}b.textContent='Simpan';upd()};
load();
</script></body></html>"""

DASH_HTML = """<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Dashboard Stok</title><style>
:root{--g:#0f7b6c;--bg:#f4f7f6;--ink:#1c2b28;--mu:#6b7c78;--ln:#dbe4e1}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.4 system-ui,sans-serif}
header{background:var(--g);color:#fff;padding:14px 16px}header h1{margin:0;font-size:19px}
main{max-width:980px;margin:0 auto;padding:12px}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.card{background:#fff;border:1px solid var(--ln);border-radius:12px;padding:10px;text-align:center;cursor:pointer}
.card b{display:block;font-size:24px}.card span{font-size:12px;color:var(--mu)}
.card.m b{color:#b27a00}.card.h b{color:#c0281c}.card.a b{color:#14633a}.card.b b{color:#666}
input[type=search]{width:100%;padding:10px;border:1px solid var(--ln);border-radius:8px;font:inherit;margin:12px 0 8px}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--ln);border-radius:12px;overflow:hidden}
th,td{padding:8px 10px;border-bottom:1px solid var(--ln);text-align:left;vertical-align:middle}th{font-size:12px;color:var(--mu);background:#f0f5f3}
td.n{text-align:right;white-space:nowrap}tr.menipis td:first-child{border-left:4px solid #e0a800}tr.habis td:first-child{border-left:4px solid #d9392b}tr.belum td:first-child{border-left:4px solid #bbb}tr.aman td:first-child{border-left:4px solid #2e9e63}
td input{width:70px;padding:6px;border:1px solid var(--ln);border-radius:6px;text-align:right;font:inherit}
.btn{background:var(--g);color:#fff;border:0;border-radius:8px;padding:10px 14px;font:inherit;font-weight:600}
h2{font-size:15px;margin:20px 2px 6px}.mut{font-size:13px;color:var(--mu)}.mut div{padding:4px 0;border-bottom:1px solid var(--ln)}
@media(max-width:640px){.cards{grid-template-columns:repeat(2,1fr)}th:nth-child(n+5),td:nth-child(n+5){display:none}}
</style></head><body><header><h1>📊 Dashboard Stok — __BIZ__</h1></header><main>
<div class="cards"><div class="card h" data-f="habis"><b id="c_h">0</b><span>Habis</span></div><div class="card m" data-f="menipis"><b id="c_m">0</b><span>Menipis</span></div>
<div class="card a" data-f="aman"><b id="c_a">0</b><span>Aman</span></div><div class="card b" data-f="belum"><b id="c_b">0</b><span>Belum dihitung</span></div></div>
<div style="display:flex;gap:8px;margin-top:12px"><button class="btn" id="belanja">📋 Salin daftar belanja (yang menipis/habis)</button><button class="btn" id="semua" style="background:#555">Tampilkan semua</button></div>
<input type="search" id="cari" placeholder="cari barang...">
<table><thead><tr><th>Barang</th><th class="n">Stok</th><th class="n">Min</th><th>Status</th><th class="n">Isi 1 bal</th><th>Supplier</th></tr></thead><tbody id="tb"></tbody></table>
<h2>Gerakan stok terakhir</h2><div class="mut" id="mut"></div></main>
<script>
const TOKEN=location.pathname.split('/')[2];let D=[],F='';
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>(Math.round(n*100)/100).toLocaleString('id-ID');
function stokTxt(i){if(i.stok===null)return '-';let t=fmt(i.stok)+' '+esc(i.satuan);if(i.isi_bal>0&&i.stok>=i.isi_bal)t+=' <small>('+(Math.round(i.stok/i.isi_bal*10)/10)+' bal)</small>';return t}
const ORD={habis:0,menipis:1,belum:2,aman:3};
function render(){const q=document.getElementById('cari').value.toLowerCase();let L=D.filter(i=>(!F||i.status==F)&&(i.nama+' '+i.code+' '+i.kategori).toLowerCase().includes(q));
L.sort((a,b)=>ORD[a.status]-ORD[b.status]||a.nama.localeCompare(b.nama));
document.getElementById('tb').innerHTML=L.map(i=>'<tr class="'+i.status+'"><td><b>'+esc(i.nama)+'</b><br><small style="color:#888">'+esc(i.code)+'</small></td><td class="n">'+stokTxt(i)+'</td><td class="n"><input data-k="min" data-c="'+esc(i.code)+'" value="'+(i.min||'')+'" inputmode="decimal"></td><td>'+({aman:'🟢 Aman',menipis:'🟡 Menipis',habis:'🔴 Habis',belum:'⚪ Belum dihitung'})[i.status]+'</td><td class="n"><input data-k="isi_bal" data-c="'+esc(i.code)+'" value="'+(i.isi_bal||'')+'" inputmode="decimal"></td><td>'+esc(i.supplier||'')+'</td></tr>').join('');
const c=s=>D.filter(i=>i.status==s).length;['h:habis','m:menipis','a:aman','b:belum'].forEach(x=>{const[a,b]=x.split(':');document.getElementById('c_'+a).textContent=c(b)})}
document.getElementById('tb').addEventListener('change',async e=>{const c=e.target.dataset.c;if(!c)return;const v=parseFloat(String(e.target.value).replace(',','.'))||0;
await fetch('/dashboard/'+TOKEN+'/set',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:c,field:e.target.dataset.k,value:v})});load()});
document.querySelectorAll('.card').forEach(x=>x.onclick=()=>{F=F==x.dataset.f?'':x.dataset.f;render()});
document.getElementById('semua').onclick=()=>{F='';document.getElementById('cari').value='';render()};
document.getElementById('cari').oninput=render;
document.getElementById('belanja').onclick=()=>{const L=D.filter(i=>i.status=='menipis'||i.status=='habis').map(i=>{const need=Math.max((i.min||0)*2-(i.stok||0),0);let t='• '+i.nama+' — stok '+fmt(i.stok||0)+' '+i.satuan;if(need>0){t+=' → order ±'+fmt(need)+' '+i.satuan;if(i.isi_bal>0)t+=' (±'+Math.ceil(need/i.isi_bal)+' bal)'}return t});
const txt='Daftar belanja:\\n'+(L.join('\\n')||'(semua aman)');navigator.clipboard?navigator.clipboard.writeText(txt).then(()=>alert('Tersalin:\\n\\n'+txt)):alert(txt)};
async function load(){const r=await fetch('/dashboard/'+TOKEN+'/data');const j=await r.json();D=j.items;render();
document.getElementById('mut').innerHTML=j.mutasi.map(m=>'<div>'+esc(m.Waktu)+' — <b>'+esc(m.Jenis)+'</b> '+esc(m.Nama||m.Item_Code)+': '+esc(m.Qty)+' '+esc(m.Satuan)+(m.Oleh?' ('+esc(m.Oleh)+')':'')+(m.Ref?' • '+esc(m.Ref):'')+'</div>').join('')||'Belum ada.'}
load();setInterval(load,60000);
</script></body></html>"""


def _stok_items(sheets):
    items = sheets.get_stok_all()
    sup = {str(r.get("Item_Code", "")).strip(): r.get("Supplier", "") for r in sheets.get_price_list()}
    for i in items:
        i["supplier"] = sup.get(i["code"], "")
    return items


def add_stok_routes(app, sheets_getter):
    async def _link(request, perans):
        sheets = sheets_getter()
        link = await asyncio.to_thread(sheets.get_link_by_token, request.match_info["token"])
        nama = str((link or {}).get("Nama_Customer", ""))
        if not link or nama not in perans:
            return None
        return link

    async def gudang_page(request):
        if not await _link(request, ("@gudang", "@owner")):
            return web.Response(status=404, text="Link tidak valid.")
        return web.Response(text=GUDANG_HTML.replace("__BIZ__", html.escape(config.BUSINESS_NAME)),
                            content_type="text/html", charset="utf-8")

    async def gudang_data(request):
        if not await _link(request, ("@gudang", "@owner")):
            return web.json_response({"ok": False}, status=404)
        items = await asyncio.to_thread(_stok_items, sheets_getter())
        return web.json_response({"ok": True, "items": items})

    async def gudang_submit(request):
        if not await _link(request, ("@gudang", "@owner")):
            return web.json_response({"ok": False, "error": "Link tidak valid"}, status=404)
        try:
            body = await request.json()
            mode = body.get("mode")
            if mode not in ("hitung", "masuk"):
                return web.json_response({"ok": False, "error": "Mode salah"}, status=400)
            oleh = str(body.get("oleh", ""))[:40].strip()
            if not oleh:
                return web.json_response({"ok": False, "error": "Isi nama kamu dulu"}, status=400)
            sheets = sheets_getter()
            produk = {str(p["code"]).upper(): p for p in await asyncio.to_thread(_stok_items, sheets)}
            ents = []
            for e in (body.get("entries") or [])[:300]:
                p = produk.get(str(e.get("code", "")).strip().upper())
                try:
                    qty = float(e.get("qty"))
                except (TypeError, ValueError):
                    continue
                if p is None or qty < 0 or qty > 1_000_000 or (mode == "masuk" and qty == 0):
                    continue
                if e.get("unit") == "bal":
                    if p["isi_bal"] <= 0:
                        continue
                    qty *= p["isi_bal"]
                ents.append({"item_code": p["code"], "nama": p["nama"], "jenis": "Hitung" if mode == "hitung" else "Masuk",
                             "qty": qty, "satuan": p["satuan"], "ref": str(body.get("ref", ""))[:60] if mode == "masuk" else "",
                             "catatan": "", "oleh": oleh})
            if not ents:
                return web.json_response({"ok": False, "error": "Belum ada jumlah yang valid"}, status=400)
            n = await asyncio.to_thread(sheets.add_mutasi, ents)
            return web.json_response({"ok": True, "n": n})
        except Exception:
            logger.exception("gagal simpan stok")
            return web.json_response({"ok": False, "error": "Server bermasalah"}, status=500)

    async def dash_page(request):
        if not await _link(request, ("@owner",)):
            return web.Response(status=404, text="Link tidak valid.")
        return web.Response(text=DASH_HTML.replace("__BIZ__", html.escape(config.BUSINESS_NAME)),
                            content_type="text/html", charset="utf-8")

    async def dash_data(request):
        if not await _link(request, ("@owner",)):
            return web.json_response({"ok": False}, status=404)
        sheets = sheets_getter()
        items = await asyncio.to_thread(_stok_items, sheets)
        mut = await asyncio.to_thread(sheets.get_mutasi_recent, 15)
        return web.json_response({"ok": True, "items": items, "mutasi": mut})

    async def dash_set(request):
        if not await _link(request, ("@owner",)):
            return web.json_response({"ok": False}, status=404)
        body = await request.json()
        field = body.get("field")
        if field not in ("min", "isi_bal"):
            return web.json_response({"ok": False}, status=400)
        try:
            val = max(0.0, float(body.get("value")))
        except (TypeError, ValueError):
            return web.json_response({"ok": False}, status=400)
        ok = await asyncio.to_thread(sheets_getter().set_stok_setting, str(body.get("code", "")), field, val)
        return web.json_response({"ok": bool(ok)})

    app.router.add_get("/gudang/{token}", gudang_page)
    app.router.add_get("/gudang/{token}/data", gudang_data)
    app.router.add_post("/gudang/{token}", gudang_submit)
    app.router.add_get("/dashboard/{token}", dash_page)
    app.router.add_get("/dashboard/{token}/data", dash_data)
    app.router.add_post("/dashboard/{token}/set", dash_set)
