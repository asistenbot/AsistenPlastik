"""
Parsing chat/foto order customer (dan input PO ke supplier) jadi data
terstruktur, pakai Claude. Hasil parse-nya SELALU ditunjukin ke admin dulu
buat dikonfirmasi sebelum disimpen ke Sheets -- supaya kalau AI salah baca,
gampang dikoreksi (lihat handle_confirm / handle_pending_correction di
bot.py).
"""

import base64
import json
import re

import anthropic

import config

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


class AIResponseNotJSON(Exception):
    """Dilempar internal kalau Claude BENERAN gak balikin JSON sama sekali
    (misal dia nolak/nulis penjelasan biasa, bukan format yang diminta) --
    biasanya kejadian kalau yang dikasih (foto/teks) ternyata bukan hal yang
    diminta buat diparse (misal foto price list dikirim ke parser order).
    Ini BUKAN bug -- caller yang relevan nangkep ini dan kasih fallback yang
    aman, bukan nge-crash nunjukin exception mentah ke admin."""
    def __init__(self, raw_text):
        self.raw_text = raw_text
        super().__init__("Respons AI bukan JSON yang valid")


def _extract_json(text):
    """Claude kadang bungkus JSON dengan kalimat lain / code fence -- ambil
    blok {...} pertama yang valid. Kalau BENERAN gak ketemu JSON sama sekali,
    lempar AIResponseNotJSON (bawa teks mentahnya) daripada biarin
    JSONDecodeError mentah nyampe ke user."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        if brace:
            text = brace.group(0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        raise AIResponseNotJSON(text)


def _cuplikan(raw_text, maks=300):
    t = (raw_text or "").strip()
    return t[:maks] + "..." if len(t) > maks else t


def _empty_order_result(raw_text):
    """Fallback aman kalau Claude gak balikin JSON order sama sekali --
    biasanya karena yang dikasih BUKAN order customer (misal foto price
    list/dokumen lain, atau pesan yang gak jelas). items kosong bikin
    safety net di bot.py (_process_order_text/_process_order_photo) nolak
    bikin pending_order, dan kasih tau admin apa adanya -- bukan crash."""
    catatan = "AI gak bisa baca ini jadi data order. Kemungkinan ini bukan order customer."
    cuplikan = _cuplikan(raw_text)
    if cuplikan:
        catatan += f"\n\nJawaban AI: {cuplikan}"
    return {
        "nama_customer": "", "no_hp": "", "alamat": "", "metode": "Kirim",
        "items": [], "ongkir": 0, "no_po_customer": "", "tanggal_kirim": "",
        "catatan": catatan, "perlu_konfirmasi_manual": True,
    }


def _empty_price_update_result(raw_text):
    """Sama kayak _empty_order_result tapi buat jalur update harga -- items
    kosong bikin _present_price_update di bot.py kasih tau "Gak nemu
    perubahan harga..." apa adanya, bukan crash."""
    catatan = "AI gak bisa baca ini jadi update harga."
    cuplikan = _cuplikan(raw_text)
    if cuplikan:
        catatan += f"\n\nJawaban AI: {cuplikan}"
    return {"items": [], "nama_supplier": "", "catatan": catatan}


def _catalog_context(price_list):
    lines = []
    for row in price_list:
        lines.append(
            f"- {row.get('Item_Code')} | {row.get('Nama')} | {row.get('Deskripsi')} | "
            f"kategori {row.get('Kategori')} | satuan {row.get('Satuan')} | "
            f"harga jual Rp{row.get('Harga_Jual')}"
        )
    return "\n".join(lines)


