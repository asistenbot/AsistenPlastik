"""Data import: kantong sampah HD hitam merk Tulip (khusus Grandia)."""

_UKURAN = [
    ("40X60X0.035", 19980), ("50X70X0.035", 19980), ("50X75X0.035", 19980), ("60X80X0.035", 19980),
    ("60X100X0.035", 19980), ("60X100X0.050", 19980), ("80X100X0.035", 19980), ("80X100X0.060", 19980),
    ("80X120X0.040", 19980), ("80X120X0.060", 19980), ("90X100X0.030", 19980), ("90X120X0.040", 19980),
    ("90X120X0.060", 19980), ("100X120X0.040", 19980), ("100X120X0.060", 19980),
    ("100X150X0.040", 19980), ("100X150X0.060", 19980), ("120X180X0.050", 20535),
]

PRODUK_GRANDIA = [
    {
        "item_code": "HDT-" + "X".join(u.split("X")[:2]) + "-" + u.split("X")[2][2:],
        "nama": "HD Kantong Sampah Hitam Tulip " + u.replace("X", "x"),
        "deskripsi": "POLOS", "kategori": "SAMPAH", "satuan": "Pak",
        "harga_jual": 23000, "harga_beli": beli, "khusus": "Grandia", "supplier": "Cave Sumber Berkat", "isi_bal": 25,
    }
    for u, beli in _UKURAN
]
