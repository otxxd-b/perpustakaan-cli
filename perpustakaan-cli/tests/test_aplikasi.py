"""Unit test. Jalankan: python -m unittest -v"""
import contextlib
import csv
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from perpustakaan.cli import main
from perpustakaan.errors import BerkasError, FormatDataError, ValidasiError
from perpustakaan.io_handler import baca_data, tulis_json
from perpustakaan.processor import cari, proses_data, saring
from perpustakaan.report import buat_rekap, format_rupiah
from perpustakaan.validator import parse_tanggal

DATA = Path(__file__).resolve().parent.parent / "data"
ACUAN = date(2026, 11, 26)
HEADER = ("id_pinjam,id_anggota,nama_anggota,kode_buku,judul_buku,kategori,"
          "tanggal_pinjam,tanggal_kembali\n")


def muat(nama):
    """Membaca dan memproses satu file contoh."""
    return proses_data(baca_data(DATA / nama), ACUAN)


def jalankan(*argumen, masukan=()):
    """Menjalankan CLI. Return: (exit_code, stdout, stderr)."""
    keluar, galat = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(keluar), contextlib.redirect_stderr(galat):
        with patch("builtins.input", side_effect=list(masukan)):
            kode = main(list(argumen))
    return kode, keluar.getvalue(), galat.getvalue()


class TestDataNormal(unittest.TestCase):
    def setUp(self):
        self.valid, self.ditolak = muat("peminjaman.csv")
        self.rekap = buat_rekap(self.valid, self.ditolak, ACUAN)

    def test_jumlah_baris(self):
        r = self.rekap["ringkasan"]
        self.assertEqual(r["total_baris_input"], 18)
        self.assertEqual(r["data_valid"], 10)
        self.assertEqual(r["data_duplikat"], 2)
        self.assertEqual(r["data_tidak_valid"], 6)

    def test_denda_dihitung_manual(self):
        # Hari terlambat dihitung tangan: jatuh tempo = pinjam + 7 hari.
        harapan = {"P001": 0, "P002": 3000, "P003": 16000, "P004": 0,
                   "P005": 0, "P006": 1000, "P007": 0, "P008": 0,
                   "P013": 0, "P015": 0}
        self.assertEqual({r["id_pinjam"]: r["denda"] for r in self.valid}, harapan)
        self.assertEqual(self.rekap["ringkasan"]["total_denda"], 20000)

    def test_normalisasi(self):
        p006 = next(r for r in self.valid if r["id_pinjam"] == "P006")
        self.assertEqual(p006["nama_anggota"], "Siti Rahma")
        self.assertEqual(p006["kode_buku"], "B001")
        self.assertEqual(p006["kategori"], "Teknologi")

    def test_duplikat_id_pertama_yang_valid_dipakai(self):
        # P005 muncul dua kali dengan isi berbeda.
        alasan = [r["alasan"] for r in self.ditolak if r["id_pinjam"] == "P005"]
        self.assertEqual(alasan, ["duplikat: id_pinjam sama tetapi isi berbeda"])

    def test_rekap_konsisten(self):
        for bagian in ("per_kategori", "per_anggota"):
            self.assertEqual(sum(s["denda"] for s in self.rekap[bagian].values()), 20000)
            self.assertEqual(sum(s["jumlah"] for s in self.rekap[bagian].values()), 10)
        self.assertEqual(sum(self.rekap["per_status"].values()), 10)

    def test_json(self):
        valid, ditolak = muat("peminjaman.json")
        self.assertEqual(len(valid), 3)
        self.assertEqual(len(ditolak), 1)
        self.assertEqual(sum(r["denda"] for r in valid), 4000)


class TestCariFilter(unittest.TestCase):
    def setUp(self):
        self.valid, _ = muat("peminjaman.csv")

    def test_cari_tidak_peka_huruf(self):
        self.assertEqual(len(cari(self.valid, "PYTHON")), 3)
        self.assertEqual(cari(self.valid, "tidak ada"), [])

    def test_cari_kosong(self):
        with self.assertRaises(ValidasiError):
            cari(self.valid, "   ")

    def test_saring(self):
        hasil = saring(self.valid, "terlambat", "TEKNOLOGI")
        self.assertEqual([r["id_pinjam"] for r in hasil], ["P003"])
        self.assertEqual(len(saring(self.valid)), 10)

    def test_saring_tidak_dikenal(self):
        with self.assertRaises(ValidasiError):
            saring(self.valid, status="hilang")
        with self.assertRaises(ValidasiError):
            saring(self.valid, kategori="Komik")


