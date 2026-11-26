"""Exception khusus aplikasi agar pesan kesalahan mudah dipahami pengguna."""


class AplikasiError(Exception):
    """Induk semua kesalahan yang sudah diperkirakan."""


class BerkasError(AplikasiError):
    """Berkas tidak ditemukan, tidak dapat dibaca, atau tidak dapat ditulis."""


class FormatDataError(AplikasiError):
    """Struktur file CSV/JSON tidak sesuai."""


class ValidasiError(AplikasiError):
    """Nilai pada satu baris data atau input pengguna tidak sah."""
