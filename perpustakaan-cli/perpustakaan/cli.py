"""Antarmuka command line: argumen (argparse) dan menu interaktif."""
import argparse
import os
import sys
from datetime import date
from pathlib import Path

from .config import KOLOM_DITOLAK, KOLOM_HASIL, STATUS_VALID
from .errors import AplikasiError, BerkasError, ValidasiError
from .io_handler import baca_data, tulis_csv, tulis_json
from .processor import cari, proses_data, saring
from .report import buat_rekap, format_rekap, format_tabel
from .validator import parse_tanggal

INPUT_BAWAAN = "data/peminjaman.csv"
OUTPUT_BAWAAN = "output"


def buat_parser():
    """Mendefinisikan perintah dan opsi. Return: argparse.ArgumentParser."""
    umum = argparse.ArgumentParser(add_help=False)
    umum.add_argument("-i", "--input", default=INPUT_BAWAAN,
                      help="file CSV/JSON (bawaan: %(default)s)")
    umum.add_argument("-t", "--tanggal",
                      help="tanggal acuan YYYY-MM-DD (bawaan: hari ini)")

    parser = argparse.ArgumentParser(
        prog="main.py",
        description="Pengolah data peminjaman buku perpustakaan. "
                    "Tanpa perintah, aplikasi membuka menu interaktif.",
    )
    sub = parser.add_subparsers(dest="perintah")

    proses = sub.add_parser("proses", parents=[umum],
                            help="bersihkan data dan simpan hasil")
    proses.add_argument("-o", "--output", default=OUTPUT_BAWAAN,
                        help="folder hasil (bawaan: %(default)s)")

    sub.add_parser("rekap", parents=[umum], help="tampilkan rekapitulasi")

    p_cari = sub.add_parser("cari", parents=[umum], help="cari data")
    p_cari.add_argument("kata_kunci")

    p_filter = sub.add_parser("filter", parents=[umum], help="saring data")
    p_filter.add_argument("--status", help=", ".join(STATUS_VALID))
    p_filter.add_argument("--kategori")

    sub.add_parser("menu", parents=[umum], help="menu interaktif")
    return parser


def muat(path_input, tanggal_acuan):
    """Membaca lalu memproses file.

    Parameter: path_input (str), tanggal_acuan (date).
    Return: tuple (valid, ditolak).
    """
    return proses_data(baca_data(path_input), tanggal_acuan)


def simpan_hasil(valid, ditolak, tanggal_acuan, path_input, folder_output):
    """Menyimpan data bersih, data ditolak, dan rekap.

    Parameter:
        valid, ditolak (list[dict]); tanggal_acuan (date);
        path_input, folder_output (str).
    Return:
        list[Path]: file yang berhasil ditulis.
    Raise:
        BerkasError: gagal menulis atau file input akan tertimpa.
    """
    folder = Path(folder_output)
    tujuan = [folder / nama for nama in
              ("data_bersih.csv", "data_ditolak.csv", "rekap.json")]
    try:
        # samefile juga mengenali hard link dan symbolic link.
        menimpa = any(t.exists() and os.path.samefile(t, path_input) for t in tujuan)
    except (OSError, ValueError) as err:
        raise BerkasError(f"Folder output tidak dapat diperiksa: {err}") from err
    if menimpa:
        raise BerkasError("Folder output akan menimpa file input. Pilih folder lain.")
    return [
        tulis_csv(tujuan[0], valid, KOLOM_HASIL),
        tulis_csv(tujuan[1], ditolak, KOLOM_DITOLAK),
        tulis_json(tujuan[2], buat_rekap(valid, ditolak, tanggal_acuan)),
    ]


