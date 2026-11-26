"""Menyusun rekapitulasi dan teks tampilan."""
from .processor import kelompokkan


def _statistik(daftar):
    """Menghitung jumlah, keterlambatan, dan denda. Return: dict."""
    return {
        "jumlah": len(daftar),
        "terlambat": sum(1 for r in daftar if r["hari_terlambat"] > 0),
        "denda": sum(r["denda"] for r in daftar),
    }


def buat_rekap(valid, ditolak, tanggal_acuan):
    """Membuat rekapitulasi seluruh data.

    Parameter:
        valid (list[dict]): data bersih.
        ditolak (list[dict]): data tidak valid atau duplikat.
        tanggal_acuan (date): tanggal perhitungan.
    Return:
        dict: rekap yang siap disimpan sebagai JSON. Tetap sah bila data kosong.
    """
    jumlah_duplikat = sum(1 for r in ditolak if r["alasan"].startswith("duplikat"))
    per_kategori = kelompokkan(valid, "kategori")
    per_anggota = kelompokkan(valid, "id_anggota")
    per_buku = kelompokkan(valid, "kode_buku")

    populer = sorted(per_buku.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:3]

    return {
        "tanggal_acuan": tanggal_acuan.isoformat(),
        "ringkasan": {
            "total_baris_input": len(valid) + len(ditolak),
            "data_valid": len(valid),
            "data_duplikat": jumlah_duplikat,
            "data_tidak_valid": len(ditolak) - jumlah_duplikat,
            "anggota_unik": len({r["id_anggota"] for r in valid}),
            "buku_unik": len({r["kode_buku"] for r in valid}),
            "peminjaman_terlambat": _statistik(valid)["terlambat"],
            "total_denda": _statistik(valid)["denda"],
        },
        "per_status": {
            status: len(daftar)
            for status, daftar in sorted(kelompokkan(valid, "status").items())
        },
        "per_kategori": {
            nama: _statistik(daftar) for nama, daftar in sorted(per_kategori.items())
        },
        "per_anggota": {
            id_anggota: {"nama": daftar[0]["nama_anggota"], **_statistik(daftar)}
            for id_anggota, daftar in sorted(per_anggota.items())
        },
        "buku_terpopuler": [
            {"kode_buku": kode, "judul": daftar[0]["judul_buku"], "dipinjam": len(daftar)}
            for kode, daftar in populer
        ],
    }


def format_rupiah(nilai):
    """Parameter: nilai (int). Return: str, contoh 'Rp12.000'."""
    return "Rp" + f"{nilai:,}".replace(",", ".")


def format_tabel(records):
    """Mengubah daftar record menjadi tabel teks.

    Parameter:
        records (list[dict]): data yang ditampilkan.
    Return:
        str: tabel, atau pesan bila data kosong.
    """
    if not records:
        return "Tidak ada data yang cocok."
    kolom = [
        ("ID", "id_pinjam"), ("Anggota", "nama_anggota"), ("Judul", "judul_buku"),
        ("Jatuh Tempo", "jatuh_tempo"), ("Status", "status"), ("Denda", "denda"),
    ]
    baris = [[judul for judul, _ in kolom]]
    baris += [
        [format_rupiah(r[k]) if k == "denda" else str(r[k]) for _, k in kolom]
        for r in records
    ]
    lebar = [max(len(b[i]) for b in baris) for i in range(len(kolom))]
    teks = [" | ".join(sel.ljust(lebar[i]) for i, sel in enumerate(b)) for b in baris]
    teks.insert(1, "-+-".join("-" * n for n in lebar))
    teks.append(f"Total: {len(records)} data")
    return "\n".join(teks)


def format_rekap(rekap):
    """Mengubah rekap menjadi teks laporan.

    Parameter:
        rekap (dict): hasil buat_rekap().
    Return:
        str: laporan siap cetak.
    """
    r = rekap["ringkasan"]
    teks = [
        f"=== REKAP PEMINJAMAN (per {rekap['tanggal_acuan']}) ===",
        f"Baris input        : {r['total_baris_input']}",
        f"Data valid         : {r['data_valid']}",
        f"Data duplikat      : {r['data_duplikat']}",
        f"Data tidak valid   : {r['data_tidak_valid']}",
        f"Anggota unik       : {r['anggota_unik']}",
        f"Judul buku unik    : {r['buku_unik']}",
        f"Pinjaman terlambat : {r['peminjaman_terlambat']}",
        f"Total denda        : {format_rupiah(r['total_denda'])}",
    ]
    if not r["data_valid"]:
        teks.append("Belum ada data valid untuk direkap.")
        return "\n".join(teks)

    teks.append("\nPer kategori:")
    teks += [
        f"  - {nama}: {s['jumlah']} pinjam, {s['terlambat']} terlambat, "
        f"denda {format_rupiah(s['denda'])}"
        for nama, s in rekap["per_kategori"].items()
    ]
    teks.append("\nAnggota yang memiliki denda:")
    penunggak = [
        f"  - {kode} {s['nama']}: {format_rupiah(s['denda'])}"
        for kode, s in rekap["per_anggota"].items()
        if s["denda"] > 0
    ]
    teks += penunggak or ["  (tidak ada)"]
    teks.append("\nBuku terpopuler:")
    teks += [
        f"  {i}. {b['judul']} ({b['dipinjam']}x)"
        for i, b in enumerate(rekap["buku_terpopuler"], 1)
    ]
    return "\n".join(teks)
