from django.db import models
from django.utils import timezone
class DPP(models.Model):
    no = models.IntegerField(null=True, blank=True)
    npwp = models.CharField(max_length=50, null=True, blank=True)
    nama_wp = models.CharField(max_length=255, null=True, blank=True)

    unit_kerja = models.CharField(max_length=255, null=True, blank=True)
    petugas_pengawasan = models.CharField(max_length=255, null=True, blank=True)

    tahun_pajak = models.IntegerField(null=True, blank=True)

    nilai_potensi_lha = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    nilai_data_pemicu = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    nilai_potensi_analisis_mandiri = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    estimasi_lha_mandiri = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    estimasi_data_lain = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    total_estimasi_dpp = models.DecimalField(max_digits=20, decimal_places=2)

    jumlah_sp2dk = models.IntegerField(default=0)
    nilai_potensi_awal_sp2dk = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    jumlah_lhp2dk_selesai = models.IntegerField(default=0)
    nilai_lhp2dk_selesai = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    jumlah_usul_pemeriksaan = models.IntegerField(default=0)
    nilai_usul_pemeriksaan = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    jumlah_usul_bukper = models.IntegerField(default=0)
    nilai_usul_bukper = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    jumlah_dalam_pengawasan = models.IntegerField(default=0)
    nilai_dalam_pengawasan = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    realisasi = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    created_time = models.DateTimeField(default=timezone.now)

    def success_rate(self):
        if self.total_estimasi_dpp == 0:
            return 0
        return (self.realisasi / self.total_estimasi_dpp) * 100


class BaseSP2DK(models.Model):
    npwp = models.CharField(max_length=50)
    nama_wp = models.CharField(max_length=255)

    nip_ar = models.CharField(max_length=50)
    nama_ar = models.CharField(max_length=255)

    lhpt_nomor = models.CharField(max_length=100, null=True, blank=True)
    lhpt_tanggal = models.DateField(null=True, blank=True)

    nomor_sp2dk = models.CharField(max_length=100, null=True, blank=True)
    tanggal_sp2dk = models.DateField(null=True, blank=True)
    tahun_pajak = models.IntegerField(null=True, blank=True)
    estimasi_potensi_sp2dk = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    nomor_lhp2dk = models.CharField(max_length=100, null=True, blank=True)
    tanggal_lhp2dk = models.DateField(null=True, blank=True)
    keputusan = models.CharField(max_length=100, null=True, blank=True)
    kesimpulan = models.CharField(max_length=50, null=True, blank=True)
    estimasi_potensi_lhp2dk = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    realisasi = models.DecimalField(max_digits=20, decimal_places=2, default=0)

    dspp_nomor = models.CharField(max_length=100, null=True, blank=True)
    dspp_tanggal = models.DateField(null=True, blank=True)

    np2_nomor = models.CharField(max_length=100, null=True, blank=True)
    np2_tanggal = models.DateField(null=True, blank=True)

    sp2_nomor = models.CharField(max_length=100, null=True, blank=True)
    sp2_tanggal = models.DateField(null=True, blank=True)

    class Meta:
        abstract = True

class SP2DKCurrent(BaseSP2DK):
    """SP2DK Tahun Berjalan"""
    pass


class SP2DKPrevious(BaseSP2DK):
    """SP2DK Tahun Sebelumnya"""
    pass