class TestEdgeCase(unittest.TestCase):
    def test_file_hanya_header(self):
        valid, ditolak = muat("edge_kosong.csv")
        self.assertEqual((valid, ditolak), ([], []))
        rekap = buat_rekap(valid, ditolak, ACUAN)
        self.assertEqual(rekap["ringkasan"]["total_denda"], 0)
        self.assertEqual(rekap["buku_terpopuler"], [])

    def test_batas_jatuh_tempo(self):
        valid, _ = muat("edge_jatuh_tempo.csv")
        self.assertEqual(
            [(r["status"], r["denda"]) for r in valid],
            [("kembali_tepat", 0), ("kembali_terlambat", 1000),
             ("dipinjam", 0), ("terlambat", 1000)],
        )

    def test_tanggal(self):
        self.assertEqual(parse_tanggal("2028-02-29"), date(2028, 2, 29))
        for salah in ("2026-02-29", "2026-1-5", "20260105", "", "9999-12-31", None):
            with self.subTest(salah=salah), self.assertRaises(ValidasiError):
                parse_tanggal(salah)

    def test_rupiah(self):
        self.assertEqual(format_rupiah(0), "Rp0")
        self.assertEqual(format_rupiah(1234000), "Rp1.234.000")


class TestError(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.tmp = Path(folder.name)

    def tulis(self, nama, isi):
        path = self.tmp / nama
        path.write_bytes(isi.encode("utf-8") if isinstance(isi, str) else isi)
        return path

    def test_file_tidak_ada(self):
        with self.assertRaises(BerkasError):
            baca_data(self.tmp / "hilang.csv")

    def test_path_folder(self):
        (self.tmp / "folder.csv").mkdir()
        with self.assertRaises(BerkasError):
            baca_data(self.tmp / "folder.csv")

    def test_format_salah(self):
        kasus = {
            "a.txt": "x",
            "kosong.csv": "",
            "kolom.csv": "id_pinjam\nP001\n",
            "ganda.csv": HEADER.strip() + ",id_pinjam\n",
            "kutip.csv": HEADER + 'P001,A001,"Andi,B001\n',
            "biner.csv": b"\xff\xfe\x00\x81",
            "rusak.json": "[{",
            "kosong.json": "",
            "objek.json": "{}",
            "surrogate.json": '[{"id_pinjam": "\\ud800"}]',
            "dalam.json": "[" * 100000,
        }
        for nama, isi in kasus.items():
            with self.subTest(nama=nama), self.assertRaises(FormatDataError):
                baca_data(self.tulis(nama, isi))

    def test_csv_dengan_bom_excel(self):
        path = self.tulis("bom.csv", "﻿" + HEADER)
        self.assertEqual(baca_data(path), [])

    def test_baris_bermasalah_tidak_menghentikan_program(self):
        path = self.tulis("a.csv", HEADER + "P001\n"
                          "P002,A001,Andi,B001,Judul,Fiksi,2026-11-01,,lebih\n"
                          "P003,A001,Andi,B001,Judul,Fiksi,2026-12-01,\n")
        valid, ditolak = proses_data(baca_data(path), ACUAN)
        self.assertEqual(valid, [])
        self.assertEqual(len(ditolak), 3)

    def test_kolom_hilang_tidak_dianggap_belum_kembali(self):
        baris = "P001,A001,Andi,B001,Judul,Fiksi,2026-11-01"  # hanya 7 kolom
        objek = dict(zip(HEADER.strip().split(",")[:-1], baris.split(",")))
        objek["tanggal_kembalii"] = "2026-11-02"  # salah ketik nama kunci
        for nama, isi in (("a.csv", HEADER + baris + "\n"),
                          ("a.json", json.dumps([objek]))):
            with self.subTest(nama=nama):
                valid, ditolak = proses_data(baca_data(self.tulis(nama, isi)), ACUAN)
                self.assertEqual(valid, [])
                self.assertEqual(ditolak[0]["alasan"], "kolom hilang: tanggal_kembali")

    def test_json_elemen_aneh(self):
        path = self.tulis("a.json", '[1, "x", null, [], {}]')
        valid, ditolak = proses_data(baca_data(path), ACUAN)
        self.assertEqual((len(valid), len(ditolak)), (0, 5))

    def test_baris_tidak_valid_tidak_memblokir_id(self):
        path = self.tulis("a.csv", HEADER +
                          "P001,A001,Andi,B001,Judul,Fiksi,salah,\n"
                          "P001,A001,Andi,B001,Judul,Fiksi,2026-11-01,\n")
        valid, ditolak = proses_data(baca_data(path), ACUAN)
        self.assertEqual((len(valid), len(ditolak)), (1, 1))

    def test_tulis_gagal(self):
        penghalang = self.tulis("file", "x")
        with self.assertRaises(BerkasError):
            tulis_json(penghalang / "rekap.json", {})


class TestCLI(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.tmp = Path(folder.name)
        self.opsi = ["-i", str(DATA / "peminjaman.csv"), "-t", "2026-11-26"]

    def test_proses_menulis_tiga_file(self):
        kode, _, _ = jalankan("proses", *self.opsi, "-o", str(self.tmp))
        self.assertEqual(kode, 0)
        with (self.tmp / "data_bersih.csv").open(encoding="utf-8", newline="") as f:
            self.assertEqual(len(list(csv.DictReader(f))), 10)
        with (self.tmp / "data_ditolak.csv").open(encoding="utf-8", newline="") as f:
            self.assertEqual(len(list(csv.DictReader(f))), 8)
        rekap = json.loads((self.tmp / "rekap.json").read_text(encoding="utf-8"))
        self.assertEqual(rekap["ringkasan"]["total_denda"], 20000)

    def test_input_tidak_boleh_tertimpa(self):
        salinan = self.tmp / "data_bersih.csv"
        isi = (DATA / "peminjaman.csv").read_bytes()
        salinan.write_bytes(isi)
        kode, _, galat = jalankan("proses", "-i", str(salinan), "-o", str(self.tmp))
        self.assertEqual(kode, 1)
        self.assertIn("menimpa", galat)
        self.assertEqual(salinan.read_bytes(), isi)

    def test_hard_link_input_tidak_tertimpa(self):
        asal = self.tmp / "asal.csv"
        isi = (DATA / "peminjaman.csv").read_bytes()
        asal.write_bytes(isi)
        try:
            os.link(asal, self.tmp / "data_bersih.csv")
        except OSError:
            self.skipTest("sistem file tidak mendukung hard link")
        kode, _, _ = jalankan("proses", "-i", str(asal), "-o", str(self.tmp))
        self.assertEqual(kode, 1)
        self.assertEqual(asal.read_bytes(), isi)

    def test_folder_output_tidak_sah(self):
        kode, keluar, _ = jalankan("menu", *self.opsi, masukan=["5", "a\0b", "0"])
        self.assertEqual(kode, 0)
        self.assertIn("Error:", keluar)

    def test_karakter_di_luar_encoding_terminal(self):
        path = self.tmp / "uni.csv"
        path.write_text(HEADER + "P001,A001,\u0141ukasz,B001,Judul,Fiksi,2026-11-01,\n",
                        encoding="utf-8")
        hasil = subprocess.run(
            [sys.executable, "-m", "perpustakaan", "filter", "-i", str(path),
             "-t", "2026-11-26"],
            cwd=DATA.parent, capture_output=True,
            env={**os.environ, "PYTHONIOENCODING": "cp1252"})
        self.assertEqual(hasil.returncode, 0, hasil.stderr)

    def test_exit_code_error(self):
        for argumen in (["rekap", "-i", "tidak_ada.csv"],
                        ["rekap", *self.opsi[:2], "-t", "26-11-2026"],
                        ["cari", " ", *self.opsi]):
            with self.subTest(argumen=argumen):
                kode, _, galat = jalankan(*argumen)
                self.assertEqual(kode, 1)
                self.assertIn("Error:", galat)

    def test_menu_tahan_input_salah(self):
        kode, keluar, _ = jalankan(
            "menu", *self.opsi,
            masukan=["9", "abc", "", "2", "", "3", "hilang", "", "1", "0"])
        self.assertEqual(kode, 0)
        self.assertEqual(keluar.count("Pilihan tidak dikenal"), 3)
        self.assertIn("Kata kunci tidak boleh kosong", keluar)
        self.assertIn("tidak dikenal. Pilihan", keluar)
        self.assertIn("Rp20.000", keluar)

    def test_menu_semua_fitur(self):
        kode, keluar, _ = jalankan(
            "menu", *self.opsi,
            masukan=["2", "siti", "3", "", "fiksi", "4", "5", str(self.tmp), "0"])
        self.assertEqual(kode, 0)
        self.assertIn("Total: 2 data", keluar)
        self.assertIn("Total: 3 data", keluar)
        self.assertTrue((self.tmp / "rekap.json").exists())

    def test_dibatalkan(self):
        for gangguan in (KeyboardInterrupt, EOFError):
            kode, _, _ = jalankan("menu", *self.opsi, masukan=[gangguan])
            self.assertEqual(kode, 130)


if __name__ == "__main__":
    unittest.main()
