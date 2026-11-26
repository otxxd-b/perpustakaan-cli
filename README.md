# Aplikasi Pengolah Data Peminjaman Perpustakaan (CLI)

Aplikasi command line Python untuk membersihkan data peminjaman buku, menghitung
keterlambatan dan denda, mencari/menyaring data, dan membuat rekapitulasi.

- Target pengguna: petugas/pustakawan perpustakaan sekolah atau kampus.
- Aturan: lama pinjam **7 hari**, denda **Rp1.000 per hari** terlambat
  (dapat diubah di `perpustakaan/config.py`).

## Kebutuhan

- Python 3.8 atau lebih baru (diuji pada Python 3.11, 3.12, dan 3.13).
- **Tidak ada dependency pihak ketiga**, sehingga tidak perlu `pip install`.
- Standard library: `argparse`, `csv`, `json`, `datetime`, `pathlib`, `re`,
  `os`,
  `sys`. Untuk pengujian: `unittest`, `tempfile`, `contextlib`, `io`,
  `subprocess`, `unittest.mock`. Untuk debugging: `pdb`.
- Package buatan sendiri: `perpustakaan`.

## Cara menjalankan

Buka terminal di folder proyek (folder yang berisi `main.py`). Di Linux/macOS
gunakan `python3` bila perintah `python` tidak tersedia.

```bash
# Menu interaktif
python main.py

# Menu interaktif dengan file dan tanggal tertentu
python main.py menu -i data/peminjaman.csv -t 2026-11-26

# Bersihkan data dan simpan hasil ke folder output/
python main.py proses -i data/peminjaman.csv -o output -t 2026-11-26

# Rekapitulasi, pencarian, dan filter
python main.py rekap -t 2026-11-26
python main.py cari python -t 2026-11-26
python main.py filter --status terlambat -t 2026-11-26
python main.py filter --kategori Fiksi -t 2026-11-26

# Input JSON
python main.py proses -i data/peminjaman.json -o output/json -t 2026-11-26

# Bantuan
python main.py --help
python main.py proses --help
```

Aplikasi juga dapat dijalankan dengan `python -m perpustakaan`.

| Opsi              | Arti                             | Bawaan                |
| ----------------- | -------------------------------- | --------------------- |
| `-i`, `--input`   | file input `.csv` / `.json`      | `data/peminjaman.csv` |
| `-t`, `--tanggal` | tanggal acuan `YYYY-MM-DD`       | tanggal hari ini      |
| `-o`, `--output`  | folder hasil (perintah `proses`) | `output`              |

Opsi ditulis **setelah** nama perintah. Gunakan `-t 2026-11-26` agar hasil sama
persis dengan file contoh. Tanpa `-t`, denda buku yang belum kembali dihitung
sampai hari ini sehingga angkanya bertambah. Menjalankan `proses` ulang akan
menimpa file hasil sebelumnya di folder yang sama.

Kode keluar: `0` sukses, `1` kesalahan data/file/nilai, `2` perintah atau
argumen tidak dikenal, `130` dibatalkan (Ctrl+C).

## Struktur program

```
perpustakaan-cli/
├── main.py                  titik masuk
├── perpustakaan/            package buatan sendiri
│   ├── __init__.py
│   ├── __main__.py          untuk python -m perpustakaan
│   ├── config.py            konstanta
│   ├── errors.py            exception khusus
│   ├── io_handler.py        baca/tulis CSV dan JSON
│   ├── validator.py         validasi dan normalisasi
│   ├── processor.py         denda, duplikat, cari, filter, kelompok
│   ├── report.py            rekapitulasi dan format teks
│   └── cli.py               argparse dan menu interaktif
├── data/                    file input contoh
├── output/                  file hasil contoh
├── tests/                   unit test
└── debugging/               skenario debugging
```

### Alur dependensi antar-module

| Module             | Mengimpor dari package                                               |
| ------------------ | -------------------------------------------------------------------- |
| `main.py`          | `cli`                                                                |
| `cli`              | `config`, `errors`, `io_handler`, `processor`, `report`, `validator` |
| `io_handler`       | `config`, `errors`                                                   |
| `validator`        | `config`, `errors`                                                   |
| `processor`        | `config`, `errors`, `validator`                                      |
| `report`           | `processor`                                                          |
| `config`, `errors` | tidak ada                                                            |

Tidak ada impor melingkar. Alur perintah `proses`:

```
main() -> jalankan_perintah() -> muat()
                                   ├─ baca_data()
                                   └─ proses_data()
                                        ├─ bersihkan_baris()
                                        ├─ validasi_baris()
                                        └─ hitung_keterlambatan()
       -> simpan_hasil()
            ├─ tulis_csv()   (2 kali)
            ├─ buat_rekap()
            └─ tulis_json()
```

## Format input

CSV (pemisah koma, UTF-8, baris pertama header) atau JSON (list of object).

| Kolom             | Wajib                                 | Contoh                     |
| ----------------- | ------------------------------------- | -------------------------- |
| `id_pinjam`       | ya                                    | `P001`                     |
| `id_anggota`      | ya                                    | `A001`                     |
| `nama_anggota`    | ya                                    | `Andi Saputra`             |
| `kode_buku`       | ya                                    | `B001`                     |
| `judul_buku`      | ya                                    | `Dasar Pemrograman Python` |
| `kategori`        | ya                                    | `Teknologi`                |
| `tanggal_pinjam`  | ya                                    | `2026-11-01`               |
| `tanggal_kembali` | tidak (kosong/`null` = belum kembali) | `2026-11-08`               |

