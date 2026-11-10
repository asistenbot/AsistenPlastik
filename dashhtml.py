"""Halaman dashboard owner (HTML satu file, tanpa library luar)."""

DASH_HTML = r"""<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#070B14"><meta name="color-scheme" content="dark"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin><link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;500;600;700;800&display=swap" rel="stylesheet"><title>Dashboard Owner</title><style>
:root{--bg:#070B14;--bg2:#0C1322;--sf:rgba(255,255,255,.045);--sf2:rgba(255,255,255,.08);--ln:rgba(255,255,255,.09);--ln2:rgba(255,255,255,.16);
--tx:#E9EEF7;--mu:#8A97AD;--cy:#5CE1FF;--vi:#A78BFA;--pk:#FF7AC6;--ok:#3DDC97;--amb:#FFB547;--red:#FF5D73;--blu:#5CE1FF;--g:#5CE1FF;--ink:#E9EEF7;
--iri:linear-gradient(115deg,#5CE1FF 0%,#A78BFA 45%,#FF7AC6 75%,#FFD27A 100%);--r:16px}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%;background:var(--bg)}input,select,button{font-size:16px}
body{margin:0;min-height:100vh;color:var(--tx);font:15px/1.5 'Sora',system-ui,sans-serif;font-variant-numeric:tabular-nums;
background:radial-gradient(1200px 600px at 85% -10%,rgba(167,139,250,.16),transparent 60%),radial-gradient(900px 500px at -10% 10%,rgba(92,225,255,.12),transparent 60%),var(--bg);background-attachment:fixed}
button,input,select{font-family:inherit}::selection{background:rgba(92,225,255,.35)}
:focus-visible{outline:2px solid var(--cy);outline-offset:2px}
header{padding:16px max(16px,env(safe-area-inset-right)) 12px max(16px,env(safe-area-inset-left));display:flex;align-items:center;gap:12px;flex-wrap:wrap;border-bottom:1px solid var(--ln);background:rgba(7,11,20,.6);-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px)}
.brand{display:flex;align-items:center;gap:12px;flex:1;min-width:200px}
.logo{width:40px;height:40px;border-radius:12px;background:var(--iri);color:#0A0F1C;display:grid;place-items:center;font-weight:800;font-size:15px;letter-spacing:-.5px;flex:0 0 auto;box-shadow:0 0 24px rgba(167,139,250,.45)}
header h1{margin:0;font-size:16.5px;font-weight:700;letter-spacing:-.3px;line-height:1.2}header small{display:block;color:var(--mu);font-size:12px;font-weight:400;letter-spacing:.2px}
.hctl{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
header input,.chip,.ib{-webkit-appearance:none;border:1px solid var(--ln2);background:var(--sf);color:var(--tx);border-radius:12px;padding:8px 12px;font:inherit;font-size:13.5px;font-weight:600;cursor:pointer;color-scheme:dark}
.chip:hover,.ib:hover{background:var(--sf2);border-color:rgba(92,225,255,.5)}
.tabs{display:flex;gap:6px;overflow-x:auto;padding:10px max(12px,env(safe-area-inset-left));position:sticky;top:0;z-index:5;-webkit-overflow-scrolling:touch;scrollbar-width:none;background:rgba(7,11,20,.72);-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);border-bottom:1px solid var(--ln)}
.tabs::-webkit-scrollbar{display:none}
.tabs button{-webkit-appearance:none;flex:0 0 auto;padding:9px 15px;border:1px solid var(--ln);background:var(--sf);font:inherit;font-size:13.5px;font-weight:600;color:var(--mu);border-radius:999px;white-space:nowrap;cursor:pointer}
.tabs button:hover{color:var(--tx)}
.tabs button.on{color:#06101E;background:var(--cy);border-color:var(--cy);box-shadow:0 0 18px rgba(92,225,255,.35)}
.tabs button .pill{background:var(--pk);color:#1A0612;margin-left:3px}
main{max-width:1120px;margin:0 auto;padding:16px 14px 48px}.pane{display:none}.pane.on{display:block;animation:in .22s ease-out}
@keyframes in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--ln);border:1px solid var(--ln);border-radius:var(--r);overflow:hidden;margin:0 0 12px}
.card{background:#0B111E;padding:14px 16px;text-align:left;min-width:0}
.card span{display:flex;align-items:center;gap:7px;font-size:12px;color:var(--mu);font-weight:500;letter-spacing:.2px}
.card span::before{content:"";width:7px;height:7px;border-radius:50%;background:#4A5670;flex:0 0 auto}
.card b{display:block;font-size:21px;font-weight:700;letter-spacing:-.6px;margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.card small{display:block;font-size:11.5px;color:var(--mu);margin-top:2px}
.grn span::before{background:var(--ok);box-shadow:0 0 8px var(--ok)}.amb span::before{background:var(--amb);box-shadow:0 0 8px var(--amb)}.red span::before{background:var(--red);box-shadow:0 0 8px var(--red)}.blu span::before{background:var(--cy);box-shadow:0 0 8px var(--cy)}
.red b{color:var(--red)}
.card.stok{cursor:pointer}.card.stok:hover{background:#101829}
h2{font-size:15.5px;font-weight:700;letter-spacing:-.2px;margin:28px 2px 10px}
h3{font-weight:700}
.pane>h2:first-child{margin-top:6px}
.box{background:var(--sf);border:1px solid var(--ln);border-radius:var(--r);padding:13px 15px;margin:8px 0}
.mut{font-size:13.5px;color:var(--mu)}.mut div{padding:7px 0;border-bottom:1px solid var(--ln)}.mut div:last-child{border-bottom:0}.mut b{color:var(--tx)}
.hb{display:flex;align-items:center;gap:10px;margin:9px 0;font-size:13.5px}.hb .l{flex:0 0 38%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:500}
.hb .t{flex:1;background:rgba(255,255,255,.06);border-radius:999px;height:8px;position:relative}.hb .t i{display:block;height:100%;border-radius:999px;background:linear-gradient(90deg,#3B82F6,var(--cy))}
.hb:first-child .t i{background:var(--iri)}
.hb .v{flex:0 0 auto;min-width:86px;text-align:right;font-weight:600}
.vc{display:flex;align-items:flex-end;gap:5px;height:150px;margin-top:6px}.vc div{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;height:100%}
.vc i{display:block;width:100%;max-width:44px;background:linear-gradient(180deg,rgba(92,225,255,.55),rgba(92,225,255,.08));border-radius:8px 8px 3px 3px;min-height:2px}.vc div:last-child i{background:var(--iri);box-shadow:0 0 22px rgba(167,139,250,.5)}
.vc small{font-size:10.5px;color:var(--mu);margin-top:5px;white-space:nowrap}
.vc2 i{width:46%;background:linear-gradient(180deg,var(--ok),rgba(61,220,151,.15))!important;box-shadow:none!important}.vc2 i+i{background:linear-gradient(180deg,var(--red),rgba(255,93,115,.15))!important}.vc2 div{flex-direction:row;align-items:flex-end;justify-content:center;gap:3px;position:relative;padding-bottom:18px}.vc2 small{position:absolute;bottom:0}
.lg{font-size:12px;color:var(--mu);margin-top:8px}.lg b{display:inline-block;width:9px;height:9px;border-radius:3px;margin:0 5px 0 10px;vertical-align:0}
.lg b:first-child{background:var(--ok)!important}.lg b+b{background:var(--red)!important}
table{width:100%;border-collapse:separate;border-spacing:0;background:var(--sf);border:1px solid var(--ln);border-radius:var(--r);overflow:hidden}
th,td{padding:12px 13px;border-bottom:1px solid var(--ln);text-align:left;vertical-align:middle}tr:last-child td{border-bottom:0}
th{font-size:12px;font-weight:600;color:var(--mu);background:rgba(255,255,255,.03);letter-spacing:.2px}
tbody tr:hover td{background:rgba(92,225,255,.035)}
td .btn.s{margin:2px 0}td.n{text-align:right;white-space:nowrap;font-weight:600}
tr.menipis td:first-child{box-shadow:inset 3px 0 var(--amb)}tr.habis td:first-child{box-shadow:inset 3px 0 var(--red)}tr.belum td:first-child{box-shadow:inset 3px 0 #4A5670}tr.aman td:first-child{box-shadow:inset 3px 0 var(--ok)}
main input:not([type=checkbox]),main select,main textarea{background:rgba(255,255,255,.05)!important;color:var(--tx)!important;border:1px solid var(--ln2)!important;border-radius:12px!important;color-scheme:dark}
main input::placeholder{color:#5F6C83}
td input[type=text],td input:not([type]){width:72px;padding:7px;text-align:right;font:inherit}
input[type=search]{width:100%;padding:12px 14px;font:inherit;margin:12px 0 10px}
input[type=checkbox]{width:18px;height:18px;accent-color:var(--cy)}
.btn{-webkit-appearance:none;background:var(--cy);color:#06101E;border:0;border-radius:12px;padding:10px 16px;font:inherit;font-size:14px;font-weight:700;cursor:pointer;line-height:1.2;transition:box-shadow .15s,transform .1s}
.btn:hover{box-shadow:0 0 0 1px var(--cy),0 0 20px rgba(92,225,255,.4)}.btn:active{transform:scale(.98)}.btn:disabled{opacity:.45}
.btn.s{padding:7px 11px;font-size:12.5px;border-radius:10px}
.btn.k{background:var(--sf2);color:var(--tx);box-shadow:inset 0 0 0 1px var(--ln2)}.btn.k:hover{box-shadow:inset 0 0 0 1px rgba(92,225,255,.6)}
.btn.r{background:var(--red);color:#1A0509}
a.btn{text-decoration:none}
.pill{display:inline-block;font-size:11.5px;padding:3px 10px;border-radius:999px;font-weight:600;white-space:nowrap;border:1px solid transparent}
.p-belum{background:rgba(255,93,115,.12);color:#FF8A9B;border-color:rgba(255,93,115,.3)}.p-sudah{background:rgba(61,220,151,.12);color:#6FE8B3;border-color:rgba(61,220,151,.3)}.p-x{background:var(--sf2);color:var(--mu)}.p-telat{background:var(--red);color:#1A0509}
.act{background:rgba(255,181,71,.08);border:1px solid rgba(255,181,71,.3);border-radius:var(--r);padding:6px 14px;margin:8px 0;font-size:14px}.act div{padding:8px 0;border-bottom:1px solid var(--ln)}.act div:last-child{border-bottom:0}
.empty{color:var(--mu);padding:14px 16px;font-size:13.5px;background:transparent;border:1px dashed var(--ln2);border-radius:var(--r)}
small{color:inherit}
/* hero: yang perlu diurus — satu-satunya elemen pelangi besar */
.todo{position:relative;border-radius:22px;padding:18px 16px 10px;margin:4px 0 20px;background:linear-gradient(#0D1424,#0D1424) padding-box,var(--iri) border-box;border:1.5px solid transparent;box-shadow:0 0 0 1px rgba(255,255,255,.02),0 20px 60px -20px rgba(167,139,250,.45)}
.todo::before{content:"";position:absolute;inset:0;border-radius:inherit;background:radial-gradient(500px 160px at 0% 0%,rgba(92,225,255,.14),transparent 70%),radial-gradient(400px 160px at 100% 0%,rgba(255,122,198,.12),transparent 70%);pointer-events:none}
.todo h3{position:relative;margin:0 0 12px;font-size:19px;letter-spacing:-.4px;background:var(--iri);-webkit-background-clip:text;background-clip:text;color:transparent;display:inline-block}
.todo button{position:relative;-webkit-appearance:none;display:flex;align-items:center;gap:12px;width:100%;text-align:left;background:rgba(255,255,255,.045);border:1px solid var(--ln);border-radius:14px;padding:12px 12px;margin:0 0 8px;font:inherit;font-size:14px;font-weight:500;color:var(--tx);cursor:pointer;transition:border-color .15s,background .15s}
.todo button:hover{background:rgba(255,255,255,.08);border-color:rgba(92,225,255,.45)}
.todo button .ic{font-size:18px;flex:0 0 auto;width:34px;height:34px;display:grid;place-items:center;border-radius:10px;background:rgba(255,255,255,.06)}.todo button .tx{flex:1}
.todo button .go{flex:0 0 auto;font-size:12px;font-weight:700;color:#06101E;background:var(--cy);border-radius:999px;padding:5px 11px}
.todo.clear{background:linear-gradient(#0D1424,#0D1424) padding-box,linear-gradient(115deg,var(--ok),var(--cy)) border-box}.todo.clear h3{background:linear-gradient(115deg,var(--ok),var(--cy));-webkit-background-clip:text;background-clip:text}.todo.clear p{position:relative;margin:0 0 8px;color:var(--mu)}
.sec{display:flex;align-items:baseline;justify-content:space-between;gap:8px;margin:24px 2px 10px}.sec h2{margin:0}.sec span{font-size:12px;color:var(--mu);font-weight:500}
.grid2{display:grid;grid-template-columns:1fr;gap:0 16px}
details{color:var(--tx)}summary{cursor:pointer}
@media(prefers-reduced-motion:reduce){.pane.on{animation:none}.btn{transition:none}}
@media(min-width:900px){.card b{font-size:24px}.grid2{grid-template-columns:1fr 1fr}}
@media(max-width:700px){.cards{grid-template-columns:repeat(2,1fr)}header{padding-top:14px;padding-bottom:12px}#prAll{display:none}.chip,.ib{padding:7px 10px;font-size:13px}td:first-child{width:62%}td .btn.s{padding:6px 9px;font-size:12px}.hb .l{flex-basis:44%}.hide-s{display:none}header .hctl{width:100%;flex-wrap:nowrap}header input{flex:1;width:0;min-width:110px}}
@media(min-width:1180px){
body{display:grid;grid-template-columns:240px 1fr;grid-template-rows:auto 1fr}
header{grid-column:1/-1}
.tabs{grid-column:1;flex-direction:column;align-self:start;position:sticky;top:0;padding:18px 14px;border:0;background:none;overflow:visible;gap:4px;-webkit-backdrop-filter:none;backdrop-filter:none}
.tabs button{border:1px solid transparent;background:none;text-align:left;border-radius:12px;padding:11px 14px;font-size:14.5px}
.tabs button:hover{background:var(--sf)}
.tabs button.on{background:var(--sf2);color:var(--tx);border-color:var(--ln2);box-shadow:inset 3px 0 0 var(--cy)}
main{grid-column:2;margin:0;max-width:1080px;padding:20px 26px 56px}
}
#phead{display:none}
@media print{
html,body{background:#fff!important;color:#000!important;display:block!important}.card,.box,table,th,td,.cards,.empty,.act{background:#fff!important;color:#000!important}.card b,.mut,.mut b,th,small,.card span{color:#000!important}.hb .t i,.vc i{background:#333!important;box-shadow:none!important}.todo{display:none}
@page{size:A4;margin:12mm}
body{background:#fff;color:#000;font-size:11pt}
header,.tabs,.btn,button,input[type=search],#kbSel,.noprint,td:last-child button{display:none!important}
#phead{display:block;border-bottom:2px solid #000;margin-bottom:10px;padding-bottom:4px}#phead h1{margin:0;font-size:16pt}#phead div{font-size:10pt}
main{max-width:none;padding:0}.pane{display:none}.pane.on{display:block}
body.printall .pane{display:block}body.printall .pane#p_stok,body.printall .pane#p_gudang{display:none}body.printall .pane+.pane{page-break-before:always}
.card,.box,.act,tr{break-inside:avoid;border-color:#888!important;box-shadow:none}
.cards{grid-template-columns:repeat(4,1fr)}
.hb .t i,.vc i,.pill{-webkit-print-color-adjust:exact;print-color-adjust:exact}
table{font-size:10pt}th{background:#eee!important;-webkit-print-color-adjust:exact;print-color-adjust:exact}
td input{border:0!important;background:none!important;width:auto!important;text-align:right}
.hide-s{display:table-cell!important}
}
details summary::-webkit-details-marker{display:none}details[open] summary .arw{transform:rotate(180deg)}
</style><script src="/thermal.js"></script></head><body>
<header><div class="brand"><div class="logo">AS</div><div><h1>__BIZ__</h1><small id="hsub">Dashboard owner</small></div></div><div class="hctl"><input type="month" id="bln" placeholder="2026-10" pattern="[0-9]{4}-[0-9]{2}" aria-label="Pilih bulan"><button class="chip" id="semuaBln">Semua bulan</button><button class="ib" id="pr1" title="Cetak halaman ini">🖨️ Cetak</button><button class="ib" id="prAll" title="Cetak semua laporan">Cetak semua</button></div></header>
<div id="phead"><h1>__BIZ__</h1><div id="phinfo"></div></div>
<div class="tabs" id="tabs"></div>
<main>
<div class="pane" id="p_ringkasan"></div>
<div class="pane" id="p_penjualan"></div>
<div class="pane" id="p_tagihan"></div>
<div class="pane" id="p_utang"></div>
<div class="pane" id="p_customer"></div>
<div class="pane" id="p_kas"></div>
<div class="pane" id="p_stok">
<div class="cards"><div class="card stok red" data-f="habis"><b id="c_h">0</b><span>Habis</span></div><div class="card stok amb" data-f="menipis"><b id="c_m">0</b><span>Menipis</span></div>
<div class="card stok grn" data-f="aman"><b id="c_a">0</b><span>Aman</span></div><div class="card stok" data-f="belum"><b id="c_b">0</b><span>Belum dihitung</span></div></div>
<div style="display:flex;gap:8px;margin-top:10px"><button class="btn" id="belanja">📋 Salin daftar belanja</button><button class="btn k" id="semua">Tampilkan semua</button></div>
<input type="search" id="cari" placeholder="cari barang...">
<table><thead><tr><th>Barang</th><th class="n">Stok</th><th></th><th class="n">Min</th><th>Status</th><th class="n hide-s">Isi 1 bal</th><th class="hide-s">Supplier</th></tr></thead><tbody id="tb"></tbody></table></div>
<div class="pane" id="p_gudang">
<h2>✅ Menunggu persetujuan</h2><div id="pend"></div>
<h2>📦 PO yang barangnya belum lengkap datang</h2><div id="pobel"></div>
<h2>🛒 Permintaan barang dari gudang</h2><div id="perm"></div>
<h2>🚚 Status pengiriman pesanan</h2><div class="mut" id="ord"></div>
<h2>🧾 Stok yang udah disetujui (3 hari terakhir)</h2><div class="mut" style="margin-bottom:4px">Kalau ada yang salah masuk (mis. staff ngisi di Barang Masuk padahal maksudnya stok opname), klik <b>Jadikan stok real</b>: angka-angka itu langsung jadi stok sekarang.</div><div id="setuju"></div>
<h2>✔ Permintaan yang udah ditandai beres</h2><div id="permsel"></div>
<h2>Gerakan stok terakhir</h2><div class="mut" id="mut"></div></div>
</main>
<script>
const TOKEN=location.pathname.split('/')[2],B='/dashboard/'+TOKEN;let D=[],F='',L=null,TAB='ringkasan';
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>(Math.round(n*100)/100).toLocaleString('id-ID');
const rp=n=>'Rp'+Math.round(n||0).toLocaleString('id-ID');
const rps=n=>{n=n||0;const a=Math.abs(n);return a>=1e9?'Rp'+(n/1e9).toFixed(1).replace('.',',')+' M':a>=1e6?'Rp'+(n/1e6).toFixed(1).replace('.',',')+' jt':rp(n)};
const dmy=s=>s?String(s).slice(8,10)+'-'+String(s).slice(5,7)+'-'+String(s).slice(0,4):'-';
const TABS=[['ringkasan','🏠 Ringkasan'],['penjualan','📈 Penjualan'],['tagihan','🧾 Tagihan'],['utang','💸 Utang Supplier'],['customer','👥 Customer'],['kas','💰 Kas'],['stok','📦 Stok'],['gudang','🏭 Gudang']];
let PEND=0;function drawTabs(){document.getElementById('tabs').innerHTML=TABS.map(t=>'<button data-t="'+t[0]+'" class="'+(t[0]==TAB?'on':'')+'">'+t[1]+(t[0]=='gudang'&&PEND?' <span class="pill p-belum">'+PEND+'</span>':'')+'</button>').join('')}drawTabs();
function showTab(t){TAB=t;try{location.hash=t}catch(_){}document.querySelectorAll('.tabs button').forEach(b=>{b.classList.toggle('on',b.dataset.t==t);if(b.dataset.t==t&&b.scrollIntoView&&innerWidth<1180)try{b.scrollIntoView({block:'nearest',inline:'center'})}catch(_){}});document.querySelectorAll('.pane').forEach(p=>p.classList.toggle('on',p.id=='p_'+t))}
document.getElementById('tabs').onclick=e=>{const b=e.target.closest('button');if(b)showTab(b.dataset.t)};
function card(l,v,cls,sub){return '<div class="card '+(cls||'')+'"><span>'+l+'</span><b>'+v+'</b>'+(sub?'<small>'+sub+'</small>':'')+'</div>'}
function hbars(arr,empty){if(!arr||!arr.length)return '<div class="empty">'+(empty||'Belum ada data.')+'</div>';const mx=Math.max(...arr.map(a=>a.total),1);
return arr.map(a=>'<div class="hb"><div class="l" title="'+esc(a.nama)+'">'+esc(a.nama)+'</div><div class="t"><i style="width:'+Math.max(a.total/mx*100,1)+'%"></i></div><div class="v">'+rps(a.total)+'</div></div>').join('')}
function vbars(arr,key,lab){const mx=Math.max(...arr.map(a=>a[key]),1);return '<div class="vc">'+arr.map(a=>'<div title="'+esc(a.tgl||a.bulan)+': '+rp(a[key])+'"><i style="height:'+(a[key]/mx*100)+'%"></i><small>'+lab(a)+'</small></div>').join('')+'</div>'}
function dok(inv){return '<a class="btn s k" style="text-decoration:none;display:inline-block" target="_blank" rel="noopener" href="'+B+'/dok/'+encodeURIComponent(inv)+'/inv">🧾 Invoice</a> <a class="btn s k" style="text-decoration:none;display:inline-block" target="_blank" rel="noopener" href="'+B+'/dok/'+encodeURIComponent(inv)+'/sj">🚚 Surat Jalan</a> <a class="btn s k" style="text-decoration:none;display:inline-block" href="'+B+'/dok/'+encodeURIComponent(inv)+'/invtxt">📝 Inv teks</a> <a class="btn s k" style="text-decoration:none;display:inline-block" href="'+B+'/dok/'+encodeURIComponent(inv)+'/sjtxt">📝 SJ teks</a> <button class="btn s" style="background:var(--blu)" data-th="'+esc(inv)+'">📠 Thermal</button>'}
function pill(k,telat){if(telat)return '<span class="pill p-telat">Lewat tempo</span>';return k=='belum'?'<span class="pill p-belum">Belum kontra bon</span>':k=='sudah'?'<span class="pill p-sudah">Sudah kontra bon</span>':'<span class="pill p-x">Tanpa kontra bon</span>'}

function renderRingkasan(){const r=L.ringkas;const a=[];const T=(ic,tx,tab,lab)=>a.push([ic,tx,tab,lab]);
if(PEND)T('🏭',PEND+' kiriman dari gudang nunggu persetujuan lu','gudang','Gudang');
if(r.web_menunggu)T('🌐',r.web_menunggu+' order dari web nunggu dipencet "Simpan" di Telegram','#web','Lihat');
if(r.belum_kirim)T('🚚',r.belum_kirim+' invoice belum dikirim','#kirim','Lihat');
if(r.belum_kontra_bon)T('📋',r.belum_kontra_bon+' invoice belum kontra bon','tagihan','Tagihan');
if(r.telat)T('⏰',r.telat+' invoice lewat tempo · '+rp(r.total_telat),'tagihan','Tagihan');
if(r.komisi_belum)T('🤫',r.komisi_belum+' komisi belum dibayar · '+rp(r.komisi_belum_total),'tagihan','Tagihan');
if(r.po_telat)T('💸',r.po_telat+' PO supplier lewat jatuh tempo','utang','Utang');
if(r.stok_habis)T('🔴',r.stok_habis+' barang stoknya habis','stok','Stok');
if(r.stok_menipis)T('🟡',r.stok_menipis+' barang stoknya menipis','stok','Stok');
let h=a.length?'<div class="todo"><h3>Yang perlu diurus</h3>'+a.map(x=>'<button data-go="'+x[2]+'"><span class="ic">'+x[0]+'</span><span class="tx">'+esc(x[1])+'</span><span class="go">'+x[3]+'</span></button>').join('')+'</div>'
:'<div class="todo clear"><h3>Semua beres 👍</h3><p>Gak ada yang perlu diurus sekarang.</p></div>';
h+='<div class="sec"><h2>Penjualan</h2><span>'+esc(L.bulan_label)+'</span></div><div class="cards">'+
card('Omzet',rps(r.omzet),'blu',r.jml_invoice+' invoice')+card('Laba kotor (perkiraan)',rps(r.laba_kotor),r.laba_kotor>=0?'grn':'red',(r.laba_lengkap?'dari harga beli':'harga beli belum lengkap')+(r.komisi_bulan?' · udah dipotong komisi '+rps(r.komisi_bulan):''))+
card('Udah dibayar',rps(r.lunas),'grn')+card('Belum dibayar',rps(r.belum_lunas),'amb')+'</div>'+
'<div class="sec"><h2>Piutang & utang</h2><span>sampai hari ini</span></div><div class="cards">'+
card('Piutang customer',rps(r.total_piutang),'amb',r.jml_tagihan+' invoice')+card('Belum kontra bon',r.belum_kontra_bon,r.belum_kontra_bon?'red':'grn','invoice')+
card('Lewat tempo',rps(r.total_telat),r.telat?'red':'grn',r.telat+' invoice')+card('Utang supplier',rps(r.total_utang),'amb',r.jml_po_terbuka+' PO belum lunas')+'</div>'+
'<div class="sec"><h2>Kas</h2><span>'+esc(L.bulan_label)+'</span></div><div class="cards">'+
card('Kas masuk',rps(r.kas_masuk),'grn')+card('Kas keluar',rps(r.kas_keluar),'red')+card('Laba kas',rps(r.kas_laba),r.kas_laba>=0?'grn':'red')+card('Saldo kas',rps(r.saldo_kas),'blu','semua waktu')+'</div>';
h+='<div class="grid2"><div><h2>Omzet 6 bulan</h2><div class="box">'+vbars(L.tren,'omzet',a=>esc(a.bulan))+'</div></div>';
h+='<div><h2>Kas masuk vs keluar</h2><div class="box"><div class="vc vc2">'+(()=>{const mx=Math.max(...L.tren.map(a=>Math.max(a.kas_masuk,a.kas_keluar)),1);return L.tren.map(a=>'<div title="'+esc(a.bulan)+'"><i style="height:'+(a.kas_masuk/mx*100)+'%"></i><i style="height:'+(a.kas_keluar/mx*100)+'%;background:#d9392b"></i><small>'+esc(a.bulan)+'</small></div>').join('')})()+'</div><div class="lg"><b style="background:var(--g)"></b>Masuk<b style="background:#d9392b"></b>Keluar</div></div></div></div>';
h+='<h2 id="web">🌐 Order web menunggu persetujuan</h2>'+(L.web_list.length?'<div class="box">'+L.web_list.map(w=>'<div>• <b>'+esc(w.nama)+'</b> — '+w.n_item+' item • '+esc(w.waktu)+'</div>').join('')+'<div class="mut" style="margin-top:6px">Klik ✅ Simpan di Telegram biar jadi invoice.</div></div>':'<div class="empty">Gak ada.</div>');
h+='<h2 id="kirim">🚚 Invoice belum dikirim</h2>'+(L.belum_kirim_list.length?'<div style="margin:6px 0"><button class="btn k" id="kirimAll">✅ Tandai SEMUA sudah dikirim ('+L.ringkas.belum_kirim+')</button></div><table><thead><tr><th>Invoice</th><th>Customer</th><th>Req. kirim</th></tr></thead><tbody>'+L.belum_kirim_list.map(o=>'<tr><td>'+esc(o.invoice)+'<br><small style="color:var(--mu)">'+dmy(o.tgl)+' • '+o.n_item+' item</small><div style="margin-top:4px">'+dok(o.invoice)+' <button class="btn s" data-kirim="'+esc(o.invoice)+'">✅ Sudah dikirim</button></div></td><td>'+esc(o.customer)+'</td><td>'+(o.kirim?esc(o.kirim):'-')+'</td></tr>').join('')+'</tbody></table>':'<div class="empty">Semua udah dikirim 🎉</div>');
document.getElementById('p_ringkasan').innerHTML=h}

function renderPenjualan(){const r=L.ringkas;let h='<div class="cards">'+card('Omzet '+esc(L.bulan_label),rps(r.omzet),'blu')+card('Jumlah invoice',r.jml_invoice)+card('Rata-rata / invoice',rps(r.rata_invoice))+card('Estimasi laba kotor',rps(r.laba_kotor),'grn',r.laba_lengkap?'':'harga beli belum lengkap')+'</div>';
h+=L.bulan=='semua'?'<h2>Omzet per bulan</h2><div class="box">'+vbars(L.harian,'total',a=>esc(a.label||a.tgl))+'</div>':'<h2>Omzet per hari</h2><div class="box">'+vbars(L.harian,'total',a=>(+a.tgl.slice(8,10))%5==1||a.tgl.slice(8,10)=='31'?+a.tgl.slice(8,10):'')+'</div>';
h+='<h2>Customer teratas</h2><div class="box">'+hbars(L.top_customer)+'</div>';
h+='<h2>Produk terlaris (rupiah)</h2><div class="box">'+hbars(L.top_produk.map(p=>({nama:p.nama+' ('+fmt(p.qty)+' '+p.satuan+')',total:p.total})))+'</div>';
h+='<h2>Per kategori</h2><div class="box">'+hbars(L.per_kategori)+'</div>';
h+='<h2>Daftar invoice bulan ini</h2>'+(L.invoice_bulan.length?'<table><thead><tr><th>Invoice</th><th>Customer</th><th class="n">Total</th><th>Pembayaran</th></tr></thead><tbody>'+L.invoice_bulan.map(o=>'<tr><td>'+esc(o.invoice)+'<br><small style="color:var(--mu)">'+dmy(o.tgl)+'</small><div style="margin-top:4px">'+dok(o.invoice)+'</div></td><td>'+esc(o.customer)+'</td><td class="n">'+rp(o.total)+'</td><td>'+(o.status=='Lunas'?'<span class="pill p-sudah">✅ Lunas</span>':'<span class="pill p-belum">Belum bayar</span>')+'</td></tr>').join('')+'</tbody></table>':'<div class="empty">Belum ada invoice bulan ini.</div>');
document.getElementById('p_penjualan').innerHTML=h}

function renderTagihan(){const r=L.ringkas;let h='<div class="box" style="border-color:rgba(92,225,255,.45)"><b>🔎 Cek transfer masuk</b><div class="mut">Ketik nominal transfer, gua cariin bon mana aja yang jumlahnya pas (termasuk yang udah ditandai lunas, biar ketahuan kalau ada yang kepencet).</div><div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px"><input id="tfn" placeholder="mis. 1.223.500 / 1,2jt" inputmode="decimal" style="flex:1;min-width:140px;padding:9px;border:1px solid var(--ln);border-radius:8px"><input id="tfc" placeholder="customer (boleh kosong)" style="flex:1;min-width:140px;padding:9px;border:1px solid var(--ln);border-radius:8px"><button class="btn" id="tfgo">Cek</button></div><div id="tfres"></div></div>'+'<div class="cards">'+card('Total piutang',rps(r.total_piutang),'amb',r.jml_tagihan+' invoice')+card('Belum kontra bon',r.belum_kontra_bon,r.belum_kontra_bon?'red':'grn')+card('Lewat tempo',rps(r.total_telat),r.telat?'red':'grn')+card('Umur >30 hari',rps(L.aging[3].total),L.aging[3].total?'red':'grn')+'</div>';
h+='<h2>🤫 Komisi jalur belakang</h2><div class="box">'+(L.komisi_setting.length?L.komisi_setting.map(k=>'<div>• '+esc(k.customer)+': <b>'+rp(k.rate)+'</b>/satuan'+(k.penerima?' → '+esc(k.penerima):'')+'</div>').join(''):'<div class="mut">Belum ada. Pasang lewat Telegram (chat pribadi): /komisi baso yen 100 Pak Andi</div>')+'</div>'+
(L.komisi_belum_list.length?'<table><thead><tr><th>Belum dibayar</th><th class="n">Komisi</th></tr></thead><tbody>'+L.komisi_belum_list.map(k=>'<tr><td><b>'+esc(k.penerima||'-')+'</b><br><small style="color:var(--mu)">'+esc(k.invoice)+' • '+esc(k.customer)+' • '+fmt(k.qty)+' × '+rp(k.rate)+'</small><div style="margin-top:4px"><button class="btn s" data-km="'+esc(k.invoice)+'" data-j="'+k.jumlah+'">✅ Sudah dibayar</button></div></td><td class="n">'+rp(k.jumlah)+'</td></tr>').join('')+'</tbody></table>':'<div class="empty">Semua komisi udah dibayar.</div>');
{const by={};L.tagihan.forEach(t=>{const k=t.customer.toLowerCase().replace(/[^a-z0-9]/g,'');(by[k]=by[k]||{nama:t.customer,inv:[],total:0}).inv.push(t);by[k].total+=t.total});
const C=Object.values(by).sort((a,b)=>b.total-a.total);
h+='<h2>📄 Rincian piutang per customer</h2>'+(C.length?C.map((c,ci)=>'<div class="box" data-cust="'+ci+'"><div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><b>'+esc(c.nama)+'</b><b>'+rp(c.total)+'</b></div><div class="mut">'+c.inv.length+' invoice belum lunas</div>'+
c.inv.slice().sort((a,b)=>a.tgl<b.tgl?-1:1).map(t=>'<label style="display:flex;gap:8px;align-items:center;padding:4px 0;border-bottom:1px solid var(--ln)"><input type="checkbox" class="pc" data-ci="'+ci+'" value="'+esc(t.invoice)+'" data-j="'+t.total+'"><span style="flex:1">'+esc(t.invoice)+' <small style="color:var(--mu)">'+dmy(t.tgl)+' • '+t.umur+' hari</small></span><span>'+rp(t.total)+'</span></label>').join('')+
'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px"><button class="btn s" data-lb="'+ci+'">✅ Lunas yang dicentang</button><button class="btn s k" data-lball="'+ci+'">✅ Lunas semua ('+rp(c.total)+')</button><button class="btn s k" data-tf="'+ci+'">💸 Transfer sejumlah…</button><button class="btn s k" data-cr="'+ci+'">🖨️ Cetak rincian</button></div></div>').join(''):'<div class="empty">Gak ada piutang 🎉</div>');
window._PC=C}
h+='<h2>Umur piutang</h2><div class="box">'+hbars(L.aging)+'</div><h2>Piutang per customer</h2><div class="box">'+hbars(L.piutang_customer,'Gak ada piutang 🎉')+'</div>';
h+='<h2>Invoice belum lunas</h2>';
if(!L.tagihan.length)h+='<div class="empty">Semua invoice udah lunas 🎉</div>';else{
h+='<div style="margin:6px 0;display:flex;gap:6px;flex-wrap:wrap">'+(r.belum_kontra_bon?'<button class="btn" id="kbAll">✅ Semua yang belum → sudah kontra bon ('+r.belum_kontra_bon+')</button>':'')+'<button class="btn k" id="kbSel">Tandai yang dicentang saja</button></div><table><thead><tr><th></th><th>Invoice</th><th class="n">Total</th><th>Status</th></tr></thead><tbody>'+L.tagihan.map(t=>'<tr><td>'+(t.kontra_bon=='belum'?'<input type="checkbox" class="kbc" value="'+esc(t.invoice)+'">':'')+'</td><td><b>'+esc(t.customer)+'</b><br><small style="color:var(--mu)">'+esc(t.invoice)+' • '+dmy(t.tgl)+' • '+t.umur+' hari</small><div style="margin-top:4px;display:flex;gap:4px;flex-wrap:wrap">'+dok(t.invoice)+' <button class="btn s" data-lunas="'+esc(t.invoice)+'" data-n="'+esc(t.customer)+'" data-j="'+t.total+'">✅ Lunas</button></div></td><td class="n">'+rp(t.total)+'</td><td>'+pill(t.kontra_bon,t.telat)+(t.jadwal?'<br><small style="color:var(--mu)">'+(t.kontra_bon=='belum'?'jadwal ':'cek bayar ')+dmy(t.jadwal)+'</small>':'')+'</td></tr>').join('')+'</tbody></table>'}
document.getElementById('p_tagihan').innerHTML=h}

function renderUtang(){const r=L.ringkas;let h='<div class="cards">'+card('Total utang supplier',rps(r.total_utang),'amb')+card('PO terbuka',r.jml_po_terbuka)+card('PO lewat tempo',r.po_telat,r.po_telat?'red':'grn')+'</div>';
h+='<h2>Utang per supplier</h2><div class="box">'+hbars(L.utang_supplier,'Gak ada utang 🎉')+'</div><h2>PO yang belum lunas</h2>';
h+=L.po_terbuka.length?'<div style="margin:6px 0"><button class="btn" id="bayarSel">✅ Tandai yang dicentang: SUDAH DIBAYAR</button></div><table><thead><tr><th></th><th>PO</th><th class="n">Total</th><th>Jatuh tempo</th></tr></thead><tbody>'+L.po_terbuka.map(o=>'<tr><td><input type="checkbox" class="poc" value="'+esc(o.po)+'" data-j="'+o.total+'"></td><td><b>'+esc(o.supplier||'-')+'</b><br><small style="color:var(--mu)">'+esc(o.po)+' • '+dmy(o.tgl)+'</small><div style="margin-top:4px"><button class="btn s" data-bpo="'+esc(o.po)+'" data-n="'+esc(o.supplier)+'" data-j="'+o.total+'">✅ Sudah dibayar</button></div></td><td class="n">'+rp(o.total)+'</td><td>'+(o.jatuh_tempo?(o.telat?'<span class="pill p-telat">'+dmy(o.jatuh_tempo)+'</span>':dmy(o.jatuh_tempo)):'-')+'</td></tr>').join('')+'</tbody></table>':'<div class="empty">Semua PO udah lunas.</div>';
h+='<div class="mut" style="margin-top:8px">Klik "Sudah dibayar" → utang supplier berkurang, dicatat Kas Keluar, PO jadi Lunas. Bisa juga lewat Telegram: /bayarutang.</div>';
document.getElementById('p_utang').innerHTML=h}

function renderKas(){const r=L.ringkas;let h='<div class="cards">'+card('Kas masuk',rps(r.kas_masuk),'grn',esc(L.bulan_label))+card('Kas keluar',rps(r.kas_keluar),'red')+card('Laba/rugi kas',rps(r.kas_laba),r.kas_laba>=0?'grn':'red')+card('Saldo kas (semua)',rps(r.saldo_kas),'blu')+'</div>';
h+='<h2>Kas masuk per kategori</h2><div class="box">'+hbars(L.kas_masuk_kat)+'</div><h2>Kas keluar per kategori</h2><div class="box">'+hbars(L.kas_keluar_kat)+'</div><h2>Transaksi kas bulan ini</h2>';
h+=L.kas_list.length?'<table><thead><tr><th>Tanggal</th><th>Keterangan</th><th class="n">Jumlah</th></tr></thead><tbody>'+L.kas_list.map(k=>'<tr><td>'+dmy(k.tgl)+'</td><td>'+esc(k.kategori)+'<br><small style="color:var(--mu)">'+esc(k.ket)+'</small></td><td class="n" style="color:'+(k.jenis=='Masuk'?'var(--ok)':'var(--red)')+'">'+(k.jenis=='Masuk'?'+':'-')+rp(k.jumlah)+'</td></tr>').join('')+'</tbody></table>':'<div class="empty">Belum ada transaksi kas bulan ini.</div>';
document.getElementById('p_kas').innerHTML=h}

let CPER='semua';
function renderCustomer(){const C=L.customers||[];let h='';
h+='<h2>⚠️ Ditandai LUNAS 7 hari terakhir</h2><div class="mut" style="margin-bottom:4px">Cek di sini kalau ada yang kepencet lunas. Klik ↩️ buat balikin jadi belum lunas (Kas Masuk-nya ikut dihapus).</div>'+
((L.lunas_baru||[]).length?'<table><thead><tr><th>Invoice</th><th class="n">Total</th></tr></thead><tbody>'+L.lunas_baru.map(o=>'<tr><td><b>'+esc(o.customer)+'</b><br><small style="color:var(--mu)">'+esc(o.invoice)+' • invoice '+dmy(o.tgl)+' • <b>lunas '+dmy(o.bayar)+'</b>'+(o.via?' • lewat '+esc(o.via):'')+'</small><div style="margin-top:4px"><button class="btn s r" data-bl="'+esc(o.invoice)+'" data-n="'+esc(o.customer)+'" data-j="'+o.total+'">↩️ Batal lunas</button></div></td><td class="n">'+rp(o.total)+'</td></tr>').join('')+'</tbody></table>':'<div class="empty">Gak ada.</div>');
const per=CPER=='semua'||L.bulan=='semua'?'':L.bulan;
h+='<h2>👥 Per customer</h2><div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px"><button class="btn s '+(CPER=='semua'?'':'k')+'" data-cper="semua">Semua waktu</button>'+(L.bulan!='semua'?'<button class="btn s '+(CPER=='bulan'?'':'k')+'" data-cper="bulan">'+esc(L.bulan_label)+'</button>':'')+'</div><input type="search" id="ccari" placeholder="cari customer..."><div id="clist"></div>';
document.getElementById('p_customer').innerHTML=h;
const data=C.map(c=>{const inv=c.invoices.filter(o=>!per||o.tgl.startsWith(per));const tot=inv.reduce((a,o)=>a+o.total,0),bel=inv.filter(o=>o.status!='Lunas').reduce((a,o)=>a+o.total,0);
const brg={};inv.forEach(o=>o.items.forEach(it=>{const k=it.nama+'|'+it.satuan;(brg[k]=brg[k]||{nama:it.nama,sat:it.satuan,qty:0,sub:0});brg[k].qty+=it.qty;brg[k].sub+=it.sub}));
return {nama:c.nama,inv,tot,bel,brg:Object.values(brg).sort((a,b)=>b.sub-a.sub)}}).filter(c=>c.inv.length).sort((a,b)=>b.tot-a.tot);
const draw=()=>{const q=(document.getElementById('ccari').value||'').toLowerCase();
document.getElementById('clist').innerHTML=data.filter(c=>c.nama.toLowerCase().includes(q)).map(c=>'<details class="box" style="padding:0"><summary style="padding:10px 12px;cursor:pointer;list-style:none;display:flex;gap:8px;align-items:center"><span style="flex:1"><b>'+esc(c.nama)+'</b><br><small style="color:var(--mu)">'+c.inv.length+' invoice • '+c.inv.filter(o=>o.status=='Lunas').length+' lunas</small></span><span style="text-align:right"><b>'+rp(c.tot)+'</b><br>'+(c.bel>0?'<span class="pill p-belum">belum '+rps(c.bel)+'</span>':'<span class="pill p-sudah">lunas semua</span>')+'</span><span class="arw" style="color:var(--mu)">▾</span></summary>'+
'<div style="padding:0 12px 12px"><div class="cards">'+card('Total belanja',rps(c.tot),'blu',c.inv.length+' invoice')+card('Sudah bayar',rps(c.tot-c.bel),'grn')+card('Belum bayar',rps(c.bel),c.bel>0?'red':'grn')+'</div>'+
'<div style="font-weight:600;margin:8px 0 4px">📦 Barang yang dipesan</div>'+c.brg.map(b=>'<div class="hb"><div class="l" title="'+esc(b.nama)+'">'+esc(b.nama)+'</div><div class="v" style="min-width:auto">'+fmt(b.qty)+' '+esc(b.sat)+'</div><div class="v">'+rp(b.sub)+'</div></div>').join('')+
'<div style="font-weight:600;margin:10px 0 4px">🧾 Invoice</div>'+c.inv.map(o=>'<div style="padding:6px 0;border-bottom:1px solid var(--ln)"><div style="display:flex;gap:6px;align-items:center"><span>'+(o.status=='Lunas'?'✅':'⏳')+'</span><span style="flex:1"><b>'+esc(o.invoice)+'</b> <small style="color:var(--mu)">'+dmy(o.tgl)+'</small></span><b>'+rp(o.total)+'</b></div><div class="mut">'+esc(o.items.map(it=>it.nama+' x'+fmt(it.qty)+' '+it.satuan).join(', '))+'</div><div style="margin-top:4px">'+(o.status=='Lunas'?'<span class="pill p-sudah">Lunas '+dmy(o.bayar)+'</span> <button class="btn s r" data-bl="'+esc(o.invoice)+'" data-n="'+esc(c.nama)+'" data-j="'+o.total+'">↩️ Batal lunas</button>':'<span class="pill p-belum">Belum lunas</span> <button class="btn s" data-lunas="'+esc(o.invoice)+'" data-n="'+esc(c.nama)+'" data-j="'+o.total+'">✅ Lunas</button>')+' '+dok(o.invoice)+'</div></div>').join('')+'</div></details>').join('')||'<div class="empty">Gak ada data.</div>'};
draw();document.getElementById('ccari').oninput=draw}
let MODE='';async function loadLap(){const bl=MODE||document.getElementById('bln').value;document.getElementById('semuaBln').style.background=MODE?'var(--cy)':'';document.getElementById('semuaBln').style.color=MODE?'#06101E':'';try{const r=await fetch(B+'/laporan?bulan='+encodeURIComponent(bl));const j=await r.json();if(!j.ok)throw 0;L=j;if(!bl&&j.bulan!='semua')document.getElementById('bln').value=j.bulan;
renderRingkasan();renderPenjualan();renderTagihan();renderUtang();renderKas();renderCustomer()}catch(e){document.getElementById('p_ringkasan').innerHTML='<div class="box">Gagal ambil laporan. Coba refresh sebentar lagi (Google Sheets lagi sibuk).</div>'}}
document.getElementById('bln').onchange=()=>{MODE='';loadLap()};document.getElementById('semuaBln').onclick=()=>{MODE=MODE?'':'semua';loadLap()};
function cetak(all){const nm=(TABS.find(t=>t[0]==TAB)||['',''])[1].replace(/^\S+\s/,'');
document.getElementById('phinfo').textContent=(all?'Laporan lengkap':nm)+' — '+(L?L.bulan_label:'')+' • dicetak '+new Date().toLocaleString('id-ID');
document.body.classList.toggle('printall',!!all);setTimeout(()=>{window.print();setTimeout(()=>document.body.classList.remove('printall'),500)},100)}
document.getElementById('pr1').onclick=()=>cetak(false);document.getElementById('prAll').onclick=()=>cetak(true);

document.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;
if(b.dataset.kirim||b.id=='kirimAll'){const v=b.id=='kirimAll'?L.belum_kirim_all:[b.dataset.kirim];if(!confirm(b.id=='kirimAll'?'Tandai SEMUA '+v.length+' invoice sudah dikirim?':'Tandai '+v[0]+' sudah dikirim?'))return;b.disabled=true;const r=await (await fetch(B+'/kirim',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({invoices:v})})).json();if(!r.ok)alert('Gagal');loadLap();loadPend();return}
if(b.dataset.ubah){const v=prompt('Stok REAL '+b.dataset.nm+' sekarang berapa '+b.dataset.sat+'?\n(stok sistem: '+(b.dataset.st===''?'belum ada':b.dataset.st)+')',b.dataset.st);if(v===null||v.trim()==='')return;const n=/^\d{1,3}(\.\d{3})+$/.test(v.trim())?v.trim().replace(/\./g,''):v.trim();if(isNaN(parseFloat(n.replace(',','.')))||parseFloat(n.replace(',','.'))<0){alert('Angkanya salah');return}
b.disabled=true;const r=await (await fetch(B+'/setstok',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:b.dataset.ubah,qty:n})})).json();if(!r.ok)alert(r.error||'Gagal');loadStok();loadLap();return}
if(b.dataset.jh){if(!confirm('Jadikan angka-angka di kiriman ini STOK REAL sekarang? (stok barang-barang itu ditimpa jadi angka ini)'))return;b.disabled=true;const r=await (await fetch(B+'/jadihitung',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({batch:b.dataset.jh})})).json();if(r.ok){b.outerHTML='<span class="pill p-sudah">✅ Sudah jadi stok real</span>';alert('✅ '+r.n+' barang: stoknya sekarang ikut angka ini.')}else alert(r.error||'Gagal');loadStok();loadPend();return}
if(b.dataset.poall){const ids=b.dataset.poall.split(',');if(!confirm('Bikin PO otomatis buat '+ids.length+' permintaan? Supplier & harga beli diambil dari PriceList, PDF PO langsung dikirim ke Telegram.'))return;b.disabled=true;
const r=await (await fetch(B+'/popermintaan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids})})).json();
const noSup=(r.gagal||[]).filter(g=>g.kurang=='supplier');
if(noSup.length){let sl=[];try{sl=(await (await fetch(B+'/suppliers')).json()).suppliers||[]}catch(e){}
for(const g of noSup){const s=prompt('Supplier buat "'+g.nama+'" belum diisi.\nKetik nama supplier-nya'+(sl.length?' (yang udah ada: '+sl.join(', ')+')':'')+':');
if(!s||!s.trim())continue;const semua=g.kategori&&confirm('Sekalian isi supplier "'+s.trim()+'" buat SEMUA barang kategori '+g.kategori+' yang supplier-nya masih kosong?');
await fetch(B+'/setsupplier',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({codes:[g.code],supplier:s.trim(),kategori:semua?g.kategori:''})})}
const r2=await (await fetch(B+'/popermintaan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ids:noSup.map(g=>g.id)})})).json();
r.pos=(r.pos||[]).concat(r2.pos||[]);r.gagal=(r.gagal||[]).filter(g=>g.kurang!='supplier').concat(r2.gagal||[])}
let m=(r.pos||[]).map(p=>'✅ '+p.no_po+' → '+p.supplier+' ('+rp(p.total)+')').join('\n');if((r.gagal||[]).length)m+=(m?'\n\n':'')+'⚠️ Belum bisa dibikinin PO:\n'+r.gagal.map(g=>'• '+g.nama+' — '+g.alasan).join('\n')+'\n\nLengkapi kolom Supplier / Harga_Beli di PriceList, lalu klik Buat PO lagi.';
alert(m||'Gak ada yang diproses (mungkin udah dibikin PO).');loadPend();return}
if(b.dataset.lb!==undefined||b.dataset.lball!==undefined){const ci=b.dataset.lb!==undefined?b.dataset.lb:b.dataset.lball;const c=window._PC[ci];
const v=b.dataset.lball!==undefined?c.inv.map(t=>t.invoice):[...document.querySelectorAll('.pc[data-ci="'+ci+'"]:checked')].map(x=>x.value);
if(!v.length){alert('Centang dulu invoice yang dibayar.');return}const tot=c.inv.filter(t=>v.includes(t.invoice)).reduce((a,t)=>a+t.total,0);
if(!confirm('Tandai LUNAS '+v.length+' invoice '+c.nama+' = '+rp(tot)+'?\nOtomatis dicatat Kas Masuk.'))return;b.disabled=true;
const r=await (await fetch(B+'/lunasbanyak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({invoices:v})})).json();alert(r.ok?'✅ '+r.n+' invoice lunas, '+rp(r.total)+' masuk Kas.':'Gagal');loadLap();return}
if(b.dataset.tf!==undefined){const c=window._PC[b.dataset.tf];let s=prompt('Berapa yang ditransfer '+c.nama+'? (mis. 5.000.000 atau 5jt)');if(!s)return;s=s.toLowerCase().replace(/rp|\s/g,'');
let n=/jt|juta/.test(s)?parseFloat(s.replace(',','.'))*1e6:/rb|ribu|k$/.test(s)?parseFloat(s.replace(',','.'))*1e3:parseFloat(s.replace(/[.,]/g,''));if(!(n>0)){alert('Nominal salah');return}
let sisa=n;document.querySelectorAll('.pc[data-ci="'+b.dataset.tf+'"]').forEach(x=>x.checked=false);
c.inv.slice().sort((a,b)=>a.tgl<b.tgl?-1:1).forEach(t=>{if(t.total<=sisa+0.5){sisa-=t.total;const x=document.querySelector('.pc[data-ci="'+b.dataset.tf+'"][value="'+t.invoice+'"]');if(x)x.checked=true}});
alert(sisa>=n?'Nominal belum cukup buat 1 invoice pun.':'☑️ Udah dicentang invoice terlama yang pas sama '+rp(n)+'.'+(sisa>0.5?'\n⚠️ Sisa '+rp(sisa)+' gak pas — cek lagi.':'\n✅ Pas!')+'\nCek centangnya, terus klik "Lunas yang dicentang".');return}
if(b.dataset.cr!==undefined){const c=window._PC[b.dataset.cr];const w=window.open('','_blank');if(!w){alert('Izinkan pop-up buat cetak');return}
w.document.write('<html><head><meta charset="utf-8"><title>Rincian '+esc(c.nama)+'</title><style>body{font:14px system-ui,sans-serif;margin:24px}table{border-collapse:collapse;width:100%}td,th{border:1px solid #999;padding:6px 8px;text-align:left}td.n,th.n{text-align:right}h2,h3{margin:4px 0}</style></head><body><h2>'+esc(document.title.indexOf('Dashboard')>=0?'__BIZ__':'__BIZ__')+'</h2><h3>Rincian tagihan: '+esc(c.nama)+'</h3><div>Per '+new Date().toLocaleDateString('id-ID')+'</div><br><table><tr><th>No</th><th>Invoice</th><th>Tanggal</th><th class="n">Jumlah</th></tr>'+
c.inv.slice().sort((a,b)=>a.tgl<b.tgl?-1:1).map((t,i)=>'<tr><td>'+(i+1)+'</td><td>'+esc(t.invoice)+'</td><td>'+dmy(t.tgl)+'</td><td class="n">'+rp(t.total)+'</td></tr>').join('')+'<tr><th colspan="3">TOTAL</th><th class="n">'+rp(c.total)+'</th></tr></table></body></html>');w.document.close();setTimeout(()=>w.print(),300);return}
if(b.dataset.bl){if(!confirm('Balikin '+b.dataset.bl+' ('+b.dataset.n+', '+rp(+b.dataset.j)+') jadi BELUM LUNAS?\nCatatan Kas Masuk-nya dihapus & pengingat tagihan dipasang lagi.'))return;b.disabled=true;
const r=await (await fetch(B+'/batallunas',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({invoice:b.dataset.bl})})).json();alert(r.ok?'↩️ '+b.dataset.bl+' balik jadi belum lunas.':'Gagal');loadLap();return}
if(b.id=='tfgo'){const n=document.getElementById('tfn').value.trim();if(!n){alert('Isi nominalnya dulu');return}b.disabled=true;
const r=await (await fetch(B+'/cektransfer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nominal:n,customer:document.getElementById('tfc').value})})).json();b.disabled=false;
const box=document.getElementById('tfres');if(!r.ok){box.innerHTML='<div class="empty">'+esc(r.error||'Gagal')+'</div>';return}
const H=(r.pas&&r.pas.length)?r.pas:(r.mirip||[]);
if(!H.length){box.innerHTML='<div class="empty">Gak ketemu kombinasi bon yang pas sama '+rp(r.nominal)+'. Mungkin ada potongan/biaya transfer atau bayar sebagian.</div>';return}
box.innerHTML='<div class="mut" style="margin:8px 0 4px">'+(r.pas&&r.pas.length?'✅ Pas '+rp(r.nominal)+':':'Gak ada yang pas persis, yang paling mirip:')+'</div>'+H.map((m,i)=>'<div class="box"><b>'+(i+1)+'. '+esc(m.customer)+'</b> — '+m.invoices.length+' bon = '+rp(m.invoices.reduce((a,o)=>a+o.total,0))+(m.selisih?' <span class="pill p-telat">selisih '+rp(Math.abs(m.selisih))+'</span>':'')+
m.invoices.map(o=>'<div>• '+esc(o.invoice)+' <small style="color:var(--mu)">'+dmy(o.tgl)+'</small> '+rp(o.total)+' — '+(o.status=='Lunas'?'<b style="color:var(--amb)">⚠️ udah ditandai lunas '+dmy(o.bayar)+'</b>':'belum lunas')+'</div>').join('')+
(m.sudah.length&&m.belum.length?'<div class="mut">↳ sebagian udah lunas duluan — cek, mungkin ada yang kepencet</div>':m.sudah.length?'<div class="mut">↳ semua udah ditandai lunas</div>':'')+
(m.belum.length?'<div style="margin-top:6px"><button class="btn s" data-tfl="'+esc(m.belum.join(','))+'">✅ Lunasin '+m.belum.length+' bon yang belum</button></div>':'')+'</div>').join('')+(H.length>1?'<div class="mut">Ada beberapa kemungkinan — pilih yang sesuai bukti transfer.</div>':'');return}
if(b.dataset.tfl){const v=b.dataset.tfl.split(',');if(!confirm('Tandai LUNAS: '+v.join(', ')+'?'))return;b.disabled=true;const r=await (await fetch(B+'/lunasbanyak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({invoices:v})})).json();alert(r.ok?'✅ '+r.n+' bon lunas ('+rp(r.total)+').':'Gagal');loadLap();return}
if(b.dataset.cper){CPER=b.dataset.cper;renderCustomer();return}
if(b.dataset.bpo||b.id=='bayarSel'){const v=b.id=='bayarSel'?[...document.querySelectorAll('.poc:checked')].map(x=>x.value):[b.dataset.bpo];
if(!v.length){alert('Centang dulu PO yang udah dibayar.');return}const tot=b.id=='bayarSel'?[...document.querySelectorAll('.poc:checked')].reduce((a,x)=>a+(+x.dataset.j),0):+b.dataset.j;
if(!confirm('Tandai '+v.length+' PO SUDAH DIBAYAR = '+rp(tot)+'?\n'+v.join(', ')+'\n\nUtang supplier berkurang & dicatat Kas Keluar.'))return;b.disabled=true;
const r=await (await fetch(B+'/bayarpo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pos:v})})).json();
alert(r.ok&&r.hasil.length?'✅ '+r.hasil.map(h=>h.po+' '+h.supplier+' '+rp(h.total)).join('\n'):'Gak ada yang diproses (mungkin udah lunas).');loadLap();return}
if(b.dataset.go){const g=b.dataset.go;if(g[0]=='#'){const el=document.querySelector(g);el&&el.scrollIntoView({behavior:'smooth',block:'start'})}else{showTab(g);scrollTo(0,0)}return}
if(b.dataset.hid){try{const h=JSON.parse(localStorage.getItem('hid_setuju')||'[]');h.push(b.dataset.hid);localStorage.setItem('hid_setuju',JSON.stringify(h.slice(-200)))}catch(e){}b.closest('.box').remove();return}
if(b.dataset.km){if(!confirm('Komisi '+b.dataset.km+' ('+rp(+b.dataset.j)+') sudah dibayar? Otomatis dicatat Kas Keluar.'))return;b.disabled=true;const r=await (await fetch(B+'/bayarkomisi',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({invoice:b.dataset.km})})).json();if(!r.ok)alert(r.error||'Gagal');loadLap();return}
if(b.dataset.tutup){if(!confirm('Tutup '+b.dataset.tutup+'? Sisa barang dianggap gak dikirim & PO hilang dari daftar staff.'))return;b.disabled=true;await fetch(B+'/tutuppo',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({po:b.dataset.tutup})});loadPend();return}
if(b.dataset.th){cetakThermal(B+'/struk/'+encodeURIComponent(b.dataset.th),b);return}
if(b.id=='kbSel'||b.id=='kbAll'){const v=b.id=='kbAll'?L.tagihan.filter(t=>t.kontra_bon=='belum').map(t=>t.invoice):[...document.querySelectorAll('.kbc:checked')].map(x=>x.value);if(!v.length){alert('Centang dulu invoice yang udah di-kontra bon.');return}
if(!confirm('Tandai '+v.length+' invoice sudah kontra bon?'))return;b.disabled=true;const r=await (await fetch(B+'/kontrabon',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({invoices:v})})).json();alert(r.ok?'✅ '+r.n+' invoice ditandai sudah kontra bon.':'Gagal');loadLap()}
if(b.dataset.lunas){if(!confirm('Tandai '+b.dataset.lunas+' ('+b.dataset.n+', '+rp(+b.dataset.j)+') LUNAS? Otomatis masuk Kas.'))return;b.disabled=true;const r=await (await fetch(B+'/lunas',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({invoice:b.dataset.lunas})})).json();alert(r.ok?'✅ Lunas '+rp(r.total)+' & dicatat ke Kas.':(r.error||'Gagal'));loadLap()}
if(b.dataset.b){if(!confirm(b.dataset.a=='1'?'Setujui pengajuan ini? Stok akan berubah.':'Tolak pengajuan ini?'))return;b.disabled=true;await fetch(B+'/decide',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({batch:b.dataset.b,approve:b.dataset.a=='1'})});loadStok();loadPend()}
if(b.dataset.q){b.disabled=true;await fetch(B+'/permintaan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:b.dataset.q,status:'Selesai'})});loadPend()}});

/* ---------- stok & gudang ---------- */
function stokTxt(i){if(i.stok===null)return '-';let t=fmt(i.stok)+' '+esc(i.satuan)+(i.estimasi?' <small title="belum ada Hitung Stok awal">(sementara)</small>':'');if(i.isi_bal>0&&i.stok>=i.isi_bal)t+=' <small>('+(Math.round(i.stok/i.isi_bal*10)/10)+' bal)</small>';return t}
const ORD={habis:0,menipis:1,belum:2,aman:3};
function renderStok(){const q=document.getElementById('cari').value.toLowerCase();let X=D.filter(i=>(!F||i.status==F)&&(i.nama+' '+i.code+' '+i.kategori).toLowerCase().includes(q));
X.sort((a,b)=>ORD[a.status]-ORD[b.status]||a.nama.localeCompare(b.nama));
document.getElementById('tb').innerHTML=X.map(i=>'<tr class="'+i.status+'"><td><b>'+esc(i.nama)+'</b><br><small style="color:var(--mu)">'+esc(i.code)+'</small></td><td class="n">'+stokTxt(i)+'</td><td><button class="btn s k" data-ubah="'+esc(i.code)+'" data-nm="'+esc(i.nama)+'" data-st="'+(i.stok===null?'':i.stok)+'" data-sat="'+esc(i.satuan)+'">✏️</button></td><td class="n"><input data-k="min" data-c="'+esc(i.code)+'" value="'+(i.min||'')+'" inputmode="decimal"></td><td>'+({aman:'🟢 Aman',menipis:'🟡 Menipis',habis:'🔴 Habis',belum:'⚪ Belum dihitung'})[i.status]+'</td><td class="n hide-s"><input data-k="isi_bal" data-c="'+esc(i.code)+'" value="'+(i.isi_bal||'')+'" inputmode="decimal"></td><td class="hide-s">'+esc(i.supplier||'')+'</td></tr>').join('');
const c=s=>D.filter(i=>i.status==s).length;['h:habis','m:menipis','a:aman','b:belum'].forEach(x=>{const[a,b]=x.split(':');document.getElementById('c_'+a).textContent=c(b)})}
document.getElementById('tb').addEventListener('change',async e=>{const c=e.target.dataset.c;if(!c)return;const v=parseFloat(String(e.target.value).replace(',','.'))||0;
await fetch(B+'/set',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code:c,field:e.target.dataset.k,value:v})});loadStok()});
document.querySelectorAll('.card.stok').forEach(x=>x.onclick=()=>{F=F==x.dataset.f?'':x.dataset.f;renderStok()});
document.getElementById('semua').onclick=()=>{F='';document.getElementById('cari').value='';renderStok()};
document.getElementById('cari').oninput=renderStok;
document.getElementById('belanja').onclick=()=>{const X=D.filter(i=>i.status=='menipis'||i.status=='habis').map(i=>{const need=Math.max((i.min||0)*2-(i.stok||0),0);let t='• '+i.nama+' — stok '+fmt(i.stok||0)+' '+i.satuan;if(need>0){t+=' → order ±'+fmt(need)+' '+i.satuan;if(i.isi_bal>0)t+=' (±'+Math.ceil(need/i.isi_bal)+' bal)'}return t});
const txt='Daftar belanja:\n'+(X.join('\n')||'(semua aman)');navigator.clipboard?navigator.clipboard.writeText(txt).then(()=>alert('Tersalin:\n\n'+txt)):alert(txt)};
async function loadStok(){const r=await fetch(B+'/data');const j=await r.json();D=j.items;renderStok();
document.getElementById('mut').innerHTML=j.mutasi.map(m=>'<div>'+esc(m.Waktu)+' — <b>'+esc(m.Jenis)+'</b> '+esc(m.Nama||m.Item_Code)+': '+esc(m.Qty)+' '+esc(m.Satuan)+(m.Oleh?' ('+esc(m.Oleh)+')':'')+(m.Ref?' • '+esc(m.Ref):'')+'</div>').join('')||'Belum ada.'}
async function loadPend(){const r=await (await fetch(B+'/pending')).json();if(!r.ok)return;
PEND=r.pengajuan.length+r.permintaan.length;drawTabs();if(L)renderRingkasan();
document.getElementById('pend').innerHTML=r.pengajuan.map(b=>'<div class="box"><b>'+esc(b.jenis=='Masuk'?'📥 Barang Masuk':'🧮 Hitung Stok')+' — '+esc(b.staff)+'</b><div class="mut">'+esc(b.waktu)+(b.ref?' • '+esc(b.ref):'')+'</div>'+(b.banding?'<div class="mut" style="margin:6px 0 2px">Dipesan vs diterima ('+esc(b.ref)+'):</div>'+b.banding.map(x=>'<div>'+(Math.abs(x.sisa)<0.001?'✅':x.sisa<0?'⚠️':'🕒')+' '+esc(x.nama)+': dipesan '+fmt(x.pesan)+(x.sebelumnya>0?', sebelumnya '+fmt(x.sebelumnya):'')+', <b>datang sekarang '+fmt(x.terima)+'</b> '+esc(x.satuan)+(Math.abs(x.sisa)<0.001?' (lengkap)':x.sisa>0?' <b style="color:var(--amb)">(sisa '+fmt(x.sisa)+')</b>':' <b style="color:var(--red)">(lebih '+fmt(-x.sisa)+')</b>')+'</div>').join(''):b.items.map(i=>'<div>• '+esc(i.nama)+': <b>'+esc(i.qty)+' '+esc(i.satuan)+'</b>'+(i.sekarang===undefined?'':(b.jenis=='Hitung'?' <span class="mut">(stok sistem sekarang '+(i.sekarang===null?'belum ada':fmt(i.sekarang))+' → jadi <b>'+esc(i.qty)+'</b>)</span>':' <span class="mut">(stok '+(i.sekarang===null?'belum ada':fmt(i.sekarang))+' → '+(i.sekarang===null?'':fmt(i.sekarang+(+i.qty||0)))+')</span>'))+'</div>').join(''))+'<div style="margin-top:8px"><button class="btn" data-b="'+esc(b.batch)+'" data-a="1">✅ Setujui</button> <button class="btn r" data-b="'+esc(b.batch)+'" data-a="0">❌ Tolak</button></div></div>').join('')||'<div class="mut">Tidak ada yang menunggu.</div>';
document.getElementById('pobel').innerHTML=(r.po_belum||[]).map(p=>'<div class="box"><b>'+esc(p.po)+' — '+esc(p.supplier)+'</b> <span class="mut">'+esc(p.tgl)+(p.status_terima=='Menunggu'?' • ada kiriman nunggu persetujuan':'')+'</span>'+p.items.map(i=>'<div>• '+esc(i.nama)+': datang <b>'+fmt(i.qty-i.sisa)+'</b> dari '+fmt(i.qty)+' '+esc(i.satuan)+(i.sisa>0?' — <b style="color:var(--amb)">sisa '+fmt(i.sisa)+'</b>':' ✅')+'</div>').join('')+'<div style="margin-top:6px"><button class="btn s k" data-tutup="'+esc(p.po)+'">Tutup PO (sisa gak dikirim)</button></div></div>').join('')||'<div class="mut">Semua PO sudah lengkap.</div>';
document.getElementById('perm').innerHTML=(r.permintaan.length?'<div style="margin:4px 0 6px"><button class="btn" data-poall="'+esc(r.permintaan.map(q=>q.ID).join(','))+'">📝 Buat PO dari SEMUA permintaan ('+r.permintaan.length+')</button></div>':'')+r.permintaan.map(q=>'<div class="box"><b>'+esc(q.Nama)+': '+esc(q.Qty)+' '+esc(q.Satuan)+'</b><div class="mut">'+esc(q.Staff)+' • '+esc(q.Waktu)+(q.Catatan?' • '+esc(q.Catatan):'')+'</div><div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px"><button class="btn s" data-poall="'+esc(q.ID)+'">📝 Buat PO</button><button class="btn s k" data-q="'+esc(q.ID)+'">✔ Udah diurus sendiri</button></div></div>').join('')||'<div class="mut">Tidak ada permintaan baru.</div>';
let HID=[];try{HID=JSON.parse(localStorage.getItem('hid_setuju')||'[]')}catch(e){}
const DS=(r.disetujui||[]),DSb=DS.filter(b=>b.beres||HID.includes(b.batch)),DSo=DS.filter(b=>!b.beres&&!HID.includes(b.batch));
document.getElementById('setuju').innerHTML=(DSo.length?'':'<div class="mut">✅ Semua kiriman stok udah beres.</div>')+(DSb.length?'<div class="mut" style="margin:4px 0">'+DSb.length+' kiriman lain udah beres (stok opname / udah dijadiin stok real / ketimpa hitungan terbaru) — disembunyiin.</div>':'')+DSo.map(b=>'<div class="box"><b>'+(b.jenis=='Masuk'?'📥 Barang Masuk':'🧮 Hitung Stok')+' — '+esc(b.staff)+'</b> <span class="mut">'+esc(b.waktu)+(b.ref?' • '+esc(b.ref):'')+'</span>'+b.items.map(i=>'<div>• '+esc(i.nama)+': <b>'+esc(i.qty)+' '+esc(i.satuan)+'</b></div>').join('')+'<div style="margin-top:6px;display:flex;gap:6px;flex-wrap:wrap"><button class="btn s k" data-jh="'+esc(b.batch)+'">🔁 Jadikan stok real</button><button class="btn s" data-hid="'+esc(b.batch)+'">✓ Udah dicek, sembunyiin</button></div></div>').join('');
document.getElementById('permsel').innerHTML=(r.permintaan_selesai||[]).map(q=>'<div class="box"><b>'+esc(q.Nama)+': '+esc(q.Qty)+' '+esc(q.Satuan)+'</b> <span class="mut">'+esc(q.Staff)+' • '+esc(q.Waktu)+'</span><div style="margin-top:6px"><button class="btn s" data-poall="'+esc(q.ID)+'">📝 Buat PO</button></div></div>').join('')||'<div class="mut">Gak ada.</div>';
document.getElementById('ord').innerHTML=r.orders.map(o=>'<div>'+(o.dikirim?'✅':'⏳')+' '+esc(o.invoice)+' — '+esc(o.customer)+(o.dikirim?' (dikirim oleh '+esc(o.dikirim_oleh)+')':' (belum dikirim)')+'</div>').join('')||'Belum ada.'}
showTab((location.hash||'').slice(1)&&TABS.some(t=>t[0]==location.hash.slice(1))?location.hash.slice(1):'ringkasan');
loadLap();loadStok();loadPend();setInterval(()=>{loadLap();loadStok();loadPend()},120000);
</script></body></html>"""
