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
#phead{display:none}
@media print{
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
<header><h1>📊 __BIZ__</h1><button class="btn k" id="pr1">🖨️ Cetak halaman ini</button><button class="btn k" id="prAll">🖨️ Cetak semua laporan</button><input type="month" id="bln" placeholder="2026-10" pattern="[0-9]{4}-[0-9]{2}"><button class="btn k" id="semuaBln">Semua bulan</button></header>
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
function showTab(t){TAB=t;try{location.hash=t}catch(_){}document.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('on',b.dataset.t==t));document.querySelectorAll('.pane').forEach(p=>p.classList.toggle('on',p.id=='p_'+t))}
document.getElementById('tabs').onclick=e=>{const b=e.target.closest('button');if(b)showTab(b.dataset.t)};
function card(l,v,cls,sub){return '<div class="card '+(cls||'')+'"><span>'+l+'</span><b>'+v+'</b>'+(sub?'<small>'+sub+'</small>':'')+'</div>'}
function hbars(arr,empty){if(!arr||!arr.length)return '<div class="empty">'+(empty||'Belum ada data.')+'</div>';const mx=Math.max(...arr.map(a=>a.total),1);
return arr.map(a=>'<div class="hb"><div class="l" title="'+esc(a.nama)+'">'+esc(a.nama)+'</div><div class="t"><i style="width:'+Math.max(a.total/mx*100,1)+'%"></i></div><div class="v">'+rps(a.total)+'</div></div>').join('')}
function vbars(arr,key,lab){const mx=Math.max(...arr.map(a=>a[key]),1);return '<div class="vc">'+arr.map(a=>'<div title="'+esc(a.tgl||a.bulan)+': '+rp(a[key])+'"><i style="height:'+(a[key]/mx*100)+'%"></i><small>'+lab(a)+'</small></div>').join('')+'</div>'}
function dok(inv){return '<a class="btn s k" style="text-decoration:none;display:inline-block" target="_blank" rel="noopener" href="'+B+'/dok/'+encodeURIComponent(inv)+'/inv">🧾 Invoice</a> <a class="btn s k" style="text-decoration:none;display:inline-block" target="_blank" rel="noopener" href="'+B+'/dok/'+encodeURIComponent(inv)+'/sj">🚚 Surat Jalan</a> <a class="btn s k" style="text-decoration:none;display:inline-block" href="'+B+'/dok/'+encodeURIComponent(inv)+'/invtxt">📝 Inv teks</a> <a class="btn s k" style="text-decoration:none;display:inline-block" href="'+B+'/dok/'+encodeURIComponent(inv)+'/sjtxt">📝 SJ teks</a> <button class="btn s" style="background:var(--blu)" data-th="'+esc(inv)+'">📠 Thermal</button>'}
function pill(k,telat){if(telat)return '<span class="pill p-telat">Lewat tempo</span>';return k=='belum'?'<span class="pill p-belum">Belum kontra bon</span>':k=='sudah'?'<span class="pill p-sudah">Sudah kontra bon</span>':'<span class="pill p-x">Tanpa kontra bon</span>'}

