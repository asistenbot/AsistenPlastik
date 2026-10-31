"""Halaman dashboard owner (HTML satu file, tanpa library luar)."""

DASH_HTML = r"""<!doctype html><html lang="id"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Dashboard Owner</title><style>
:root{--g:#0f7b6c;--bg:#f4f7f6;--ink:#1c2b28;--mu:#6b7c78;--ln:#dbe4e1;--red:#c0281c;--amb:#b27a00;--blu:#2a6fb5}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}input,select,button{font-size:16px}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.4 system-ui,sans-serif}
header{background:var(--g);color:#fff;padding:12px max(16px,env(safe-area-inset-right)) 12px max(16px,env(safe-area-inset-left));display:flex;align-items:center;gap:10px;flex-wrap:wrap}
header h1{margin:0;font-size:18px;flex:1}header input{padding:7px 9px;border:0;border-radius:8px;font:inherit}
.tabs{display:flex;overflow-x:auto;background:#fff;border-bottom:1px solid var(--ln);position:sticky;top:0;z-index:5}
.tabs{-webkit-overflow-scrolling:touch}.tabs button{-webkit-appearance:none;flex:0 0 auto;padding:12px 14px;border:0;background:none;font:inherit;font-weight:600;color:var(--mu);border-bottom:3px solid transparent;white-space:nowrap}
.tabs button.on{color:var(--g);border-color:var(--g)}
main{max-width:1100px;margin:0 auto;padding:12px}.pane{display:none}.pane.on{display:block}
.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:6px}
.card{background:#fff;border:1px solid var(--ln);border-radius:12px;padding:10px;text-align:center}
.card b{display:block;font-size:19px;margin-top:2px}.card span{font-size:12px;color:var(--mu)}.card small{display:block;font-size:11px;color:var(--mu)}
.card.stok{cursor:pointer}.red b{color:var(--red)}.amb b{color:var(--amb)}.grn b{color:#14633a}.blu b{color:var(--blu)}
h2{font-size:15px;margin:18px 2px 6px}.box{background:#fff;border:1px solid var(--ln);border-radius:12px;padding:10px 12px;margin:8px 0}
.mut{font-size:13px;color:var(--mu)}.mut div{padding:4px 0;border-bottom:1px solid var(--ln)}
.hb{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:13px}.hb .l{flex:0 0 38%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.hb .t{flex:1;background:#eef3f1;border-radius:6px;height:18px;position:relative}.hb .t i{display:block;height:100%;border-radius:6px;background:var(--g)}
.hb .v{flex:0 0 auto;min-width:84px;text-align:right}
.vc{display:flex;align-items:flex-end;gap:3px;height:120px;margin-top:6px}.vc div{flex:1;display:flex;flex-direction:column;justify-content:flex-end;align-items:center;height:100%}
.vc i{display:block;width:100%;background:var(--g);border-radius:3px 3px 0 0;min-height:1px}.vc small{font-size:10px;color:var(--mu);margin-top:2px}
.vc2 i{width:48%}.vc2 div{flex-direction:row;align-items:flex-end;gap:2px;position:relative;padding-bottom:14px}.vc2 small{position:absolute;bottom:0}
.lg{font-size:12px;color:var(--mu);margin-top:6px}.lg b{display:inline-block;width:10px;height:10px;border-radius:2px;margin:0 4px 0 8px}
table{width:100%;border-collapse:collapse;background:#fff;border:1px solid var(--ln);border-radius:12px;overflow:hidden}
th,td{padding:8px 10px;border-bottom:1px solid var(--ln);text-align:left;vertical-align:middle}th{font-size:12px;color:var(--mu);background:#f0f5f3}
td.n{text-align:right;white-space:nowrap}tr.menipis td:first-child{border-left:4px solid #e0a800}tr.habis td:first-child{border-left:4px solid #d9392b}tr.belum td:first-child{border-left:4px solid #bbb}tr.aman td:first-child{border-left:4px solid #2e9e63}
td input[type=text],td input:not([type]){width:70px;padding:6px;border:1px solid var(--ln);border-radius:6px;text-align:right;font:inherit}
input[type=search]{width:100%;padding:10px;border:1px solid var(--ln);border-radius:8px;font:inherit;margin:10px 0 8px}
.btn{background:var(--g);color:#fff;border:0;border-radius:8px;padding:9px 13px;font:inherit;font-weight:600}.btn.s{padding:5px 9px;font-size:13px}.btn.r{background:#b3261e}.btn.k{background:#555}
.pill{display:inline-block;font-size:12px;padding:2px 8px;border-radius:10px;font-weight:600}
.p-belum{background:#ffe3df;color:#9a1b12}.p-sudah{background:#d9f3e4;color:#14633a}.p-x{background:#e8e8e8;color:#555}.p-telat{background:#ffd9d6;color:#9a1b12}
.act{background:#fff8e6;border:1px solid #f0dca0;border-radius:12px;padding:10px 12px;margin:8px 0;font-size:14px}.act div{padding:2px 0}
.empty{color:var(--mu);padding:8px 2px;font-size:14px}
@media(min-width:900px){.cards{gap:12px}.card b{font-size:22px}}
@media(max-width:700px){.cards{grid-template-columns:repeat(2,1fr)}.hb .l{flex-basis:44%}.hide-s{display:none}}
</style></head><body>
<header><h1>📊 __BIZ__</h1><input type="month" id="bln" placeholder="2026-10" pattern="[0-9]{4}-[0-9]{2}"></header>
<div class="tabs" id="tabs"></div>
<main>
<div class="pane" id="p_ringkasan"></div>
<div class="pane" id="p_penjualan"></div>
<div class="pane" id="p_tagihan"></div>
<div class="pane" id="p_utang"></div>
<div class="pane" id="p_kas"></div>
<div class="pane" id="p_stok">
<div class="cards"><div class="card stok red" data-f="habis"><b id="c_h">0</b><span>Habis</span></div><div class="card stok amb" data-f="menipis"><b id="c_m">0</b><span>Menipis</span></div>
<div class="card stok grn" data-f="aman"><b id="c_a">0</b><span>Aman</span></div><div class="card stok" data-f="belum"><b id="c_b">0</b><span>Belum dihitung</span></div></div>
<div style="display:flex;gap:8px;margin-top:10px"><button class="btn" id="belanja">📋 Salin daftar belanja</button><button class="btn k" id="semua">Tampilkan semua</button></div>
<input type="search" id="cari" placeholder="cari barang...">
<table><thead><tr><th>Barang</th><th class="n">Stok</th><th class="n">Min</th><th>Status</th><th class="n hide-s">Isi 1 bal</th><th class="hide-s">Supplier</th></tr></thead><tbody id="tb"></tbody></table></div>
<div class="pane" id="p_gudang">
<h2>✅ Menunggu persetujuan</h2><div id="pend"></div>
<h2>🛒 Permintaan barang dari gudang</h2><div id="perm"></div>
<h2>🚚 Status pengiriman pesanan</h2><div class="mut" id="ord"></div>
<h2>Gerakan stok terakhir</h2><div class="mut" id="mut"></div></div>
</main>
<script>
const TOKEN=location.pathname.split('/')[2],B='/dashboard/'+TOKEN;let D=[],F='',L=null,TAB='ringkasan';
const esc=s=>String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=n=>(Math.round(n*100)/100).toLocaleString('id-ID');
const rp=n=>'Rp'+Math.round(n||0).toLocaleString('id-ID');
const rps=n=>{n=n||0;const a=Math.abs(n);return a>=1e9?'Rp'+(n/1e9).toFixed(1).replace('.',',')+' M':a>=1e6?'Rp'+(n/1e6).toFixed(1).replace('.',',')+' jt':rp(n)};
const dmy=s=>s?String(s).slice(8,10)+'-'+String(s).slice(5,7)+'-'+String(s).slice(0,4):'-';
const TABS=[['ringkasan','🏠 Ringkasan'],['penjualan','📈 Penjualan'],['tagihan','🧾 Tagihan'],['utang','💸 Utang Supplier'],['kas','💰 Kas'],['stok','📦 Stok'],['gudang','🏭 Gudang']];
let PEND=0;function drawTabs(){document.getElementById('tabs').innerHTML=TABS.map(t=>'<button data-t="'+t[0]+'" class="'+(t[0]==TAB?'on':'')+'">'+t[1]+(t[0]=='gudang'&&PEND?' <span class="pill p-belum">'+PEND+'</span>':'')+'</button>').join('')}drawTabs();
function showTab(t){TAB=t;try{location.hash=t}catch(_){}document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('on',b.dataset.t==t));document.querySelectorAll('.pane').forEach(p=>p.classList.toggle('on',p.id=='p_'+t))}
document.getElementById('tabs').onclick=e=>{const b=e.target.closest('button');if(b)showTab(b.dataset.t)};
function card(l,v,cls,sub){return '<div class="card '+(cls||'')+'"><span>'+l+'</span><b>'+v+'</b>'+(sub?'<small>'+sub+'</small>':'')+'</div>'}
function hbars(arr,empty){if(!arr||!arr.length)return '<div class="empty">'+(empty||'Belum ada data.')+'</div>';const mx=Math.max(...arr.map(a=>a.total),1);
return arr.map(a=>'<div class="hb"><div class="l" title="'+esc(a.nama)+'">'+esc(a.nama)+'</div><div class="t"><i style="width:'+Math.max(a.total/mx*100,1)+'%"></i></div><div class="v">'+rps(a.total)+'</div></div>').join('')}
function vbars(arr,key,lab){const mx=Math.max(...arr.map(a=>a[key]),1);return '<div class="vc">'+arr.map(a=>'<div title="'+esc(a.tgl||a.bulan)+': '+rp(a[key])+'"><i style="height:'+(a[key]/mx*100)+'%"></i><small>'+lab(a)+'</small></div>').join('')+'</div>'}
function pill(k,telat){if(telat)return '<span class="pill p-telat">Lewat tempo</span>';return k=='belum'?'<span class="pill p-belum">Belum kontra bon</span>':k=='sudah'?'<span class="pill p-sudah">Sudah kontra bon</span>':'<span class="pill p-x">Tanpa kontra bon</span>'}

function renderRingkasan(){const r=L.ringkas;let h='<h2>'+esc(L.bulan_label)+'</h2><div class="cards">'+
card('Omzet',rps(r.omzet),'blu',r.jml_invoice+' invoice')+card('Estimasi laba kotor',rps(r.laba_kotor),r.laba_kotor>=0?'grn':'red',r.laba_lengkap?'dari harga beli PriceList':'harga beli belum lengkap')+
card('Sudah dibayar',rps(r.lunas),'grn')+card('Belum dibayar',rps(r.belum_lunas),'amb')+'</div><div class="cards">'+
card('Total piutang',rps(r.total_piutang),'amb',r.jml_tagihan+' invoice')+card('Belum kontra bon',r.belum_kontra_bon,r.belum_kontra_bon?'red':'grn','invoice')+
card('Lewat tempo',rps(r.total_telat),r.telat?'red':'grn',r.telat+' invoice')+card('Utang supplier',rps(r.total_utang),'amb',r.jml_po_terbuka+' PO terbuka')+'</div><div class="cards">'+
card('Kas masuk',rps(r.kas_masuk),'grn')+card('Kas keluar',rps(r.kas_keluar),'red')+card('Laba kas',rps(r.kas_laba),r.kas_laba>=0?'grn':'red')+card('Saldo kas (semua)',rps(r.saldo_kas),'blu')+'</div>';
const a=[];if(r.belum_kontra_bon)a.push('📋 '+r.belum_kontra_bon+' invoice belum di-kontra bon → tab Tagihan');if(r.telat)a.push('⏰ '+r.telat+' invoice lewat tempo ('+rp(r.total_telat)+')');
if(r.po_telat)a.push('💸 '+r.po_telat+' PO supplier lewat jatuh tempo → tab Utang Supplier');if(PEND)a.push('🏭 '+PEND+' kiriman dari staff gudang nunggu persetujuan lu → tab Gudang');if(r.stok_habis)a.push('🔴 '+r.stok_habis+' barang stok habis');if(r.stok_menipis)a.push('🟡 '+r.stok_menipis+' barang stok menipis → tab Stok');
h+='<h2>Perlu tindakan</h2>'+(a.length?'<div class="act">'+a.map(x=>'<div>'+x+'</div>').join('')+'</div>':'<div class="box">✅ Semua beres, gak ada yang mendesak.</div>');
h+='<h2>Tren 6 bulan (omzet)</h2><div class="box">'+vbars(L.tren,'omzet',a=>esc(a.bulan))+'</div>';
h+='<h2>Kas masuk vs keluar (6 bulan)</h2><div class="box"><div class="vc vc2">'+(()=>{const mx=Math.max(...L.tren.map(a=>Math.max(a.kas_masuk,a.kas_keluar)),1);return L.tren.map(a=>'<div title="'+esc(a.bulan)+'"><i style="height:'+(a.kas_masuk/mx*100)+'%"></i><i style="height:'+(a.kas_keluar/mx*100)+'%;background:#d9392b"></i><small>'+esc(a.bulan)+'</small></div>').join('')})()+'</div><div class="lg"><b style="background:var(--g)"></b>Masuk<b style="background:#d9392b"></b>Keluar</div></div>';
document.getElementById('p_ringkasan').innerHTML=h}

function renderPenjualan(){const r=L.ringkas;let h='<div class="cards">'+card('Omzet '+esc(L.bulan_label),rps(r.omzet),'blu')+card('Jumlah invoice',r.jml_invoice)+card('Rata-rata / invoice',rps(r.rata_invoice))+card('Estimasi laba kotor',rps(r.laba_kotor),'grn',r.laba_lengkap?'':'harga beli belum lengkap')+'</div>';
h+='<h2>Omzet per hari</h2><div class="box">'+vbars(L.harian,'total',a=>(+a.tgl.slice(8,10))%5==1||a.tgl.slice(8,10)=='31'?+a.tgl.slice(8,10):'')+'</div>';
h+='<h2>Customer teratas</h2><div class="box">'+hbars(L.top_customer)+'</div>';
h+='<h2>Produk terlaris (rupiah)</h2><div class="box">'+hbars(L.top_produk.map(p=>({nama:p.nama+' ('+fmt(p.qty)+' '+p.satuan+')',total:p.total})))+'</div>';
h+='<h2>Per kategori</h2><div class="box">'+hbars(L.per_kategori)+'</div>';
h+='<h2>Daftar invoice bulan ini</h2>'+(L.invoice_bulan.length?'<table><thead><tr><th>Invoice</th><th>Customer</th><th class="n">Total</th><th>Status</th></tr></thead><tbody>'+L.invoice_bulan.map(o=>'<tr><td>'+esc(o.invoice)+'<br><small style="color:#888">'+dmy(o.tgl)+'</small></td><td>'+esc(o.customer)+'</td><td class="n">'+rp(o.total)+'</td><td>'+(o.status=='Lunas'?'<span class="pill p-sudah">Lunas</span>':'<span class="pill p-belum">Belum</span>')+'</td></tr>').join('')+'</tbody></table>':'<div class="empty">Belum ada invoice bulan ini.</div>');
document.getElementById('p_penjualan').innerHTML=h}

function renderTagihan(){const r=L.ringkas;let h='<div class="cards">'+card('Total piutang',rps(r.total_piutang),'amb',r.jml_tagihan+' invoice')+card('Belum kontra bon',r.belum_kontra_bon,r.belum_kontra_bon?'red':'grn')+card('Lewat tempo',rps(r.total_telat),r.telat?'red':'grn')+card('Umur >30 hari',rps(L.aging[3].total),L.aging[3].total?'red':'grn')+'</div>';
h+='<h2>Umur piutang</h2><div class="box">'+hbars(L.aging)+'</div><h2>Piutang per customer</h2><div class="box">'+hbars(L.piutang_customer,'Gak ada piutang 🎉')+'</div>';
h+='<h2>Invoice belum lunas</h2>';
if(!L.tagihan.length)h+='<div class="empty">Semua invoice udah lunas 🎉</div>';else{
h+='<div style="margin:6px 0"><button class="btn" id="kbSel">✅ Tandai yang dicentang: sudah kontra bon</button></div><table><thead><tr><th></th><th>Invoice</th><th class="n">Total</th><th>Status</th><th></th></tr></thead><tbody>'+L.tagihan.map(t=>'<tr><td>'+(t.kontra_bon=='belum'?'<input type="checkbox" class="kbc" value="'+esc(t.invoice)+'">':'')+'</td><td><b>'+esc(t.customer)+'</b><br><small style="color:#888">'+esc(t.invoice)+' • '+dmy(t.tgl)+' • '+t.umur+' hari</small></td><td class="n">'+rp(t.total)+'</td><td>'+pill(t.kontra_bon,t.telat)+(t.jadwal?'<br><small style="color:#888">'+(t.kontra_bon=='belum'?'jadwal ':'cek bayar ')+dmy(t.jadwal)+'</small>':'')+'</td><td><button class="btn s k" data-lunas="'+esc(t.invoice)+'" data-n="'+esc(t.customer)+'" data-j="'+t.total+'">Lunas</button></td></tr>').join('')+'</tbody></table>'}
document.getElementById('p_tagihan').innerHTML=h}

function renderUtang(){const r=L.ringkas;let h='<div class="cards">'+card('Total utang supplier',rps(r.total_utang),'amb')+card('PO terbuka',r.jml_po_terbuka)+card('PO lewat tempo',r.po_telat,r.po_telat?'red':'grn')+'</div>';
h+='<h2>Utang per supplier</h2><div class="box">'+hbars(L.utang_supplier,'Gak ada utang 🎉')+'</div><h2>PO yang belum lunas</h2>';
h+=L.po_terbuka.length?'<table><thead><tr><th>PO</th><th>Supplier</th><th class="n">Total</th><th>Jatuh tempo</th></tr></thead><tbody>'+L.po_terbuka.map(o=>'<tr><td>'+esc(o.po)+'<br><small style="color:#888">'+dmy(o.tgl)+'</small></td><td>'+esc(o.supplier)+'</td><td class="n">'+rp(o.total)+'</td><td>'+(o.jatuh_tempo?(o.telat?'<span class="pill p-telat">'+dmy(o.jatuh_tempo)+'</span>':dmy(o.jatuh_tempo)):'-')+'</td></tr>').join('')+'</tbody></table>':'<div class="empty">Semua PO udah lunas.</div>';
h+='<div class="mut" style="margin-top:8px">Bayar utang: ketik <b>/bayarutang</b> di Telegram, atau balas pengingat PO.</div>';
document.getElementById('p_utang').innerHTML=h}

function renderKas(){const r=L.ringkas;let h='<div class="cards">'+card('Kas masuk',rps(r.kas_masuk),'grn',esc(L.bulan_label))+card('Kas keluar',rps(r.kas_keluar),'red')+card('Laba/rugi kas',rps(r.kas_laba),r.kas_laba>=0?'grn':'red')+card('Saldo kas (semua)',rps(r.saldo_kas),'blu')+'</div>';
h+='<h2>Kas masuk per kategori</h2><div class="box">'+hbars(L.kas_masuk_kat)+'</div><h2>Kas keluar per kategori</h2><div class="box">'+hbars(L.kas_keluar_kat)+'</div><h2>Transaksi kas bulan ini</h2>';
h+=L.kas_list.length?'<table><thead><tr><th>Tanggal</th><th>Keterangan</th><th class="n">Jumlah</th></tr></thead><tbody>'+L.kas_list.map(k=>'<tr><td>'+dmy(k.tgl)+'</td><td>'+esc(k.kategori)+'<br><small style="color:#888">'+esc(k.ket)+'</small></td><td class="n" style="color:'+(k.jenis=='Masuk'?'#14633a':'#c0281c')+'">'+(k.jenis=='Masuk'?'+':'-')+rp(k.jumlah)+'</td></tr>').join('')+'</tbody></table>':'<div class="empty">Belum ada transaksi kas bulan ini.</div>';
document.getElementById('p_kas').innerHTML=h}

async function loadLap(){const bl=document.getElementById('bln').value;try{const r=await fetch(B+'/laporan?bulan='+encodeURIComponent(bl));const j=await r.json();if(!j.ok)throw 0;L=j;if(!bl)document.getElementById('bln').value=j.bulan;
renderRingkasan();renderPenjualan();renderTagihan();renderUtang();renderKas()}catch(e){document.getElementById('p_ringkasan').innerHTML='<div class="box">Gagal ambil laporan. Coba refresh sebentar lagi (Google Sheets lagi sibuk).</div>'}}
document.getElementById('bln').onchange=loadLap;

document.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;
if(b.id=='kbSel'){const v=[...document.querySelectorAll('.kbc:checked')].map(x=>x.value);if(!v.length){alert('Centang dulu invoice yang udah di-kontra bon.');return}
if(!confirm('Tandai '+v.length+' invoice sudah kontra bon?'))return;b.disabled=true;const r=await (await fetch(B+'/kontrabon',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({invoices:v})})).json();alert(r.ok?'✅ '+r.n+' invoice ditandai sudah kontra bon.':'Gagal');loadLap()}
if(b.dataset.lunas){if(!confirm('Tandai '+b.dataset.lunas+' ('+b.dataset.n+', '+rp(+b.dataset.j)+') LUNAS? Otomatis masuk Kas.'))return;b.disabled=true;const r=await (await fetch(B+'/lunas',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({invoice:b.dataset.lunas})})).json();alert(r.ok?'✅ Lunas '+rp(r.total)+' & dicatat ke Kas.':(r.error||'Gagal'));loadLap()}
if(b.dataset.b){if(!confirm(b.dataset.a=='1'?'Setujui pengajuan ini? Stok akan berubah.':'Tolak pengajuan ini?'))return;b.disabled=true;await fetch(B+'/decide',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({batch:b.dataset.b,approve:b.dataset.a=='1'})});loadStok();loadPend()}
if(b.dataset.q){b.disabled=true;await fetch(B+'/permintaan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:b.dataset.q,status:'Selesai'})});loadPend()}});

/* ---------- stok & gudang ---------- */
function stokTxt(i){if(i.stok===null)return '-';let t=fmt(i.stok)+' '+esc(i.satuan);if(i.isi_bal>0&&i.stok>=i.isi_bal)t+=' <small>('+(Math.round(i.stok/i.isi_bal*10)/10)+' bal)</small>';return t}
const ORD={habis:0,menipis:1,belum:2,aman:3};
function renderStok(){const q=document.getElementById('cari').value.toLowerCase();let X=D.filter(i=>(!F||i.status==F)&&(i.nama+' '+i.code+' '+i.kategori).toLowerCase().includes(q));
X.sort((a,b)=>ORD[a.status]-ORD[b.status]||a.nama.localeCompare(b.nama));
document.getElementById('tb').innerHTML=X.map(i=>'<tr class="'+i.status+'"><td><b>'+esc(i.nama)+'</b><br><small style="color:#888">'+esc(i.code)+'</small></td><td class="n">'+stokTxt(i)+'</td><td class="n"><input data-k="min" data-c="'+esc(i.code)+'" value="'+(i.min||'')+'" inputmode="decimal"></td><td>'+({aman:'🟢 Aman',menipis:'🟡 Menipis',habis:'🔴 Habis',belum:'⚪ Belum dihitung'})[i.status]+'</td><td class="n hide-s"><input data-k="isi_bal" data-c="'+esc(i.code)+'" value="'+(i.isi_bal||'')+'" inputmode="decimal"></td><td class="hide-s">'+esc(i.supplier||'')+'</td></tr>').join('');
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
document.getElementById('pend').innerHTML=r.pengajuan.map(b=>'<div class="box"><b>'+esc(b.jenis=='Masuk'?'📥 Barang Masuk':'🧮 Hitung Stok')+' — '+esc(b.staff)+'</b><div class="mut">'+esc(b.waktu)+(b.ref?' • '+esc(b.ref):'')+'</div>'+b.items.map(i=>'<div>• '+esc(i.nama)+': <b>'+esc(i.qty)+' '+esc(i.satuan)+'</b></div>').join('')+'<div style="margin-top:8px"><button class="btn" data-b="'+esc(b.batch)+'" data-a="1">✅ Setujui</button> <button class="btn r" data-b="'+esc(b.batch)+'" data-a="0">❌ Tolak</button></div></div>').join('')||'<div class="mut">Tidak ada yang menunggu.</div>';
document.getElementById('perm').innerHTML=r.permintaan.map(q=>'<div class="box"><b>'+esc(q.Nama)+': '+esc(q.Qty)+' '+esc(q.Satuan)+'</b><div class="mut">'+esc(q.Staff)+' • '+esc(q.Waktu)+(q.Catatan?' • '+esc(q.Catatan):'')+'</div><button class="btn s" data-q="'+esc(q.ID)+'">✔ Tandai sudah diproses</button></div>').join('')||'<div class="mut">Tidak ada permintaan baru.</div>';
document.getElementById('ord').innerHTML=r.orders.map(o=>'<div>'+(o.dikirim?'✅':'⏳')+' '+esc(o.invoice)+' — '+esc(o.customer)+(o.dikirim?' (dikirim oleh '+esc(o.dikirim_oleh)+')':' (belum dikirim)')+'</div>').join('')||'Belum ada.'}
showTab((location.hash||'').slice(1)&&TABS.some(t=>t[0]==location.hash.slice(1))?location.hash.slice(1):'ringkasan');
loadLap();loadStok();loadPend();setInterval(()=>{loadLap();loadStok();loadPend()},120000);
</script></body></html>"""
