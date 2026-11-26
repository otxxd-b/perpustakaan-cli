"""Pengolahan data: transformasi, duplikat, pencarian, filter, pengelompokan."""
from datetime import timedelta

from .config import DENDA_PER_HARI, LAMA_PINJAM_HARI, STATUS_VALID
from .errors import ValidasiError
from .validator import bersihkan_baris, parse_tanggal, validasi_baris


def hitung_keterlambatan(record, tanggal_acuan):
    """Menambahkan jatuh tempo, status, hari terlambat, dan denda.

    Parameter:
        record (dict): baris yang sudah valid.
        tanggal_acuan (date): dipakai bila buku belum dikembalikan.
    Return:
        dict: record baru (record asli tidak diubah).
    """
    jatuh_tempo = parse_tanggal(record["tanggal_pinjam"]) + timedelta(
        days=LAMA_PINJAM_HARI
    )
    sudah_kembali = bool(record["tanggal_kembali"])
    akhir = (
        parse_tanggal(record["tanggal_kembali"]) if sudah_kembali else tanggal_acuan
    )
    terlambat = max(0, (akhir - jatuh_tempo).days)

    if sudah_kembali:
        status = "kembali_terlambat" if terlambat else "kembali_tepat"
    else:
        status = "terlambat" if terlambat else "dipinjam"

    return {
        **record,
        "jatuh_tempo": jatuh_tempo.isoformat(),
        "status": status,
        "hari_terlambat": terlambat,
        "denda": terlambat * DENDA_PER_HARI,
    }


def proses_data(baris_mentah, tanggal_acuan):
    """Memvalidasi, menghapus duplikat, dan mentransformasi seluruh data.

    Parameter:
        baris_mentah (list[dict]): hasil io_handler.baca_data().
        tanggal_acuan (date): tanggal perhitungan keterlambatan.
    Return:
        tuple (valid, ditolak):
            valid (list[dict]): data bersih dan unik.
            ditolak (list[dict]): baris tidak valid atau duplikat + alasan.
    """
    valid = []
    ditolak = []
    id_terpakai = set()      # cek duplikat ID dengan cepat
    sidik_terpakai = set()   # membedakan duplikat identik dan konflik ID

    for item in baris_mentah:
        try:
            bersih = bersihkan_baris(item["data"])
            record = validasi_baris(bersih, tanggal_acuan)
        except ValidasiError as err:
            ditolak.append(_catat_penolakan(item, str(err)))
            continue

        sidik = tuple(record.values())
        if record["id_pinjam"] in id_terpakai:
            alasan = (
                "duplikat: data identik"
                if sidik in sidik_terpakai
                else "duplikat: id_pinjam sama tetapi isi berbeda"
            )
            ditolak.append(_catat_penolakan(item, alasan))
            continue

        id_terpakai.add(record["id_pinjam"])
        sidik_terpakai.add(sidik)
        valid.append(hitung_keterlambatan(record, tanggal_acuan))

    return valid, ditolak


def _catat_penolakan(item, alasan):
    """Menyusun satu baris laporan penolakan. Return: dict."""
    data = item["data"] if isinstance(item["data"], dict) else {}
    return {**data, "baris": item["baris"], "alasan": alasan}


def cari(records, kata_kunci):
    """Mencari pada ID, nama anggota, dan judul (tidak peka huruf besar).

    Parameter:
        records (list[dict]): data valid.
        kata_kunci (str): teks yang dicari.
    Return:
        list[dict]: data yang cocok (dapat kosong).
    Raise:
        ValidasiError: kata kunci kosong.
    """
    kunci = kata_kunci.strip().casefold()
    if not kunci:
        raise ValidasiError("Kata kunci tidak boleh kosong.")
    kolom_cari = ("id_pinjam", "id_anggota", "nama_anggota", "kode_buku", "judul_buku")
    return [
        r for r in records
        if any(kunci in r[kolom].casefold() for kolom in kolom_cari)
    ]


def saring(records, status=None, kategori=None):
    """Menyaring data berdasarkan status dan/atau kategori.

    Parameter:
        records (list[dict]): data valid.
        status (str | None): salah satu STATUS_VALID.
        kategori (str | None): nama kategori.
    Return:
        list[dict]: data yang memenuhi semua kriteria.
    Raise:
        ValidasiError: status atau kategori tidak dikenal.
    """
    status = (status or "").strip().lower()
    kategori = (kategori or "").strip().casefold()

    if status and status not in STATUS_VALID:
        raise ValidasiError(
            f"Status '{status}' tidak dikenal. Pilihan: {', '.join(STATUS_VALID)}"
        )
    tersedia = {r["kategori"].casefold(): r["kategori"] for r in records}
    if kategori and records and kategori not in tersedia:
        raise ValidasiError(
            f"Kategori '{kategori}' tidak ada. Pilihan: "
            f"{', '.join(sorted(tersedia.values()))}"
        )
    return [
        r for r in records
        if (not status or r["status"] == status)
        and (not kategori or r["kategori"].casefold() == kategori)
    ]


def kelompokkan(records, kunci):
    """Mengelompokkan data berdasarkan satu kolom.

    Parameter:
        records (list[dict]): data valid.
        kunci (str): nama kolom pengelompokan.
    Return:
        dict[str, list[dict]]: nilai kolom -> daftar record.
    """
    kelompok = {}
    for record in records:
        kelompok.setdefault(record[kunci], []).append(record)
    return kelompok