function renderRingkasan(){const r=L.ringkas;let h='<h2>'+esc(L.bulan_label)+'</h2><div class="cards">'+
card('Omzet',rps(r.omzet),'blu',r.jml_invoice+' invoice')+card('Estimasi laba kotor',rps(r.laba_kotor),r.laba_kotor>=0?'grn':'red',(r.laba_lengkap?'dari harga beli PriceList':'harga beli belum lengkap')+(r.komisi_bulan?' • udah dipotong komisi '+rps(r.komisi_bulan):''))+
card('Sudah dibayar',rps(r.lunas),'grn')+card('Belum dibayar',rps(r.belum_lunas),'amb')+'</div><div class="cards">'+
card('Total piutang',rps(r.total_piutang),'amb',r.jml_tagihan+' invoice')+card('Belum kontra bon',r.belum_kontra_bon,r.belum_kontra_bon?'red':'grn','invoice')+
card('Lewat tempo',rps(r.total_telat),r.telat?'red':'grn',r.telat+' invoice')+card('Utang supplier',rps(r.total_utang),'amb',r.jml_po_terbuka+' PO terbuka')+'</div><div class="cards">'+
card('Kas masuk',rps(r.kas_masuk),'grn')+card('Kas keluar',rps(r.kas_keluar),'red')+card('Laba kas',rps(r.kas_laba),r.kas_laba>=0?'grn':'red')+card('Saldo kas (semua)',rps(r.saldo_kas),'blu')+'</div>';
const a=[];if(r.web_menunggu)a.push('🌐 '+r.web_menunggu+' order dari link web nunggu lu klik "Simpan" di Telegram');if(r.belum_kirim)a.push('🚚 '+r.belum_kirim+' invoice belum dikirim → bagian bawah Ringkasan');if(r.belum_kontra_bon)a.push('📋 '+r.belum_kontra_bon+' invoice belum di-kontra bon → tab Tagihan');if(r.telat)a.push('⏰ '+r.telat+' invoice lewat tempo ('+rp(r.total_telat)+')');
if(r.komisi_belum)a.push('🤫 '+r.komisi_belum+' komisi belum dibayar ('+rp(r.komisi_belum_total)+') → tab Tagihan');if(r.po_telat)a.push('💸 '+r.po_telat+' PO supplier lewat jatuh tempo → tab Utang Supplier');if(PEND)a.push('🏭 '+PEND+' kiriman dari staff gudang nunggu persetujuan lu → tab Gudang');if(r.stok_habis)a.push('🔴 '+r.stok_habis+' barang stok habis');if(r.stok_menipis)a.push('🟡 '+r.stok_menipis+' barang stok menipis → tab Stok');
h+='<h2>Perlu tindakan</h2>'+(a.length?'<div class="act">'+a.map(x=>'<div>'+x+'</div>').join('')+'</div>':'<div class="box">✅ Semua beres, gak ada yang mendesak.</div>');
h+='<h2>Tren 6 bulan (omzet)</h2><div class="box">'+vbars(L.tren,'omzet',a=>esc(a.bulan))+'</div>';
h+='<h2>Kas masuk vs keluar (6 bulan)</h2><div class="box"><div class="vc vc2">'+(()=>{const mx=Math.max(...L.tren.map(a=>Math.max(a.kas_masuk,a.kas_keluar)),1);return L.tren.map(a=>'<div title="'+esc(a.bulan)+'"><i style="height:'+(a.kas_masuk/mx*100)+'%"></i><i style="height:'+(a.kas_keluar/mx*100)+'%;background:#d9392b"></i><small>'+esc(a.bulan)+'</small></div>').join('')})()+'</div><div class="lg"><b style="background:var(--g)"></b>Masuk<b style="background:#d9392b"></b>Keluar</div></div>';
h+='<h2>🌐 Order web menunggu persetujuan</h2>'+(L.web_list.length?'<div class="box">'+L.web_list.map(w=>'<div>• <b>'+esc(w.nama)+'</b> — '+w.n_item+' item • '+esc(w.waktu)+'</div>').join('')+'<div class="mut" style="margin-top:6px">Klik ✅ Simpan di Telegram biar jadi invoice.</div></div>':'<div class="empty">Gak ada.</div>');
h+='<h2>🚚 Invoice belum dikirim</h2>'+(L.belum_kirim_list.length?'<div style="margin:6px 0"><button class="btn k" id="kirimAll">✅ Tandai SEMUA sudah dikirim ('+L.ringkas.belum_kirim+')</button></div><table><thead><tr><th>Invoice</th><th>Customer</th><th>Req. kirim</th></tr></thead><tbody>'+L.belum_kirim_list.map(o=>'<tr><td>'+esc(o.invoice)+'<br><small style="color:#888">'+dmy(o.tgl)+' • '+o.n_item+' item</small><div style="margin-top:4px">'+dok(o.invoice)+' <button class="btn s" data-kirim="'+esc(o.invoice)+'">✅ Sudah dikirim</button></div></td><td>'+esc(o.customer)+'</td><td>'+(o.kirim?esc(o.kirim):'-')+'</td></tr>').join('')+'</tbody></table>':'<div class="empty">Semua udah dikirim 🎉</div>');
document.getElementById('p_ringkasan').innerHTML=h}