Kolom `tanggal_kembali` harus tetap ada di header CSV walaupun nilainya kosong.
Semua nilai pada JSON harus berupa teks (atau `null`) dan kedelapan kunci harus
ada. Baris yang kekurangan kolom/kunci akan ditolak.

## Format output

| File               | Isi                                                             |
| ------------------ | --------------------------------------------------------------- |
| `data_bersih.csv`  | data valid + `jatuh_tempo`, `status`, `hari_terlambat`, `denda` |
| `data_ditolak.csv` | nomor baris, data asli, dan alasan penolakan                    |
| `rekap.json`       | ringkasan, per status/kategori/anggota, 3 buku terpopuler       |

Pada CSV, `baris` adalah nomor baris di file (header = baris 1). Pada JSON,
`baris` adalah urutan object mulai dari 1. Bila satu record CSV memakai
beberapa baris, yang dicatat adalah baris terakhirnya.

Status: `dipinjam`, `terlambat` (belum kembali), `kembali_tepat`,
`kembali_terlambat`.

## File contoh untuk pengujian

| File                          | Tujuan                           | Hasil yang diharapkan                               |
| ----------------------------- | -------------------------------- | --------------------------------------------------- |
| `data/peminjaman.csv`         | data normal bercampur data kotor | 10 valid, 2 duplikat, 6 tidak valid, denda Rp20.000 |
| `data/peminjaman.json`        | input JSON                       | 3 valid, 1 ditolak, denda Rp4.000                   |
| `data/edge_kosong.csv`        | edge case: hanya header          | semua nol, tidak crash                              |
| `data/edge_jatuh_tempo.csv`   | edge case: batas jatuh tempo     | denda 0, 1000, 0, 1000                              |
| `data/error_kolom_kurang.csv` | error: kolom hilang              | pesan kesalahan, kode 1                             |
| `data/error_format.json`      | error: JSON rusak                | pesan kesalahan, kode 1                             |

Hasil contoh tersedia di `output/`, `output/json/`, `output/edge_kosong/`, dan
`output/edge_jatuh_tempo/`.

## Penanganan kesalahan

- File tidak ada, folder, tanpa izin, bukan UTF-8, ekstensi salah.
- CSV kosong, kolom hilang/ganda, tanda kutip rusak; JSON rusak atau bukan list.
- Baris tidak valid atau duplikat dicatat tanpa menghentikan program.
- Tanggal salah, tanggal masa depan, tanggal kembali sebelum tanggal pinjam.
- Input menu salah, kata kunci kosong, status/kategori tidak dikenal.
- Gagal menulis output; file input tidak boleh tertimpa; Ctrl+C.

Aturan duplikat: `id_pinjam` yang sama hanya diterima satu kali, yaitu baris
**valid pertama**.

## Pengujian dan debugging

```bash
python -m unittest -v                       # 32 pengujian

python debugging/bug_baris_pendek.py
PS C:\Users\alber\Documents\ambil disini\uts pemrog\perpustakaan-cli> python debugging/bug_baris_pendek.py
Traceback (most recent call last):
  File "C:\Users\alber\Documents\ambil disini\uts pemrog\perpustakaan-cli\debugging\bug_baris_pendek.py", line 16, in <module>
    bersihkan(baris)
    ~~~~~~~~~^^^^^^^
  File "C:\Users\alber\Documents\ambil disini\uts pemrog\perpustakaan-cli\debugging\bug_baris_pendek.py", line 11, in bersihkan
    return {kolom: nilai.strip() for kolom, nilai in baris.items()}
                   ^^^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'strip'

python -m pdb -c continue debugging/bug_baris_pendek.py
python -m debugging.verifikasi_perbaikan    # setelah diperbaiki
```

Pada pdb ketik `p baris["id_pinjam"]`, lalu `q` untuk keluar (pada Python 3.11
dan 3.12 ketik `q` dua kali).

## Keterbatasan

- CSV yang memakai pemisah titik koma (`;`) belum didukung.
- Konsistensi nama untuk `id_anggota` yang sama dan stok buku tidak diperiksa.
- Denda dari buku yang sudah kembali tidak dicatat status pembayarannya.
- Semua data dimuat ke memori, cocok untuk data berukuran kecil-menengah.

## Referensi

- Dokumentasi Python: [csv](https://docs.python.org/3/library/csv.html),
  [json](https://docs.python.org/3/library/json.html),
  [argparse](https://docs.python.org/3/library/argparse.html),
  [datetime](https://docs.python.org/3/library/datetime.html),
  [pathlib](https://docs.python.org/3/library/pathlib.html),
  [unittest](https://docs.python.org/3/library/unittest.html),
  [pdb](https://docs.python.org/3/library/pdb.html),
  [Errors and Exceptions](https://docs.python.org/3/tutorial/errors.html),
  [Modules](https://docs.python.org/3/tutorial/modules.html)
- [PEP 8](https://peps.python.org/pep-0008/) dan
  [PEP 257](https://peps.python.org/pep-0257/)

## Bantuan AI

Kode, data contoh, pengujian, README, dan lembar jawaban proyek ini disusun
dengan bantuan AI **Claude (Anthropic)**. Data contoh bersifat fiktif.
