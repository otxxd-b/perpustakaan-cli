"""Validasi dan normalisasi data (defensive programming)."""
import re
from datetime import date, datetime

from .config import AWALAN_ID, KOLOM_INPUT, KOLOM_WAJIB
from .errors import ValidasiError

POLA_TANGGAL = re.compile(r"\d{4}-\d{2}-\d{2}", re.ASCII)


def parse_tanggal(teks):
    """Mengubah teks YYYY-MM-DD menjadi objek date.

    Parameter:
        teks (str): tanggal dalam format YYYY-MM-DD.
    Return:
        datetime.date
    Raise:
        ValidasiError: format salah, tanggal tidak ada, atau tahun tidak wajar.
    """
    if not isinstance(teks, str) or not POLA_TANGGAL.fullmatch(teks):
        raise ValidasiError(f"format tanggal '{teks}' harus YYYY-MM-DD")
    try:
        hasil = datetime.strptime(teks, "%Y-%m-%d").date()
    except ValueError as err:
        raise ValidasiError(f"tanggal '{teks}' tidak ada di kalender") from err
    if not date(2000, 1, 1) <= hasil <= date(2100, 12, 31):
        raise ValidasiError(f"tanggal '{teks}' di luar rentang 2000-2100")
    return hasil


def bersihkan_baris(data):
    """Merapikan spasi dan huruf besar/kecil pada satu baris.

    Parameter:
        data (dict): baris mentah dari CSV/JSON.
    Return:
        dict: baris baru dengan semua nilai berupa str.
    Raise:
        ValidasiError: bentuk baris atau tipe nilai tidak sesuai.
    """
    if not isinstance(data, dict):
        raise ValidasiError("baris harus berupa object")
    if None in data:  # DictReader memakai kunci None untuk kolom berlebih
        raise ValidasiError("jumlah kolom melebihi header")
    hilang = [kolom for kolom in KOLOM_INPUT if kolom not in data]
    if hilang:
        raise ValidasiError(f"kolom hilang: {', '.join(hilang)}")

    bersih = {}
    for kolom in KOLOM_INPUT:
        nilai = data[kolom]
        if nilai is None:  # null pada JSON
            nilai = ""
        if not isinstance(nilai, str):
            raise ValidasiError(f"kolom {kolom} harus berupa teks")
        bersih[kolom] = " ".join(nilai.split())

    for kolom in AWALAN_ID:
        bersih[kolom] = bersih[kolom].upper()
    bersih["kategori"] = bersih["kategori"].title()
    return bersih


def validasi_baris(data, tanggal_acuan):
    """Memeriksa kelengkapan dan kebenaran isi satu baris.

    Parameter:
        data (dict): hasil bersihkan_baris().
        tanggal_acuan (date): tanggal "hari ini" untuk perhitungan.
    Return:
        dict: salinan baris yang sudah dinyatakan sah.
    Raise:
        ValidasiError: berisi seluruh alasan penolakan.
    """
    kosong = [kolom for kolom in KOLOM_WAJIB if not data[kolom]]
    if kosong:
        raise ValidasiError(f"kolom kosong: {', '.join(kosong)}")

    masalah = [
        f"{kolom} '{data[kolom]}' harus berbentuk {awalan}001"
        for kolom, awalan in AWALAN_ID.items()
        if not re.fullmatch(awalan + r"\d{3,}", data[kolom], re.ASCII)
    ]

    tanggal = {}
    for kolom in ("tanggal_pinjam", "tanggal_kembali"):
        if data[kolom]:
            try:
                tanggal[kolom] = parse_tanggal(data[kolom])
            except ValidasiError as err:
                masalah.append(f"{kolom}: {err}")

    pinjam = tanggal.get("tanggal_pinjam")
    kembali = tanggal.get("tanggal_kembali")
    if pinjam and pinjam > tanggal_acuan:
        masalah.append("tanggal_pinjam melewati tanggal acuan")
    if kembali and kembali > tanggal_acuan:
        masalah.append("tanggal_kembali melewati tanggal acuan")
    if pinjam and kembali and kembali < pinjam:
        masalah.append("tanggal_kembali lebih awal dari tanggal_pinjam")

    if masalah:
        raise ValidasiError("; ".join(masalah))
    return dict(data)