function renderPenjualan(){const r=L.ringkas;let h='<div class="cards">'+card('Omzet '+esc(L.bulan_label),rps(r.omzet),'blu')+card('Jumlah invoice',r.jml_invoice)+card('Rata-rata / invoice',rps(r.rata_invoice))+card('Estimasi laba kotor',rps(r.laba_kotor),'grn',r.laba_lengkap?'':'harga beli belum lengkap')+'</div>';
h+=L.bulan=='semua'?'<h2>Omzet per bulan</h2><div class="box">'+vbars(L.harian,'total',a=>esc(a.label||a.tgl))+'</div>':'<h2>Omzet per hari</h2><div class="box">'+vbars(L.harian,'total',a=>(+a.tgl.slice(8,10))%5==1||a.tgl.slice(8,10)=='31'?+a.tgl.slice(8,10):'')+'</div>';
h+='<h2>Customer teratas</h2><div class="box">'+hbars(L.top_customer)+'</div>';
h+='<h2>Produk terlaris (rupiah)</h2><div class="box">'+hbars(L.top_produk.map(p=>({nama:p.nama+' ('+fmt(p.qty)+' '+p.satuan+')',total:p.total})))+'</div>';
h+='<h2>Per kategori</h2><div class="box">'+hbars(L.per_kategori)+'</div>';
h+='<h2>Daftar invoice bulan ini</h2>'+(L.invoice_bulan.length?'<table><thead><tr><th>Invoice</th><th>Customer</th><th class="n">Total</th><th>Status</th></tr></thead><tbody>'+L.invoice_bulan.map(o=>'<tr><td>'+esc(o.invoice)+'<br><small style="color:#888">'+dmy(o.tgl)+'</small><div style="margin-top:4px">'+dok(o.invoice)+'</div></td><td>'+esc(o.customer)+'</td><td class="n">'+rp(o.total)+'</td><td>'+(o.status=='Lunas'?'<span class="pill p-sudah">Lunas</span>':'<span class="pill p-belum">Belum</span>')+'</td></tr>').join('')+'</tbody></table>':'<div class="empty">Belum ada invoice bulan ini.</div>');
document.getElementById('p_penjualan').innerHTML=h}