ORDER_SYSTEM_PROMPT = """Kamu adalah asisten admin toko plastik "{business_name}".
Tugas kamu: baca chat/foto order dari customer (biasanya berantakan, bahasa
santai/nyingkat) dan ubah jadi data terstruktur JSON.

KATALOG PRODUK YANG VALID (HARUS dipakai buat cocokin item_code -- JANGAN
pernah mengarang item_code atau harga yang gak ada di katalog ini):
{catalog}

CUSTOMER YANG SUDAH PERNAH ORDER (buat bantu cocokin nama, boleh juga nama
baru kalau memang customer baru):
{customers}

Balikin HANYA JSON dengan struktur persis seperti ini, tanpa teks lain:
{{
  "nama_customer": "nama customer, judul huruf besar tiap kata",
  "no_hp": "nomor HP kalau disebut, kalau tidak ada string kosong",
  "alamat": "alamat kalau disebut, kalau tidak ada string kosong",
  "metode": "Kirim" atau "Ambil" (tebak dari konteks, default \"Kirim\" kalau gak jelas),
  "items": [
    {{"item_code": "KODE_DARI_KATALOG", "nama_item": "nama sesuai katalog", "qty": angka}}
  ],
  "ongkir": 0,
  "no_po_customer": "nomor PO/Purchase Order MILIK CUSTOMER kalau ada (misal kalau fotonya adalah dokumen resmi 'Purchase Order' dari customer dengan field 'Purchase Number'/'PO Number'/'No. PO', ambil nomornya persis), kalau gak ada string kosong",
  "tanggal_kirim": "tanggal customer MINTA dikirim/diambil kalau disebut eksplisit (dari teks admin, atau dari field 'Required Date'/'Due Date'/'Delivery Date' di dokumen PO customer kalau ada), format bebas tapi jelas (misal '20 September 2026'), kalau gak disebut string kosong",
  "catatan": "catatan buat admin kalau ada yang ambigu/gak yakin, kalau tidak ada string kosong",
  "perlu_konfirmasi_manual": false
}}

Aturan penting:
- qty HARUS angka (number), bukan string.
- Kalau ada item yang disebut tapi TIDAK ketemu di katalog / ambigu bisa lebih
  dari 1 kandidat, tetap masukin item itu dengan item_code kosong ("") dan
  nama_item = apa yang disebut customer, terus set perlu_konfirmasi_manual
  jadi true dan jelasin di "catatan".
- Ongkir default 0 kecuali disebutin jelas nominalnya.
- no_po_customer & tanggal_kirim itu OPSIONAL -- JANGAN mengarang, kosongin
  kalau memang gak disebut/gak keliatan di teks atau foto.
- Jangan hitung subtotal/total, itu dihitung sistem lain.
"""


def parse_order_text(text, price_list, customer_names):
    prompt = ORDER_SYSTEM_PROMPT.format(
        business_name=config.BUSINESS_NAME,
        catalog=_catalog_context(price_list),
        customers=", ".join(customer_names) if customer_names else "(belum ada)",
    )
    client = _get_client()
    resp = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=2000,
        system=prompt,
        messages=[{"role": "user", "content": f"Chat order dari customer:\n\n{text}"}],
    )
    raw = "".join(block.text for block in resp.content if block.type == "text")
    try:
        return _extract_json(raw)
    except AIResponseNotJSON as e:
        return _empty_order_result(e.raw_text)


def parse_order_image(image_bytes, media_type, price_list, customer_names):
    prompt = ORDER_SYSTEM_PROMPT.format(
        business_name=config.BUSINESS_NAME,
        catalog=_catalog_context(price_list),
        customers=", ".join(customer_names) if customer_names else "(belum ada)",
    )
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    client = _get_client()
    resp = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=2000,
        system=prompt,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": b64},
                },
                {
                    "type": "text",
                    "text": "Ini foto/screenshot order dari customer. Baca isinya dan ubah jadi JSON sesuai instruksi.",
                },
            ],
        }],
    )
    raw = "".join(block.text for block in resp.content if block.type == "text")
    try:
        return _extract_json(raw)
    except AIResponseNotJSON as e:
        return _empty_order_result(e.raw_text)


def _catalog_context_beli(price_list):
    """Katalog produk lengkap (item_code + histori harga beli), dipakai di
    prompt PO biar AI bisa: (1) cocokin item_code walau admin nulis
    singkatan/gak lengkap, dan (2) tau harga beli terakhir kalau harga gak
    disebut eksplisit di teks. Beda dari _catalog_context yang buat order
    customer (nampilin harga JUAL, bukan harga beli)."""
    lines = []
    for row in price_list or []:
        harga_beli = row.get("Harga_Beli")
        try:
            harga_num = float(harga_beli)
        except (TypeError, ValueError):
            harga_num = 0
        harga_text = f"Rp{harga_beli}" if harga_num > 0 else "belum ada histori (isi manual)"
        lines.append(
            f"- {row.get('Item_Code')} | {row.get('Nama')} | {row.get('Deskripsi')} | "
            f"kategori {row.get('Kategori')} | satuan {row.get('Satuan')} | "
            f"harga beli terakhir {harga_text}"
        )
    return "\n".join(lines) if lines else "(katalog masih kosong)"


