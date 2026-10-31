"""Cetak surat jalan ke printer thermal 58mm Bluetooth langsung dari browser
(Chrome Android, Web Bluetooth + perintah ESC/POS). Tanpa app RawBT."""

import datetime
import textwrap
import unicodedata

import config

LEBAR = 32  # 58mm, font A = 32 karakter per baris


def _ascii(s):
    s = str(s or "").replace("×", "x").replace("–", "-").replace("—", "-")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return " ".join(s.split())


def _qty(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _ascii(v)
    return str(int(f)) if f == int(f) else f"{f:g}".replace(".", ",")


def _tgl(ts):
    try:
        d = datetime.datetime.strptime(str(ts)[:10], "%Y-%m-%d")
        return d.strftime("%d-%m-%Y")
    except ValueError:
        return _ascii(ts)


def _baris(teks, lebar=LEBAR, indent=""):
    t = unicodedata.normalize("NFKD", str(teks or "").replace("×", "x")).encode("ascii", "ignore").decode()
    return textwrap.wrap(t.replace("\n", " "), lebar, subsequent_indent=indent) or [""]


def struk_surat_jalan(sheets, no_invoice):
    """List segmen {t, al(l/c/r), b(bold), h(dobel tinggi)} atau None."""
    rows = sheets.get_order_items(no_invoice)
    if not rows:
        return None
    f = rows[0]
    no_sj = no_invoice.replace(config.INVOICE_PREFIX, config.SURAT_JALAN_PREFIX, 1)
    seg = []

    def add(t, al="l", b=False, h=False):
        seg.append({"t": t, "al": al, "b": b, "h": h})

    garis = "-" * LEBAR
    for ln in _baris(config.BUSINESS_NAME.upper()):
        add(ln, "c", True)
    add("SURAT JALAN", "c", True, True)
    add(garis)
    add(f"No   : {no_sj}")
    add(f"Tgl  : {_tgl(f.get('Timestamp', ''))}")
    add(f"Inv  : {no_invoice}")
    if str(f.get("No_PO_Customer", "")).strip():
        for ln in _baris(f"PO   : {f.get('No_PO_Customer')}", indent="       "):
            add(ln)
    if str(f.get("Tanggal_Kirim", "")).strip():
        add(f"Kirim: {_tgl(f.get('Tanggal_Kirim'))}")
    add(garis)
    add("Kepada:", b=True)
    for ln in _baris(f.get("Nama_Customer", "")):
        add(ln, b=True)
    if str(f.get("No_HP", "")).strip():
        add(f"HP: {_ascii(f.get('No_HP'))}")
    if str(f.get("Alamat", "")).strip():
        for ln in _baris(f.get("Alamat")):
            add(ln)
    add(garis)
    for i, r in enumerate(rows, start=1):
        for ln in _baris(f"{i}. {r.get('Nama_Item', '')}", indent="   "):
            add(ln)
        q = f"{_qty(r.get('Qty'))} {_ascii(r.get('Satuan', ''))}  [ ]"
        add(q.rjust(LEBAR), b=True)
    add(garis)
    add(f"Jumlah: {len(rows)} macam barang")
    add("")
    add("  Penerima          Pengirim")
    add("")
    add("")
    add("(..........)    (..........)")
    add("")
    add("Barang sudah diterima dalam", "c")
    add("keadaan baik & lengkap.", "c")
    return seg


THERMAL_JS = r"""
(function(){
const SVC=['000018f0-0000-1000-8000-00805f9b34fb','0000ff00-0000-1000-8000-00805f9b34fb','0000ffe0-0000-1000-8000-00805f9b34fb',
'0000fee7-0000-1000-8000-00805f9b34fb','0000ae30-0000-1000-8000-00805f9b34fb','0000ae3a-0000-1000-8000-00805f9b34fb',
'49535343-fe7d-4ae5-8fa9-9fafd205e455','e7810a71-73ae-499d-8c15-faa9aef0c3f2','0000ff80-0000-1000-8000-00805f9b34fb',
'0000fff0-0000-1000-8000-00805f9b34fb','0000ffb0-0000-1000-8000-00805f9b34fb'];
let CH=null,DEV=null;
function enc(seg){const out=[0x1b,0x40,0x1b,0x74,0x00];const AL={l:0,c:1,r:2};
for(const s of seg){out.push(0x1b,0x61,AL[s.al]||0,0x1b,0x45,s.b?1:0,0x1d,0x21,s.h?0x01:0x00);
for(const ch of String(s.t||'')){const c=ch.charCodeAt(0);out.push(c<128?c:63)}out.push(0x0a)}
out.push(0x1b,0x61,0,0x1b,0x45,0,0x1d,0x21,0,0x1b,0x64,4);return new Uint8Array(out)}
async function connect(){if(!navigator.bluetooth)throw new Error('NOBT');
if(CH&&DEV&&DEV.gatt.connected)return CH;
if(!DEV){DEV=await navigator.bluetooth.requestDevice({acceptAllDevices:true,optionalServices:SVC});DEV.addEventListener('gattserverdisconnected',()=>{CH=null})}
const srv=await DEV.gatt.connect();let svcs=[];try{svcs=await srv.getPrimaryServices()}catch(e){}
for(const s of svcs){let cs=[];try{cs=await s.getCharacteristics()}catch(e){continue}
for(const c of cs){if(c.properties.write||c.properties.writeWithoutResponse){CH=c;return CH}}}
throw new Error('NOCHAR')}
async function kirim(bytes){const c=await connect();const wr=c.properties.write;const N=20;/* 20 byte = aman buat semua printer BLE murah */
for(let i=0;i<bytes.length;i+=N){const part=bytes.slice(i,i+N);
if(wr&&c.writeValueWithResponse)await c.writeValueWithResponse(part);else if(c.writeValueWithoutResponse){await c.writeValueWithoutResponse(part);await new Promise(r=>setTimeout(r,12))}else await c.writeValue(part)}}
function msg(e){const m=String(e&&e.message||e);
if(m=='NOBT')return 'Browser ini belum bisa Bluetooth.\n\nPakai Google Chrome di HP/tablet Android (iPad/iPhone: pakai browser Bluefy).';
if(m=='NOCHAR')return 'Printer ketemu tapi gak bisa dikirimi data lewat Bluetooth browser. Kemungkinan printer ini cuma Bluetooth biasa (bukan BLE).';
if(/cancel/i.test(m)||e&&e.name=='NotFoundError')return '';
return 'Gagal print: '+m+'\n\nCek: printer nyala, kertas ada, gak lagi nyambung ke HP/app lain. Coba lagi.'}
window.cetakThermal=async function(url,btn){const old=btn?btn.textContent:'';try{if(btn){btn.disabled=true;btn.textContent='Nyambung...'}
if(!navigator.bluetooth)throw new Error('NOBT');
const r=await fetch(url,{credentials:'same-origin'});const j=await r.json();if(!j.ok)throw new Error(j.error||'Data gak ketemu');
if(btn)btn.textContent='Nge-print...';await kirim(enc(j.seg));if(btn)btn.textContent='✅ Terkirim';setTimeout(()=>{if(btn){btn.textContent=old;btn.disabled=false}},1500)}
catch(e){DEV&&!DEV.gatt.connected&&(CH=null);const m=msg(e);if(m)alert(m);if(btn){btn.textContent=old;btn.disabled=false}}};
window.gantiPrinterThermal=function(){try{DEV&&DEV.gatt.connected&&DEV.gatt.disconnect()}catch(e){}DEV=null;CH=null;alert('Oke, print berikutnya bakal minta pilih printer lagi.')};
window._thermalEnc=enc;
})();
"""


def add_thermal_routes(app):
    from aiohttp import web

    async def js(request):
        return web.Response(text=THERMAL_JS, content_type="application/javascript", charset="utf-8",
                            headers={"Cache-Control": "no-cache"})

    app.router.add_get("/thermal.js", js)
