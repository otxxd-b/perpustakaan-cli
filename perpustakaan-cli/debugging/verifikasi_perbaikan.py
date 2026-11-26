"""Membuktikan bug sudah diperbaiki pada package perpustakaan.

Jalankan dari folder utama: python -m debugging.verifikasi_perbaikan
"""
from datetime import date

from perpustakaan.io_handler import baca_data
from perpustakaan.processor import proses_data

valid, ditolak = proses_data(baca_data("data/peminjaman.csv"), date(2026, 11, 26))
print(f"Program selesai tanpa crash: {len(valid)} valid, {len(ditolak)} ditolak")
for baris in ditolak:
    if baris["id_pinjam"] == "P016":
        print(f"Baris {baris['baris']}: {baris['alasan']}")