PO_SYSTEM_PROMPT = """Kamu adalah asisten admin toko plastik "{business_name}"
yang lagi bikin Purchase Order (PO) BELANJA BAHAN ke supplier (bukan order
dari customer). Baca teks dari admin dan ubah jadi JSON.

SUPPLIER YANG SUDAH PERNAH DIPAKAI:
{suppliers}

KATALOG PRODUK (HARUS dipakai buat cocokin item_code, meski admin nulis
singkatan/gak lengkap -- misal "plastik sampah uk 90" itu cocok ke produk
kategori SAMPAH yang ada angka 90 di Nama/Deskripsi-nya):
{catalog}

Balikin HANYA JSON dengan struktur persis seperti ini, tanpa teks lain:
{{
  "nama_supplier": "nama supplier, judul huruf besar tiap kata",
  "items": [
    {{"item_code": "KODE_DARI_KATALOG, kosong string kalau BENERAN gak ketemu match apapun", "nama_item": "nama PERSIS sesuai katalog kalau item_code ketemu, atau apa yang ditulis admin kalau gak ketemu", "qty": angka, "satuan": "sesuai katalog kalau ketemu, atau tebakan kalau gak ketemu", "harga_satuan": angka harga beli per satuan}}
  ],
  "catatan": "catatan kalau ada yang ambigu / item_code kosong, kalau tidak ada string kosong"
}}

Aturan penting:
1. item_code & nama_item WAJIB dicocokin ke KATALOG di atas kalau memang ada
   yang cocok -- JANGAN nulis ulang/gabung sendiri nama & ukuran barang dari
   tebakan kamu (contoh SALAH: admin nyebut "uk 90" lalu qty "100kg"
   terpisah, JANGAN digabung jadi ukuran "90 x100" -- itu bukan dimensi
   gabungan, "100kg" itu qty). Kalau ragu antara qty vs bagian dari nama
   barang, PRIORITASKAN cocokin dulu ke katalog.
2. Kalau BENERAN gak ada yang cocok di katalog, item_code dikosongin ("")
   dan nama_item = persis apa yang ditulis admin, terus jelasin di catatan
   biar admin cek manual.
3. Aturan harga_satuan (urut prioritas):
   a. Kalau teks admin EKSPLISIT nyebut harga, PAKAI itu -- menang dibanding
      histori katalog.
   b. Kalau teks gak nyebut harga tapi item_code ketemu & katalog punya
      histori harga beli buat item itu, PAKAI harga beli terakhir itu.
   c. Kalau item_code gak ketemu ATAU katalog belum punya histori harga
      buat item itu, isi 0 dan jelasin di catatan supaya admin isi manual.

qty dan harga_satuan HARUS angka (number), bukan string.
"""


def parse_po_text(text, supplier_names, price_list=None):
    prompt = PO_SYSTEM_PROMPT.format(
        business_name=config.BUSINESS_NAME,
        suppliers=", ".join(supplier_names) if supplier_names else "(belum ada)",
        catalog=_catalog_context_beli(price_list),
    )
    client = _get_client()
    resp = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=1500,
        system=prompt,
        messages=[{"role": "user", "content": text}],
    )
    raw = "".join(block.text for block in resp.content if block.type == "text")
    return _extract_json(raw)


PO_PRICE_FILL_SYSTEM_PROMPT = """Kamu adalah asisten admin toko plastik "{business_name}".
Ada PO (belanja ke supplier) yang lagi nunggu konfirmasi, tapi ada item yang
harga beli-nya masih Rp0 (belum sempat diisi). Admin baru aja ngirim pesan
susulan buat ngasih tau harganya -- baca pesan itu dan cocokin ke item yang
harganya masih 0.

ITEM DI PO INI (index dimulai dari 0, INDEX INI YANG DIPAKAI DI OUTPUT):
{items}

Balikin HANYA JSON persis struktur ini, tanpa teks lain:
{{
  "updates": [
    {{"index": angka index item di atas, "harga_satuan": angka harga baru}}
  ]
}}

Aturan:
- Kalau pesan admin JELAS ngasih satu angka harga (misal "harga 18870",
  "18870 aja", "harganya 18.870"), dan cuma ADA SATU item yang harganya
  masih 0, pasangkan harga itu ke item tsb.
- Kalau ada BEBERAPA item yang harganya masih 0 dan pesan nyebut beberapa
  angka / nama barang, cocokin sebaik mungkin berdasarkan nama barang yang
  disebut di pesan.
- Kalau pesan SAMA SEKALI gak nyebut angka harga, atau gak nyambung sama
  isi PO ini (misal itu obrolan lain), balikin "updates": [] (array kosong)
  -- JANGAN maksa nebak.
"""


def parse_po_price_fill(text, items):
    items_text = "\n".join(
        f"{i}. {it.get('nama_item')} x{it.get('qty')} {it.get('satuan', '')} "
        f"(harga sekarang: Rp{it.get('harga_satuan', 0)})"
        for i, it in enumerate(items)
    )
    prompt = PO_PRICE_FILL_SYSTEM_PROMPT.format(
        business_name=config.BUSINESS_NAME,
        items=items_text or "(kosong)",
    )
    client = _get_client()
    resp = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=500,
        system=prompt,
        messages=[{"role": "user", "content": text}],
    )
    raw = "".join(block.text for block in resp.content if block.type == "text")
    try:
        return _extract_json(raw)
    except AIResponseNotJSON:
        return {"updates": []}