function renderTagihan(){const r=L.ringkas;let h='<div class="box" style="border-color:#2a6fb5"><b>🔎 Cek transfer masuk</b><div class="mut">Ketik nominal transfer, gua cariin bon mana aja yang jumlahnya pas (termasuk yang udah ditandai lunas, biar ketahuan kalau ada yang kepencet).</div><div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px"><input id="tfn" placeholder="mis. 1.223.500 / 1,2jt" inputmode="decimal" style="flex:1;min-width:140px;padding:9px;border:1px solid var(--ln);border-radius:8px"><input id="tfc" placeholder="customer (boleh kosong)" style="flex:1;min-width:140px;padding:9px;border:1px solid var(--ln);border-radius:8px"><button class="btn" id="tfgo">Cek</button></div><div id="tfres"></div></div>'+'<div class="cards">'+card('Total piutang',rps(r.total_piutang),'amb',r.jml_tagihan+' invoice')+card('Belum kontra bon',r.belum_kontra_bon,r.belum_kontra_bon?'red':'grn')+card('Lewat tempo',rps(r.total_telat),r.telat?'red':'grn')+card('Umur >30 hari',rps(L.aging[3].total),L.aging[3].total?'red':'grn')+'</div>';
h+='<h2>🤫 Komisi jalur belakang</h2><div class="box">'+(L.komisi_setting.length?L.komisi_setting.map(k=>'<div>• '+esc(k.customer)+': <b>'+rp(k.rate)+'</b>/satuan'+(k.penerima?' → '+esc(k.penerima):'')+'</div>').join(''):'<div class="mut">Belum ada. Pasang lewat Telegram (chat pribadi): /komisi baso yen 100 Pak Andi</div>')+'</div>'+
(L.komisi_belum_list.length?'<table><thead><tr><th>Belum dibayar</th><th class="n">Komisi</th></tr></thead><tbody>'+L.komisi_belum_list.map(k=>'<tr><td><b>'+esc(k.penerima||'-')+'</b><br><small style="color:#888">'+esc(k.invoice)+' • '+esc(k.customer)+' • '+fmt(k.qty)+' × '+rp(k.rate)+'</small><div style="margin-top:4px"><button class="btn s" data-km="'+esc(k.invoice)+'" data-j="'+k.jumlah+'">✅ Sudah dibayar</button></div></td><td class="n">'+rp(k.jumlah)+'</td></tr>').join('')+'</tbody></table>':'<div class="empty">Semua komisi udah dibayar.</div>');
{const by={};L.tagihan.forEach(t=>{const k=t.customer.toLowerCase().replace(/[^a-z0-9]/g,'');(by[k]=by[k]||{nama:t.customer,inv:[],total:0}).inv.push(t);by[k].total+=t.total});
const C=Object.values(by).sort((a,b)=>b.total-a.total);
h+='<h2>📄 Rincian piutang per customer</h2>'+(C.length?C.map((c,ci)=>'<div class="box" data-cust="'+ci+'"><div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><b>'+esc(c.nama)+'</b><b>'+rp(c.total)+'</b></div><div class="mut">'+c.inv.length+' invoice belum lunas</div>'+
c.inv.slice().sort((a,b)=>a.tgl<b.tgl?-1:1).map(t=>'<label style="display:flex;gap:8px;align-items:center;padding:4px 0;border-bottom:1px solid var(--ln)"><input type="checkbox" class="pc" data-ci="'+ci+'" value="'+esc(t.invoice)+'" data-j="'+t.total+'"><span style="flex:1">'+esc(t.invoice)+' <small style="color:#888">'+dmy(t.tgl)+' • '+t.umur+' hari</small></span><span>'+rp(t.total)+'</span></label>').join('')+
'<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px"><button class="btn s" data-lb="'+ci+'">✅ Lunas yang dicentang</button><button class="btn s k" data-lball="'+ci+'">✅ Lunas semua ('+rp(c.total)+')</button><button class="btn s k" data-tf="'+ci+'">💸 Transfer sejumlah…</button><button class="btn s k" data-cr="'+ci+'">🖨️ Cetak rincian</button></div></div>').join(''):'<div class="empty">Gak ada piutang 🎉</div>');
window._PC=C}
h+='<h2>Umur piutang</h2><div class="box">'+hbars(L.aging)+'</div><h2>Piutang per customer</h2><div class="box">'+hbars(L.piutang_customer,'Gak ada piutang 🎉')+'</div>';
h+='<h2>Invoice belum lunas</h2>';
if(!L.tagihan.length)h+='<div class="empty">Semua invoice udah lunas 🎉</div>';else{
h+='<div style="margin:6px 0;display:flex;gap:6px;flex-wrap:wrap">'+(r.belum_kontra_bon?'<button class="btn" id="kbAll">✅ Semua yang belum → sudah kontra bon ('+r.belum_kontra_bon+')</button>':'')+'<button class="btn k" id="kbSel">Tandai yang dicentang saja</button></div><table><thead><tr><th></th><th>Invoice</th><th class="n">Total</th><th>Status</th></tr></thead><tbody>'+L.tagihan.map(t=>'<tr><td>'+(t.kontra_bon=='belum'?'<input type="checkbox" class="kbc" value="'+esc(t.invoice)+'">':'')+'</td><td><b>'+esc(t.customer)+'</b><br><small style="color:#888">'+esc(t.invoice)+' • '+dmy(t.tgl)+' • '+t.umur+' hari</small><div style="margin-top:4px;display:flex;gap:4px;flex-wrap:wrap">'+dok(t.invoice)+' <button class="btn s" data-lunas="'+esc(t.invoice)+'" data-n="'+esc(t.customer)+'" data-j="'+t.total+'">✅ Lunas</button></div></td><td class="n">'+rp(t.total)+'</td><td>'+pill(t.kontra_bon,t.telat)+(t.jadwal?'<br><small style="color:#888">'+(t.kontra_bon=='belum'?'jadwal ':'cek bayar ')+dmy(t.jadwal)+'</small>':'')+'</td></tr>').join('')+'</tbody></table>'}
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

let CPER='semua';
function renderCustomer(){const C=L.customers||[];let h='';
h+='<h2>⚠️ Ditandai LUNAS 7 hari terakhir</h2><div class="mut" style="margin-bottom:4px">Cek di sini kalau ada yang kepencet lunas. Klik ↩️ buat balikin jadi belum lunas (Kas Masuk-nya ikut dihapus).</div>'+
((L.lunas_baru||[]).length?'<table><thead><tr><th>Invoice</th><th class="n">Total</th></tr></thead><tbody>'+L.lunas_baru.map(o=>'<tr><td><b>'+esc(o.customer)+'</b><br><small style="color:#888">'+esc(o.invoice)+' • invoice '+dmy(o.tgl)+' • <b>lunas '+dmy(o.bayar)+'</b>'+(o.via?' • lewat '+esc(o.via):'')+'</small><div style="margin-top:4px"><button class="btn s r" data-bl="'+esc(o.invoice)+'" data-n="'+esc(o.customer)+'" data-j="'+o.total+'">↩️ Batal lunas</button></div></td><td class="n">'+rp(o.total)+'</td></tr>').join('')+'</tbody></table>':'<div class="empty">Gak ada.</div>');
const per=CPER=='semua'||L.bulan=='semua'?'':L.bulan;
h+='<h2>👥 Per customer</h2><div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px"><button class="btn s '+(CPER=='semua'?'':'k')+'" data-cper="semua">Semua waktu</button>'+(L.bulan!='semua'?'<button class="btn s '+(CPER=='bulan'?'':'k')+'" data-cper="bulan">'+esc(L.bulan_label)+'</button>':'')+'</div><input type="search" id="ccari" placeholder="cari customer..."><div id="clist"></div>';
document.getElementById('p_customer').innerHTML=h;
const data=C.map(c=>{const inv=c.invoices.filter(o=>!per||o.tgl.startsWith(per));const tot=inv.reduce((a,o)=>a+o.total,0),bel=inv.filter(o=>o.status!='Lunas').reduce((a,o)=>a+o.total,0);
const brg={};inv.forEach(o=>o.items.forEach(it=>{const k=it.nama+'|'+it.satuan;(brg[k]=brg[k]||{nama:it.nama,sat:it.satuan,qty:0,sub:0});brg[k].qty+=it.qty;brg[k].sub+=it.sub}));
return {nama:c.nama,inv,tot,bel,brg:Object.values(brg).sort((a,b)=>b.sub-a.sub)}}).filter(c=>c.inv.length).sort((a,b)=>b.tot-a.tot);
const draw=()=>{const q=(document.getElementById('ccari').value||'').toLowerCase();
document.getElementById('clist').innerHTML=data.filter(c=>c.nama.toLowerCase().includes(q)).map(c=>'<details class="box" style="padding:0"><summary style="padding:10px 12px;cursor:pointer;list-style:none;display:flex;gap:8px;align-items:center"><span style="flex:1"><b>'+esc(c.nama)+'</b><br><small style="color:#888">'+c.inv.length+' invoice • '+c.inv.filter(o=>o.status=='Lunas').length+' lunas</small></span><span style="text-align:right"><b>'+rp(c.tot)+'</b><br>'+(c.bel>0?'<span class="pill p-belum">belum '+rps(c.bel)+'</span>':'<span class="pill p-sudah">lunas semua</span>')+'</span><span class="arw" style="color:#888">▾</span></summary>'+
'<div style="padding:0 12px 12px"><div class="cards">'+card('Total belanja',rps(c.tot),'blu',c.inv.length+' invoice')+card('Sudah bayar',rps(c.tot-c.bel),'grn')+card('Belum bayar',rps(c.bel),c.bel>0?'red':'grn')+'</div>'+
'<div style="font-weight:600;margin:8px 0 4px">📦 Barang yang dipesan</div>'+c.brg.map(b=>'<div class="hb"><div class="l" title="'+esc(b.nama)+'">'+esc(b.nama)+'</div><div class="v" style="min-width:auto">'+fmt(b.qty)+' '+esc(b.sat)+'</div><div class="v">'+rp(b.sub)+'</div></div>').join('')+
'<div style="font-weight:600;margin:10px 0 4px">🧾 Invoice</div>'+c.inv.map(o=>'<div style="padding:6px 0;border-bottom:1px solid var(--ln)"><div style="display:flex;gap:6px;align-items:center"><span>'+(o.status=='Lunas'?'✅':'⏳')+'</span><span style="flex:1"><b>'+esc(o.invoice)+'</b> <small style="color:#888">'+dmy(o.tgl)+'</small></span><b>'+rp(o.total)+'</b></div><div class="mut">'+esc(o.items.map(it=>it.nama+' x'+fmt(it.qty)+' '+it.satuan).join(', '))+'</div><div style="margin-top:4px">'+(o.status=='Lunas'?'<span class="pill p-sudah">Lunas '+dmy(o.bayar)+'</span> <button class="btn s r" data-bl="'+esc(o.invoice)+'" data-n="'+esc(c.nama)+'" data-j="'+o.total+'">↩️ Batal lunas</button>':'<span class="pill p-belum">Belum lunas</span> <button class="btn s" data-lunas="'+esc(o.invoice)+'" data-n="'+esc(c.nama)+'" data-j="'+o.total+'">✅ Lunas</button>')+' '+dok(o.invoice)+'</div></div>').join('')+'</div></details>').join('')||'<div class="empty">Gak ada data.</div>'};
draw();document.getElementById('ccari').oninput=draw}
let MODE='';async function loadLap(){const bl=MODE||document.getElementById('bln').value;document.getElementById('semuaBln').style.background=MODE?'#fff':'';document.getElementById('semuaBln').style.color=MODE?'var(--g)':'';try{const r=await fetch(B+'/laporan?bulan='+encodeURIComponent(bl));const j=await r.json();if(!j.ok)throw 0;L=j;if(!bl&&j.bulan!='semua')document.getElementById('bln').value=j.bulan;
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
m.invoices.map(o=>'<div>• '+esc(o.invoice)+' <small style="color:#888">'+dmy(o.tgl)+'</small> '+rp(o.total)+' — '+(o.status=='Lunas'?'<b style="color:#b27a00">⚠️ udah ditandai lunas '+dmy(o.bayar)+'</b>':'belum lunas')+'</div>').join('')+
(m.sudah.length&&m.belum.length?'<div class="mut">↳ sebagian udah lunas duluan — cek, mungkin ada yang kepencet</div>':m.sudah.length?'<div class="mut">↳ semua udah ditandai lunas</div>':'')+
(m.belum.length?'<div style="margin-top:6px"><button class="btn s" data-tfl="'+esc(m.belum.join(','))+'">✅ Lunasin '+m.belum.length+' bon yang belum</button></div>':'')+'</div>').join('')+(H.length>1?'<div class="mut">Ada beberapa kemungkinan — pilih yang sesuai bukti transfer.</div>':'');return}
if(b.dataset.tfl){const v=b.dataset.tfl.split(',');if(!confirm('Tandai LUNAS: '+v.join(', ')+'?'))return;b.disabled=true;const r=await (await fetch(B+'/lunasbanyak',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({invoices:v})})).json();alert(r.ok?'✅ '+r.n+' bon lunas ('+rp(r.total)+').':'Gagal');loadLap();return}
if(b.dataset.cper){CPER=b.dataset.cper;renderCustomer();return}
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
document.getElementById('tb').innerHTML=X.map(i=>'<tr class="'+i.status+'"><td><b>'+esc(i.nama)+'</b><br><small style="color:#888">'+esc(i.code)+'</small></td><td class="n">'+stokTxt(i)+'</td><td><button class="btn s k" data-ubah="'+esc(i.code)+'" data-nm="'+esc(i.nama)+'" data-st="'+(i.stok===null?'':i.stok)+'" data-sat="'+esc(i.satuan)+'">✏️</button></td><td class="n"><input data-k="min" data-c="'+esc(i.code)+'" value="'+(i.min||'')+'" inputmode="decimal"></td><td>'+({aman:'🟢 Aman',menipis:'🟡 Menipis',habis:'🔴 Habis',belum:'⚪ Belum dihitung'})[i.status]+'</td><td class="n hide-s"><input data-k="isi_bal" data-c="'+esc(i.code)+'" value="'+(i.isi_bal||'')+'" inputmode="decimal"></td><td class="hide-s">'+esc(i.supplier||'')+'</td></tr>').join('');
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
document.getElementById('pend').innerHTML=r.pengajuan.map(b=>'<div class="box"><b>'+esc(b.jenis=='Masuk'?'📥 Barang Masuk':'🧮 Hitung Stok')+' — '+esc(b.staff)+'</b><div class="mut">'+esc(b.waktu)+(b.ref?' • '+esc(b.ref):'')+'</div>'+(b.banding?'<div class="mut" style="margin:6px 0 2px">Dipesan vs diterima ('+esc(b.ref)+'):</div>'+b.banding.map(x=>'<div>'+(Math.abs(x.sisa)<0.001?'✅':x.sisa<0?'⚠️':'🕒')+' '+esc(x.nama)+': dipesan '+fmt(x.pesan)+(x.sebelumnya>0?', sebelumnya '+fmt(x.sebelumnya):'')+', <b>datang sekarang '+fmt(x.terima)+'</b> '+esc(x.satuan)+(Math.abs(x.sisa)<0.001?' (lengkap)':x.sisa>0?' <b style="color:#b27a00">(sisa '+fmt(x.sisa)+')</b>':' <b style="color:#c0281c">(lebih '+fmt(-x.sisa)+')</b>')+'</div>').join(''):b.items.map(i=>'<div>• '+esc(i.nama)+': <b>'+esc(i.qty)+' '+esc(i.satuan)+'</b>'+(i.sekarang===undefined?'':(b.jenis=='Hitung'?' <span class="mut">(stok sistem sekarang '+(i.sekarang===null?'belum ada':fmt(i.sekarang))+' → jadi <b>'+esc(i.qty)+'</b>)</span>':' <span class="mut">(stok '+(i.sekarang===null?'belum ada':fmt(i.sekarang))+' → '+(i.sekarang===null?'':fmt(i.sekarang+(+i.qty||0)))+')</span>'))+'</div>').join(''))+'<div style="margin-top:8px"><button class="btn" data-b="'+esc(b.batch)+'" data-a="1">✅ Setujui</button> <button class="btn r" data-b="'+esc(b.batch)+'" data-a="0">❌ Tolak</button></div></div>').join('')||'<div class="mut">Tidak ada yang menunggu.</div>';
document.getElementById('pobel').innerHTML=(r.po_belum||[]).map(p=>'<div class="box"><b>'+esc(p.po)+' — '+esc(p.supplier)+'</b> <span class="mut">'+esc(p.tgl)+(p.status_terima=='Menunggu'?' • ada kiriman nunggu persetujuan':'')+'</span>'+p.items.map(i=>'<div>• '+esc(i.nama)+': datang <b>'+fmt(i.qty-i.sisa)+'</b> dari '+fmt(i.qty)+' '+esc(i.satuan)+(i.sisa>0?' — <b style="color:#b27a00">sisa '+fmt(i.sisa)+'</b>':' ✅')+'</div>').join('')+'<div style="margin-top:6px"><button class="btn s k" data-tutup="'+esc(p.po)+'">Tutup PO (sisa gak dikirim)</button></div></div>').join('')||'<div class="mut">Semua PO sudah lengkap.</div>';
document.getElementById('perm').innerHTML=(r.permintaan.length?'<div style="margin:4px 0 6px"><button class="btn" data-poall="'+esc(r.permintaan.map(q=>q.ID).join(','))+'">📝 Buat PO dari SEMUA permintaan ('+r.permintaan.length+')</button></div>':'')+r.permintaan.map(q=>'<div class="box"><b>'+esc(q.Nama)+': '+esc(q.Qty)+' '+esc(q.Satuan)+'</b><div class="mut">'+esc(q.Staff)+' • '+esc(q.Waktu)+(q.Catatan?' • '+esc(q.Catatan):'')+'</div><div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:6px"><button class="btn s" data-poall="'+esc(q.ID)+'">📝 Buat PO</button><button class="btn s k" data-q="'+esc(q.ID)+'">✔ Udah diurus sendiri</button></div></div>').join('')||'<div class="mut">Tidak ada permintaan baru.</div>';
document.getElementById('setuju').innerHTML=(r.disetujui||[]).map(b=>'<div class="box"><b>'+(b.jenis=='Masuk'?'📥 Barang Masuk':'🧮 Hitung Stok')+' — '+esc(b.staff)+'</b> <span class="mut">'+esc(b.waktu)+(b.ref?' • '+esc(b.ref):'')+'</span>'+b.items.map(i=>'<div>• '+esc(i.nama)+': <b>'+esc(i.qty)+' '+esc(i.satuan)+'</b></div>').join('')+'<div style="margin-top:6px">'+(b.sudah_real?'<span class="pill p-sudah">✅ Sudah jadi stok real • '+esc(b.sudah_real)+'</span>':'<button class="btn s k" data-jh="'+esc(b.batch)+'">🔁 Jadikan stok real</button>')+'</div></div>').join('')||'<div class="mut">Belum ada.</div>';
document.getElementById('permsel').innerHTML=(r.permintaan_selesai||[]).map(q=>'<div class="box"><b>'+esc(q.Nama)+': '+esc(q.Qty)+' '+esc(q.Satuan)+'</b> <span class="mut">'+esc(q.Staff)+' • '+esc(q.Waktu)+'</span><div style="margin-top:6px"><button class="btn s" data-poall="'+esc(q.ID)+'">📝 Buat PO</button></div></div>').join('')||'<div class="mut">Gak ada.</div>';
document.getElementById('ord').innerHTML=r.orders.map(o=>'<div>'+(o.dikirim?'✅':'⏳')+' '+esc(o.invoice)+' — '+esc(o.customer)+(o.dikirim?' (dikirim oleh '+esc(o.dikirim_oleh)+')':' (belum dikirim)')+'</div>').join('')||'Belum ada.'}
showTab((location.hash||'').slice(1)&&TABS.some(t=>t[0]==location.hash.slice(1))?location.hash.slice(1):'ringkasan');
loadLap();loadStok();loadPend();setInterval(()=>{loadLap();loadStok();loadPend()},120000);
</script></body></html>"""
