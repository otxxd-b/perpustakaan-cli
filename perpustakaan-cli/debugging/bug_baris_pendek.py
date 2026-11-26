"""Reproduksi bug: baris CSV yang kolomnya kurang membuat program berhenti.

File ini SENGAJA masih mengandung bug, hanya untuk demonstrasi debugging.
Jalankan dari folder utama: python debugging/bug_baris_pendek.py
"""
import csv


def bersihkan(baris):
    """Versi awal (bermasalah): menganggap semua nilai pasti string."""
    return {kolom: nilai.strip() for kolom, nilai in baris.items()}


with open("data/peminjaman.csv", encoding="utf-8-sig", newline="") as berkas:
    for baris in csv.DictReader(berkas):
        bersihkan(baris)