INTENT_SYSTEM_PROMPT = """Kamu router pesan buat bot admin toko plastik
"{business_name}". Setiap pesan teks bebas yang diketik admin (BUKAN
command yang diawali "/") harus kamu klasifikasikan mau ngapain, supaya
admin gak perlu apal command kaku -- boleh nanya sesantai apapun.

Balikin HANYA JSON persis struktur ini, tanpa teks lain:
{{
  "intent": salah satu dari daftar di bawah,
  "target": "nama customer/supplier atau nomor invoice yang disebut, string kosong kalau gak ada",
  "bulan": "format YYYY-MM kalau ada bulan/tahun disebut (mis. 'bulan lalu', 'Juli 2026'), string kosong kalau gak disebut -> berarti bulan berjalan",
  "jumlah": angka nominal uang yang disebut (buat bayar utang), 0 kalau gak ada
}}

Daftar intent yang valid:
- "order" -- ini order/pesanan dari CUSTOMER (beli barang dari kita)
- "po" -- ini niat BELANJA/PO ke SUPPLIER SEKARANG (kita yang mau beli bahan,
  nyebut barang + QTY yang mau dibeli), biasanya ada kata "PO", "belanja ke",
  "order ke supplier", "stok dari <nama supplier> <qty barang>". Kalau CUMA
  ngasih tau/masukin daftar harga dari supplier TANPA qty barang yang mau
  dibeli, itu bukan "po" -- itu "update_harga" (lihat di bawah).
- "report_piutang" -- nanya piutang / tagihan customer yang belum dibayar
- "report_utang" -- nanya utang ke supplier yang belum dibayar
- "report_kas_bulanan" -- nanya laporan kas / laba rugi / untung rugi bulanan
- "report_pricelist" -- nanya daftar harga produk
- "mark_lunas" -- bilang customer tertentu udah bayar / lunas
- "bayar_utang" -- bilang udah bayar/cicil ke supplier tertentu
- "lihat_invoice" -- minta liat/cetak ulang invoice customer tertentu
- "lihat_suratjalan" -- minta liat/cetak ulang surat jalan customer tertentu
- "edit_order" -- admin mau NGOREKSI/BETULIN data order/invoice yang SUDAH
  kesimpen (misal salah ketik nama customer, salah alamat, salah no HP),
  BUKAN bikin order baru. Ciri-cirinya: diawali kata "edit", "ganti",
  "betulin", "koreksi", "salah tadi", dsb, dan TIDAK nyebutin barang/qty
  yang dibeli sama sekali. Kalau pesannya cuma nyebut 1-2 kata nama orang
  atau tempat tanpa daftar barang (misal cuma "edit Grandia Hotel"), itu
  edit_order, BUKAN order.
- "batal_order" -- admin mau BATALIN/HAPUS SELURUH order/invoice CUSTOMER
  yang SUDAH kesimpen (misal order test yang mau dibuang, atau customer
  batal jadi beli), BUKAN betulin satu-dua data yang salah ketik (itu
  edit_order), dan BUKAN batalin PO ke supplier (itu "batal_po" di bawah).
  Ciri-cirinya: kata "hapus", "batalin", "cancel", "gak jadi", diikuti
  referensi ke order/invoice/customer tertentu (BUKAN kata "PO" atau nama
  supplier), TANPA nyebut field spesifik apa yang mau diganti isinya.
- "batal_po" -- admin mau BATALIN/HAPUS PO (belanja ke SUPPLIER) yang SUDAH
  kesimpen. Ciri-cirinya: kata "hapus", "batalin", "cancel", "gak jadi"
  diikuti kata "PO" secara eksplisit dan/atau nama SUPPLIER (bukan
  customer). Contoh: "hapus PO CSB", "batalin PO ke CSB", "PO nya gak jadi",
  "cancel PO-20260830-001".
- "update_harga" -- admin mau UBAH HARGA JUAL dan/atau HARGA BELI produk di
  katalog/PriceList (bukan order dari customer, bukan PO/belanja ke
  supplier). Ciri-cirinya: nyebut nama/kode barang + harga/angka rupiah,
  pakai kata kayak "harga", "naikin", "turunin", "sekarang", "ganti harga",
  "update harga", "masukin harga/price list", dan TIDAK nyebut QTY barang
  yang lagi mau DIBELI/dipesan sekarang. PENTING: nyebut nama SUPPLIER itu
  BOLEH dan TETEP update_harga selama cuma sebagai SUMBER/ASAL data harga
  (misal "harga dari supplier X, tolong masukin", "update harga beli dari
  price list Y", foto daftar harga dengan caption nyebut nama tokonya) --
  yang bikin ini JADI "po" adalah kalau ada QTY barang yang mau dibeli
  sekarang (lihat penjelasan "po" di atas). Contoh update_harga: "harga
  tulip naik jadi 17000", "PP bening 40x60 sekarang 30rb", "update harga
  TUL-01 jadi 16500", "harga dari supplier CSB 087853077492, tolong
  masukin, harga beli yg di kolom include", foto price list dengan caption
  "daftar harga supplier baru, masukin ya".
- "lainnya" -- basa-basi / gak jelas maksudnya / gak masuk kategori manapun

Kalau ragu antara "order" dan intent lain, PILIH "order" (lebih aman salah
nanya balik daripada order customer keskip) -- KECUALI kalau pesannya
diawali kata edit/ganti/betulin/koreksi dan gak nyebut barang (itu
edit_order), diawali hapus/batalin/cancel yang nyebut "PO" atau nama
supplier (itu batal_po), diawali hapus/batalin/cancel tanpa nyebut "PO"/
supplier dan tanpa nyebut field spesifik (itu batal_order), atau nyebut
barang/daftar harga + kata "masukin"/"update"/"harga" TANPA qty barang
yang mau dibeli sekarang (itu update_harga, WALAUPUN ada nama supplier
disebut sebagai sumber datanya).
Kalau pesan cuma sapaan atau gak jelas sama sekali, pilih "lainnya".
"""


