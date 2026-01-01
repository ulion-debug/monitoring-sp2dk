import csv
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from dashboard.models import SP2DK
from decimal import Decimal


def to_int(value):
    """
    Bersihkan nilai integer:
    - kosong -> 0
    - '1. ' -> 1
    - '1.234' -> 1234
    """
    if value is None:
        return 0

    value = str(value).strip()

    if value == "":
        return 0

    # hapus titik pemisah ribuan
    value = value.replace(".", "")

    # hapus koma
    value = value.replace(",", "")

    try:
        return int(value)
    except:
        return 0


def to_decimal(value):
    """
    Bersihkan nilai desimal:
    - kosong -> 0
    - 1.234.567 -> 1234567
    - 1,23E+09 -> 1230000000
    """
    if value is None:
        return 0

    value = str(value).strip()

    if value == "":
        return 0

    # format ilmiah 1.23E+09
    if "E" in value or "e" in value:
        try:
            return Decimal(float(value))
        except:
            return 0

    # hapus pemisah ribuan
    value = value.replace(".", "").replace(",", "")

    try:
        return Decimal(value)
    except:
        return 0



class Command(BaseCommand):
    help = "Import SP2DK dari dashboard/data/dpp_2025.csv"

    def handle(self, *args, **options):

        file_path = os.path.join(settings.BASE_DIR, "dashboard", "data", "dpp_2025.csv")

        self.stdout.write(f"Membaca file: {file_path}")

        with open(file_path, newline='', encoding="utf-8-sig") as f:

            reader = csv.DictReader(f, delimiter=";")

            for row in reader:

                SP2DK.objects.create(

                    no=to_int(row.get("NO")),
                    npwp=row.get("NPWP"),
                    nama_wp=row.get("Nama WP"),
                    unit_kerja=row.get("Unit Kerja"),
                    petugas_pengawasan=row.get("Petugas Pengawasan"),
                    tahun_pajak=to_int(row.get("Tahun Pajak")),

                    nilai_potensi_lha=to_decimal(row.get("Nilai Potensi LHA")),
                    nilai_data_pemicu=to_decimal(row.get("Nilai Data Pemicu")),
                    nilai_potensi_analisis_mandiri=to_decimal(row.get("Nilai Potensi Analisis Mandiri")),

                    estimasi_lha_mandiri=to_decimal(row.get("Penghitungan Estimasi Potensi LHA dan Analisis Mandiri")),
                    estimasi_data_lain=to_decimal(row.get("Penghitungan Estimasi Potensi Data Pemicu dan/atau Data Lainnya")),

                    total_estimasi_dpp=to_decimal(row.get("Total Estimasi Potensi DPP")),

                    jumlah_sp2dk=to_int(row.get("Jumlah SP2DK")),
                    nilai_potensi_awal_sp2dk=to_decimal(row.get("Nilai Potensi Awal SP2DK")),

                    jumlah_lhp2dk_selesai=to_int(row.get("Jumlah LHP2DK Selesai")),
                    nilai_lhp2dk_selesai=to_decimal(row.get("Nilai Potensi Akhir LHP2DK Selesai")),

                    jumlah_usul_pemeriksaan=to_int(row.get("Jumlah LHP2DK Usulan Pemeriksaan")),
                    nilai_usul_pemeriksaan=to_decimal(row.get("Nilai Potensi Akhir LHP2DK Usulan Pemeriksaan")),

                    jumlah_usul_bukper=to_int(row.get("Jumlah LHP2DK Usulan Bukper")),
                    nilai_usul_bukper=to_decimal(row.get("Nilai Potensi Akhir LHP2DK Usulan Bukper")),

                    jumlah_dalam_pengawasan=to_int(row.get("Jumlah LHP2DK Dalam Pengawasan")),
                    nilai_dalam_pengawasan=to_decimal(row.get("Nilai Potensi Akhir LHP2DK Dalam Pengawasan")),

                    realisasi=to_decimal(row.get("Realisasi")),
                )

        self.stdout.write(self.style.SUCCESS("Import selesai"))
