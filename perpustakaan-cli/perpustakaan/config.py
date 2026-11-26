"""Konstanta yang dipakai bersama oleh seluruh module."""

LAMA_PINJAM_HARI = 7
DENDA_PER_HARI = 1000

# Urutan kolom pada file input (CSV maupun JSON).
KOLOM_INPUT = (
    "id_pinjam",
    "id_anggota",
    "nama_anggota",
    "kode_buku",
    "judul_buku",
    "kategori",
    "tanggal_pinjam",
    "tanggal_kembali",
)

# Kolom yang tidak boleh kosong. tanggal_kembali kosong = belum dikembalikan.
KOLOM_WAJIB = tuple(k for k in KOLOM_INPUT if k != "tanggal_kembali")

# Kolom tambahan hasil transformasi.
KOLOM_HASIL = KOLOM_INPUT + (
    "jatuh_tempo",
    "status",
    "hari_terlambat",
    "denda",
)

KOLOM_DITOLAK = ("baris",) + KOLOM_INPUT + ("alasan",)

# Awalan ID yang sah, misalnya P001, A001, B001.
AWALAN_ID = {"id_pinjam": "P", "id_anggota": "A", "kode_buku": "B"}

STATUS_VALID = (
    "dipinjam",
    "terlambat",
    "kembali_tepat",
    "kembali_terlambat",
)