def classify_intent(text):
    prompt = INTENT_SYSTEM_PROMPT.format(business_name=config.BUSINESS_NAME)
    client = _get_client()
    resp = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=300,
        system=prompt,
        messages=[{"role": "user", "content": text}],
    )
    raw = "".join(block.text for block in resp.content if block.type == "text")
    return _extract_json(raw)


EDIT_ORDER_SYSTEM_PROMPT = """Kamu asisten admin toko plastik "{business_name}".
Admin barusan mau NGOREKSI/BETULIN salah satu data di order yang SUDAH
kesimpen (bukan bikin order baru, bukan batalin/hapus order -- kalau
instruksinya "hapus"/"batalin"/"cancel" TANPA nyebut field yang mau
diganti, itu BUKAN urusan kamu, biarin semua field kosong). Data order
yang mau dikoreksi saat ini:

{current}

Baca instruksi koreksi dari admin, terus balikin HANYA JSON persis struktur
ini, tanpa teks lain:
{{
  "nama_customer": "nilai baru kalau nama customer mau diganti, string kosong kalau TIDAK diganti",
  "no_hp": "nilai baru kalau no HP mau diganti, string kosong kalau TIDAK diganti",
  "alamat": "nilai baru kalau alamat mau diganti, string kosong kalau TIDAK diganti",
  "metode": "'Kirim' atau 'Ambil' kalau metode mau diganti, string kosong kalau TIDAK diganti",
  "no_po_customer": "nilai baru kalau No. PO Customer mau diganti/ditambahin, string kosong kalau TIDAK diganti",
  "tanggal_kirim": "nilai baru kalau tanggal kirim mau diganti/ditambahin, string kosong kalau TIDAK diganti",
  "items": [
    {{
      "item_code": "kode item (dari daftar ITEM DI ORDER INI di atas) yang mau diganti",
      "qty_baru": angka qty baru, 0 kalau qty item ini TIDAK diganti,
      "harga_satuan_baru": angka harga satuan BARU khusus buat order ini aja, 0 kalau TIDAK diganti
    }}
  ]
}}

Aturan penting:
- Kalau instruksinya cuma nyebut satu-dua kata nama/tempat tanpa penjelasan
  lain (misal admin cuma ngetik "edit Grandia Hotel"), itu HAMPIR PASTI
  maksudnya mau ganti NAMA CUSTOMER jadi nama itu -- bukan field lain.
- JANGAN mengarang perubahan buat field yang gak disebut sama sekali,
  biarin string kosong / array kosong.
- KHUSUS nama_customer: kalau nilai baru yang dimaksud admin SAMA PERSIS
  (case-insensitive) dengan nama customer yang udah kesimpen sekarang,
  berarti gak ada yang perlu diubah -- biarin nama_customer string kosong,
  JANGAN balikin nilai yang sama sebagai "perubahan".
- "items" cuma diisi kalau admin EKSPLISIT minta ganti QTY dan/atau HARGA
  SATUAN salah satu barang yang UDAH ada di order ini (misal "qty jadi
  25kg", "yang tulip jadi 10 pack aja", "harganya jadi 18000",
  "plastik sampah harganya di update jadi 16000"). Kalau order cuma punya
  1 macam barang dan admin nyebut qty/harga baru tanpa nama barang, itu
  barang itu yang dimaksud. JANGAN nambah barang baru atau hapus barang
  yang gak disebut. "harga_satuan_baru" di sini CUMA ngubah harga di order
  INI SAJA (buat invoice-nya), BUKAN ngubah harga jual permanen di
  katalog/PriceList (itu urusan lain, di luar tugas kamu).
- PENTING: kalau admin nyebut "harganya di update" / "harganya berubah"
  TAPI GAK NYEBUT ANGKA BARUNYA SAMA SEKALI, JANGAN NEBAK angkanya --
  biarin harga_satuan_baru 0 (gak diganti) buat item itu, biar admin
  diminta nyebutin angkanya secara eksplisit.
"""


