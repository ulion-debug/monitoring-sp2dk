from django.core.management.base import BaseCommand
from dashboard.models import SP2DK
from django.conf import settings
import pandas as pd
import os


class Command(BaseCommand):
    help = "Import SP2DK 2025 dari file Excel"

    def handle(self, *args, **kwargs):

        file_path = os.path.join(settings.BASE_DIR, "dashboard", "data", "sp2dk_terbit_2025.xlsx")

        df = pd.read_excel(file_path)

        # normalisasi nama kolom
        df.columns = df.columns.str.strip().str.upper()

        # debug: tampilkan kolom
        print("KOLUMNYA:")
        print(df.columns)

        # kosongkan data lama
        SP2DK.objects.all().delete()

        for _, row in df.iterrows():

            SP2DK.objects.create(
                nama_wp=row.get("NAMA"),
                nama_ar=row.get("NAMA AR"),

                sp2dk_nomor=row.get("SP2DK NOMOR"),
                sp2dk_tanggal=row.get("SP2DK TANGGAL"),
                tahun=row.get("TAHUN"),

                potensi=row.get("ESTIMASI POTENSI"),

                lhp2dk_nomor=row.get("LHP2DK NOMOR"),
                lhp2dk_tanggal=row.get("LHP2DK TANGGAL"),
                kesimpulan=row.get("KESIMPULAN"),
                realisasi=row.get("REALISASI"),
            )

        self.stdout.write(self.style.SUCCESS("✔ Import Excel SP2DK selesai"))