def jalankan_perintah(args, tanggal_acuan):
    """Menjalankan satu perintah non-interaktif. Return: int (exit code)."""
    valid, ditolak = muat(args.input, tanggal_acuan)

    if args.perintah == "proses":
        berkas = simpan_hasil(valid, ditolak, tanggal_acuan, args.input, args.output)
        print(f"Selesai: {len(valid)} data valid, {len(ditolak)} data ditolak.")
        for path in berkas:
            print(f"  tersimpan -> {path.as_posix()}")
        return 0

    if ditolak:
        print(f"Catatan: {len(ditolak)} baris ditolak (jalankan 'proses' "
              "untuk melihat alasannya).", file=sys.stderr)
    if args.perintah == "rekap":
        print(format_rekap(buat_rekap(valid, ditolak, tanggal_acuan)))
    elif args.perintah == "cari":
        print(format_tabel(cari(valid, args.kata_kunci)))
    else:  # filter
        print(format_tabel(saring(valid, args.status, args.kategori)))
    return 0


def tampilkan_menu(path_input, tanggal_acuan):
    """Menu interaktif sampai pengguna memilih keluar. Return: int."""
    valid, ditolak = muat(path_input, tanggal_acuan)
    print(f"Data dimuat: {len(valid)} valid, {len(ditolak)} ditolak.")

    while True:
        print("\n=== MENU PERPUSTAKAAN ===\n"
              "1. Rekapitulasi\n2. Cari data\n3. Filter data\n"
              "4. Lihat data ditolak\n5. Simpan hasil\n0. Keluar")
        pilihan = input("Pilih menu: ").strip()
        try:
            if pilihan == "0":
                print("Terima kasih.")
                return 0
            if pilihan == "1":
                print(format_rekap(buat_rekap(valid, ditolak, tanggal_acuan)))
            elif pilihan == "2":
                print(format_tabel(cari(valid, input("Kata kunci: "))))
            elif pilihan == "3":
                print("Status:", ", ".join(STATUS_VALID))
                status = input("Status (Enter = semua): ")
                kategori = input("Kategori (Enter = semua): ")
                print(format_tabel(saring(valid, status, kategori)))
            elif pilihan == "4":
                for r in ditolak:
                    print(f"Baris {r['baris']}: {r['alasan']}")
                if not ditolak:
                    print("Tidak ada data yang ditolak.")
            elif pilihan == "5":
                folder = input(f"Folder output [{OUTPUT_BAWAAN}]: ").strip()
                for path in simpan_hasil(valid, ditolak, tanggal_acuan,
                                         path_input, folder or OUTPUT_BAWAAN):
                    print(f"  tersimpan -> {path.as_posix()}")
            else:
                print("Pilihan tidak dikenal. Masukkan angka 0-5.")
        except AplikasiError as err:
            # Kesalahan input tidak menghentikan menu.
            print(f"Error: {err}")


def atur_encoding():
    """Mencegah crash karena karakter yang tidak didukung terminal.

    Parameter: tidak ada. Return: None.
    """
    for aliran in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(aliran, "reconfigure"):
            aliran.reconfigure(errors="replace")


def main(argv=None):
    """Titik masuk CLI.

    Parameter:
        argv (list[str] | None): argumen; None berarti memakai sys.argv.
    Return:
        int: 0 sukses, 1 kesalahan aplikasi, 130 dibatalkan pengguna.
        (argparse keluar dengan kode 2 bila argumen salah.)
    """
    atur_encoding()
    args = buat_parser().parse_args(argv)
    try:
        teks_tanggal = getattr(args, "tanggal", None)
        try:
            acuan = date.today() if teks_tanggal is None else parse_tanggal(teks_tanggal)
        except ValidasiError as err:
            raise ValidasiError(f"Opsi --tanggal: {err}") from err

        if args.perintah in (None, "menu"):
            return tampilkan_menu(getattr(args, "input", INPUT_BAWAAN), acuan)
        return jalankan_perintah(args, acuan)
    except AplikasiError as err:
        print(f"Error: {err}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nDibatalkan oleh pengguna.", file=sys.stderr)
        return 130