def parse_order_correction(instruction_text, current_order_desc):
    prompt = EDIT_ORDER_SYSTEM_PROMPT.format(
        business_name=config.BUSINESS_NAME,
        current=current_order_desc,
    )
    client = _get_client()
    resp = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=300,
        system=prompt,
        messages=[{"role": "user", "content": instruction_text}],
    )
    raw = "".join(block.text for block in resp.content if block.type == "text")
    return _extract_json(raw)


PENDING_ORDER_CORRECTION_SYSTEM_PROMPT = """Kamu asisten admin toko plastik "{business_name}".
Ada ORDER BARU yang lagi di-PREVIEW (BELUM disimpan/dikonfirmasi -- masih
bebas dikoreksi sebelum admin pencet tombol Simpan). Admin barusan ngirim
pesan susulan yang KEMUNGKINAN adalah koreksi ke preview ini.

PREVIEW ORDER SAAT INI:
{current}

Baca pesan admin, balikin HANYA JSON persis struktur ini, tanpa teks lain:
{{
  "header_updates": {{
    "nama_customer": "nilai baru kalau nama customer mau diganti, string kosong kalau TIDAK diganti",
    "no_hp": "nilai baru kalau no HP mau diganti, string kosong kalau TIDAK diganti",
    "alamat": "nilai baru kalau alamat mau diganti, string kosong kalau TIDAK diganti",
    "metode": "'Kirim' atau 'Ambil' kalau metode mau diganti, string kosong kalau TIDAK diganti",
    "no_po_customer": "nilai baru kalau No. PO Customer mau diganti/ditambahin, string kosong kalau TIDAK diganti",
    "tanggal_kirim": "nilai baru kalau tanggal kirim mau diganti/ditentuin, string kosong kalau TIDAK diganti",
    "ongkir": angka ongkir baru kalau mau diganti, -1 kalau TIDAK diganti
  }},
  "item_updates": [
    {{"index": angka index item di ITEM DI ORDER INI di atas (0-based, urut dari atas), "qty": angka qty baru atau null kalau TIDAK diganti, "harga_satuan": angka harga satuan baru atau null kalau TIDAK diganti}}
  ],
  "matched": true kalau ADA SESUATU yang match jadi koreksi (header atau item), false kalau pesan ini SAMA SEKALI gak nyambung ke koreksi preview order ini
}}

Aturan penting:
- JANGAN mengarang perubahan buat field yang gak disebut -- biarin default
  (string kosong / -1 / null).
- item_updates cuma diisi kalau admin EKSPLISIT nyebut mau ganti qty
  dan/atau harga SALAH SATU item yang UDAH ada di preview ini. Kalau cuma
  ada 1 item di preview dan admin nyebut qty/harga baru tanpa nama barang,
  itu item itu yang dimaksud (index 0).
- Kalau pesan ini sebenernya mau NAMBAH barang baru (bukan koreksi item
  yang udah ada), atau sama sekali gak nyambung ke koreksi apapun (basa-
  basi/obrolan lain), set matched=false dan biarin semua field default --
  JANGAN maksa nebak.
- Kalau admin nyebut "harganya di update"/"harganya berubah" TAPI GAK
  NYEBUT ANGKA BARUNYA SAMA SEKALI, JANGAN NEBAK -- biarin harga_satuan
  item itu null.
"""


