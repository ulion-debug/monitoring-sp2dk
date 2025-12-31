from django.db import models

class SP2DK(models.Model):
    nama_wp = models.CharField(max_length=255, null=True, blank=True)
    nama_ar = models.CharField(max_length=255, null=True, blank=True)

    sp2dk_nomor = models.CharField(max_length=255, null=True, blank=True)
    sp2dk_tanggal = models.DateField(null=True, blank=True)
    tahun = models.IntegerField(null=True, blank=True)

    potensi = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    lhp2dk_nomor = models.CharField(max_length=255, null=True, blank=True)
    lhp2dk_tanggal = models.DateField(null=True, blank=True)
    kesimpulan = models.CharField(max_length=255, null=True, blank=True)

    realisasi = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    @property
    def outstanding(self):
        if not self.potensi:
            return 0
        if not self.realisasi:
            return self.potensi
        return self.potensi - self.realisasi

    def success_rate(self):
        if not self.potensi or not self.realisasi:
            return 0
        if self.potensi == 0:
            return 0
        return (self.realisasi / self.potensi) * 100

    def __str__(self):
        return self.sp2dk_nomor or "-"
