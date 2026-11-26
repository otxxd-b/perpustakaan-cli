"""Membaca dan menulis file CSV serta JSON."""
import csv
import json
from pathlib import Path

from .config import KOLOM_INPUT
from .errors import BerkasError, FormatDataError


def baca_data(path):
    """Membaca file input CSV atau JSON.

    Parameter:
        path (str | Path): lokasi file berekstensi .csv atau .json.
    Return:
        list[dict]: baris mentah. Setiap dict berisi kunci "baris" (nomor
        baris/urutan) dan "data" (isi baris).
    Raise:
        BerkasError: file tidak ada atau tidak dapat dibaca.
        FormatDataError: ekstensi atau struktur file salah.
    """
    path = Path(path)
    pembaca = {".csv": _baca_csv, ".json": _baca_json}.get(path.suffix.lower())
    if pembaca is None:
        raise FormatDataError(
            f"Format '{path.suffix or '(tanpa ekstensi)'}' tidak didukung. "
            "Gunakan file .csv atau .json."
        )
    try:
        return pembaca(path)
    except FileNotFoundError as err:
        raise BerkasError(f"File tidak ditemukan: {path}") from err
    except IsADirectoryError as err:
        raise BerkasError(f"Path adalah folder, bukan file: {path}") from err
    except PermissionError as err:
        raise BerkasError(f"Tidak punya izin membaca: {path}") from err
    except UnicodeDecodeError as err:
        raise FormatDataError(f"File bukan teks UTF-8: {path}") from err
    except OSError as err:
        raise BerkasError(f"Gagal membaca {path}: {err}") from err


def _baca_csv(path):
    """Membaca CSV dan memeriksa header. Return: list[dict]."""
    # utf-8-sig membuang BOM yang ditambahkan Microsoft Excel.
    with path.open("r", encoding="utf-8-sig", newline="") as berkas:
        pembaca = csv.DictReader(berkas, strict=True)
        try:
            if pembaca.fieldnames is None:
                raise FormatDataError(f"File CSV kosong (tanpa header): {path}")
            header = [nama.strip().lower() for nama in pembaca.fieldnames]
            _periksa_header(header)
            pembaca.fieldnames = header
            # DictReader mengisi None untuk kolom yang kurang. Kunci tersebut
            # dibuang agar validator tahu bahwa kolomnya memang tidak ada.
            return [
                {"baris": pembaca.line_num,
                 "data": {k: v for k, v in baris.items() if v is not None}}
                for baris in pembaca
            ]
        except csv.Error as err:
            raise FormatDataError(
                f"CSV rusak di sekitar baris {pembaca.line_num}: {err}"
            ) from err


def _periksa_header(header):
    """Memastikan kolom lengkap dan tidak ganda. Return: None."""
    kurang = [kolom for kolom in KOLOM_INPUT if kolom not in header]
    if kurang:
        raise FormatDataError(f"Kolom wajib tidak ada: {', '.join(kurang)}")
    if len(header) != len(set(header)):
        raise FormatDataError("Header CSV memiliki nama kolom ganda atau lebih dari satu kolom kosong.")


def _baca_json(path):
    """Membaca JSON berbentuk list of object. Return: list[dict]."""
    with path.open("r", encoding="utf-8-sig") as berkas:
        teks = berkas.read()
    try:
        isi = json.loads(teks)
        # Menolak karakter yang tidak dapat disimpan kembali (surrogate tunggal).
        json.dumps(isi, ensure_ascii=False).encode("utf-8")
    except json.JSONDecodeError as err:
        raise FormatDataError(
            f"JSON tidak valid pada baris {err.lineno} kolom {err.colno}: {err.msg}"
        ) from err
    except (ValueError, RecursionError) as err:
        raise FormatDataError(f"JSON tidak dapat diproses: {path}") from err
    if not isinstance(isi, list):
        raise FormatDataError("JSON harus berupa list (array) berisi object.")
    return [{"baris": nomor, "data": item} for nomor, item in enumerate(isi, 1)]


def tulis_csv(path, baris_data, kolom):
    """Menyimpan list of dict ke file CSV.

    Parameter:
        path (str | Path): file tujuan.
        baris_data (list[dict]): data yang ditulis.
        kolom (tuple[str]): urutan kolom.
    Return:
        Path: lokasi file yang ditulis.
    Raise:
        BerkasError: file tidak dapat ditulis.
    """
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as berkas:
            penulis = csv.DictWriter(berkas, fieldnames=kolom, extrasaction="ignore")
            penulis.writeheader()
            penulis.writerows(baris_data)
    except (OSError, ValueError) as err:
        raise BerkasError(f"Gagal menulis {path}: {err}") from err
    return path


def tulis_json(path, objek):
    """Menyimpan objek Python ke file JSON.

    Parameter:
        path (str | Path): file tujuan.
        objek (dict | list): data yang dapat diubah ke JSON.
    Return:
        Path: lokasi file yang ditulis.
    Raise:
        BerkasError: file tidak dapat ditulis.
    """
    path = Path(path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as berkas:
            json.dump(objek, berkas, indent=2, ensure_ascii=False)
            berkas.write("\n")
    except (OSError, ValueError) as err:
        raise BerkasError(f"Gagal menulis {path}: {err}") from err
    return path
