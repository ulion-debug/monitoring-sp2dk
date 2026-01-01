from django.db import models

class SP2DK(models.Model):
    no = models.IntegerField(null=True, blank=True)
    npwp = models.CharField(max_length=50, null=True, blank=True)
    nama_wp = models.CharField(max_length=255, null=True, blank=True)

    unit_kerja = models.CharField(max_length=255, null=True, blank=True)
    petugas_pengawasan = models.CharField(max_length=255, null=True, blank=True)

    tahun_pajak = models.IntegerField(null=True, blank=True)

    nilai_potensi_lha = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    nilai_data_pemicu = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    nilai_potensi_analisis_mandiri = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    estimasi_lha_mandiri = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)
    estimasi_data_lain = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    total_estimasi_dpp = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    jumlah_sp2dk = models.IntegerField(null=True, blank=True)
    nilai_potensi_awal_sp2dk = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    jumlah_lhp2dk_selesai = models.IntegerField(null=True, blank=True)
    nilai_lhp2dk_selesai = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    jumlah_usul_pemeriksaan = models.IntegerField(null=True, blank=True)
    nilai_usul_pemeriksaan = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    jumlah_usul_bukper = models.IntegerField(null=True, blank=True)
    nilai_usul_bukper = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    jumlah_dalam_pengawasan = models.IntegerField(null=True, blank=True)
    nilai_dalam_pengawasan = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    realisasi = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    def success_rate(self):
        if not self.total_estimasi_dpp or not self.realisasi or self.total_estimasi_dpp == 0:
            return 0
        return (self.realisasi / self.total_estimasi_dpp) * 100

    def __str__(self):
        return self.nama_wp or "-"