def parse_pending_order_correction(text, current_order_desc):
    prompt = PENDING_ORDER_CORRECTION_SYSTEM_PROMPT.format(
        business_name=config.BUSINESS_NAME,
        current=current_order_desc,
    )
    client = _get_client()
    resp = client.messages.create(
        model=config.CLAUDE_MODEL,
        max_tokens=400,
        system=prompt,
        messages=[{"role": "user", "content": text}],
    )
    raw = "".join(block.text for block in resp.content if block.type == "text")
    try:
        return _extract_json(raw)
    except AIResponseNotJSON:
        return {"header_updates": {}, "item_updates": [], "matched": False}


PRICE_UPDATE_SYSTEM_PROMPT = """Kamu asisten admin toko plastik "{business_name}".
Admin mau UPDATE HARGA JUAL dan/atau HARGA BELI satu atau beberapa produk di
katalog (PriceList) -- BUKAN order dari customer, BUKAN PO ke supplier.

KATALOG PRODUK SAAT INI:
{catalog}

KATEGORI YANG VALID: {kategori_valid}
SATUAN YANG VALID: {satuan_valid}

Baca instruksi dari admin, balikin HANYA JSON persis struktur ini, tanpa
teks lain:
{{
  "nama_supplier": "nama supplier kalau disebut sebagai SUMBER harga ini (misal 'harga dari supplier X'), string kosong kalau gak disebut",
  "items": [
    {{
      "item_code": "KODE_DARI_KATALOG kalau ketemu jelas, string kosong kalau item gak ketemu/ambigu",
      "nama_disebut": "nama barang persis seperti disebut admin",
      "harga_jual": angka harga jual BARU, 0 kalau harga jual TIDAK disebut/diubah,
      "harga_beli": angka harga beli BARU, 0 kalau harga beli TIDAK disebut/diubah,
      "item_code_baru": "USULAN kode singkat buat produk ini KALAU item_code di atas kosong (barang belum ada di katalog) -- huruf besar, alfanumerik tanpa spasi, max 10 karakter, JANGAN sama dengan kode yang udah ada di katalog. Kosongkan kalau item_code di atas SUDAH terisi.",
      "kategori_baru": "kategori dari daftar KATEGORI YANG VALID di atas yang paling cocok, HANYA diisi kalau item_code_baru diisi",
      "satuan_baru": "satuan dari daftar SATUAN YANG VALID di atas yang paling cocok, HANYA diisi kalau item_code_baru diisi"
    }}
  ]
}}

Aturan:
- Kalau admin cuma nyebut satu angka harga tanpa bilang itu harga
  beli/modal/dari supplier, anggap itu HARGA JUAL (harga ke customer).
- Boleh lebih dari 1 item dalam 1 pesan (misal admin bilang "tulip sama
  sampah naik semua 2000").
- Kalau nama barang yang disebut gak ketemu jelas di katalog (atau
  ambigu, bisa lebih dari 1 kandidat), tetap masukin ke items dengan
  item_code kosong ("") biar admin dikasih tau gak ketemu -- jangan
  mengarang item_code yang dipaksa cocok ke katalog. Tapi TETEP isi
  item_code_baru/kategori_baru/satuan_baru buat item itu (usulan produk
  BARU), supaya admin bisa milih nambahin ke katalog kalau mau -- JANGAN
  kosongkan ketiganya kecuali bener-bener gak ada cukup info (misal harga
  doang tanpa nama jelas sama sekali).
"""


def parse_price_update(text, price_list):
    prompt = PRICE_UPDATE_SYSTEM_PROMPT.format(
        business_name=config.BUSINESS_NAME,
        catalog=_catalog_context(price_list),
        kategori_valid=", ".join(config.CATEGORIES),
        satuan_valid=", ".join(config.UNITS),
    )
    client = _get_client()
    resp = client.messages.create(
        model=config.CLAUDE_MODEL,
        # Cukup gede biar gak kepotong pas admin nyebut BANYAK barang
        # sekaligus di 1 pesan (tiap item sekarang bisa punya sampe 7
        # field kalau ada usulan barang baru).
        max_tokens=3000,
        system=prompt,
        messages=[{"role": "user", "content": text}],
    )
    raw = "".join(block.text for block in resp.content if block.type == "text")
    try:
        return _extract_json(raw)
    except AIResponseNotJSON as e:
        return _empty_price_update_result(e.raw_text)


PRICE_UPDATE_IMAGE_SYSTEM_PROMPT = """Kamu asisten admin toko plastik "{business_name}".
Admin barusan kirim FOTO daftar harga dari SUPPLIER (bukan order dari
customer, bukan daftar harga jual kita sendiri). Tugas kamu: baca foto ini
baris per baris, cocokin tiap barang ke katalog produk kita, terus tentuin
HARGA BELI (harga modal, dari supplier ke kita) yang baru buat tiap barang.
Kalau di foto ada nama perusahaan/toko supplier-nya (biasanya di bagian
atas/kop surat foto), catat juga nama itu -- CAPTION dari admin (kalau ada,
lihat di bawah) JUGA bisa nyebut nama supplier-nya, itu sumber yang SAMA
validnya kayak yang keliatan di foto.

KATALOG PRODUK KITA SAAT INI:
{catalog}

KATEGORI YANG VALID: {kategori_valid}
SATUAN YANG VALID: {satuan_valid}
{caption_context}
Balikin HANYA JSON persis struktur ini, tanpa teks lain:
{{
  "nama_supplier": "nama supplier -- dari kop/header foto ATAU dari caption admin kalau disebut di situ, string kosong kalau beneran gak disebut di manapun",
  "items": [
    {{
      "item_code": "KODE_DARI_KATALOG kalau ketemu jelas, string kosong kalau item gak ketemu/ambigu",
      "nama_disebut": "nama barang persis seperti tertulis di foto",
      "harga_jual": 0,
      "harga_beli": angka harga beli/modal yang tertulis di foto buat barang ini,
      "item_code_baru": "USULAN kode singkat buat produk ini KALAU item_code di atas kosong (barang belum ada di katalog) -- huruf besar, alfanumerik tanpa spasi, max 10 karakter, JANGAN sama dengan kode yang udah ada di katalog. Kosongkan kalau item_code di atas SUDAH terisi.",
      "kategori_baru": "kategori dari daftar KATEGORI YANG VALID di atas yang paling cocok, HANYA diisi kalau item_code_baru diisi",
      "satuan_baru": "satuan dari daftar SATUAN YANG VALID di atas yang paling cocok, HANYA diisi kalau item_code_baru diisi"
    }}
  ]
}}

Aturan:
- Harga yang tertulis di foto daftar harga supplier ini SELALU dianggap
  HARGA BELI (harga_beli) -- harga_jual SELALU 0 di sini, JANGAN diisi,
  itu urusan admin nentuin sendiri nanti.
- Baca SEMUA baris/item yang kebaca di foto, jangan cuma yang pertama.
- Cocokin tiap baris ke item_code yang paling sesuai di katalog kita
  (berdasarkan nama/ukuran/kategori). Kalau ada barang di foto yang gak
  ketemu jelas di katalog kita (atau ambigu), tetap masukin ke items
  dengan item_code kosong ("") biar admin dikasih tau -- jangan mengarang
  item_code yang dipaksa cocok ke katalog. Tapi TETEP isi
  item_code_baru/kategori_baru/satuan_baru buat item itu (usulan produk
  BARU), supaya admin bisa milih nambahin ke katalog kalau mau -- JANGAN
  kosongkan ketiganya kecuali bener-bener gak ada cukup info.
- JANGAN mengarang nama_supplier kalau emang gak keliatan jelas di foto
  MAUPUN di caption, biarin string kosong.
"""


def parse_price_update_image(image_bytes, media_type, price_list, caption=""):
    caption = (caption or "").strip()
    caption_context = (
        f'\nCAPTION dari admin buat foto ini: "{caption}"\n' if caption
        else "\n(Admin gak kasih caption buat foto ini.)\n"
    )
    prompt = PRICE_UPDATE_IMAGE_SYSTEM_PROMPT.format(
        business_name=config.BUSINESS_NAME,
        catalog=_catalog_context(price_list),
        kategori_valid=", ".join(config.CATEGORIES),
        satuan_valid=", ".join(config.UNITS),
        caption_context=caption_context,
    )
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    client = _get_client()
    user_text = "Ini foto daftar harga dari supplier. Baca isinya dan ubah jadi JSON sesuai instruksi."
    if caption:
        user_text += f' Caption yang dikasih admin: "{caption}"'
    resp = client.messages.create(
        model=config.CLAUDE_MODEL,
        # Foto daftar harga supplier sering isinya 15-20+ baris, dan tiap
        # item sekarang bisa punya sampe 7 field (kalau ada usulan barang
        # baru) -- 1500 kepotong di tengah JSON buat tabel gede, bikin
        # respons AI gak valid dan semuanya keanggep "gak ketemu apa-apa"
        # (kejadian nyata 2026-08-29, tabel 17 baris). 4096 kasih ruang aman.
        max_tokens=4096,
        system=prompt,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": b64},
                },
                {
                    "type": "text",
                    "text": user_text,
                },
            ],
        }],
    )
    raw = "".join(block.text for block in resp.content if block.type == "text")
    try:
        return _extract_json(raw)
    except AIResponseNotJSON as e:
        return _empty_price_update_result(e.raw_text)
