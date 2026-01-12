from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.conf import settings
import pandas as pd
import requests
from .models import DPP, SP2DKCurrent, SP2DKPrevious
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.db.models.functions import ExtractMonth
from datetime import date

API_LOGIN_URL = "http://127.0.0.1:8001/login"

def require_login(view):
    def wrapper(request, *args, **kwargs):
        if not request.session.get("token"):
            return redirect("login")
        return view(request, *args, **kwargs)
    return wrapper

def clean_str(val):
    """
    Semua string kosong / nan / '-' → None (NULL DB)
    """
    if pd.isna(val):
        return None
    val = str(val).strip()
    if val.lower() in ("nan", "", "-", "none"):
        return None
    return val

def clean_date(val):
    """
    Semua tanggal invalid → None
    """
    if pd.isna(val):
        return None
    try:
        return pd.to_datetime(val, dayfirst=True, errors="coerce").date()
    except:
        return None
    
def clean_decimal(val):
    if pd.isna(val):
        return Decimal("0")
    try:
        return Decimal(str(val))
    except:
        return Decimal("0")
    

def to_decimal(val):
    try:
        if pd.isna(val):
            return Decimal("0")
        return Decimal(str(val))
    except (InvalidOperation, ValueError):
        return Decimal("0")
    
def to_int(val):
    try:
        if pd.isna(val):
            return 0
        return int(val)
    except:
        return 0
    
def to_date(val):
    try:
        if pd.isna(val):
            return None
        return pd.to_datetime(val, dayfirst=True, errors="coerce").date()
    except:
        return None
    
def login_page(request):
    if request.session.get("token"):
        return redirect("dashboard")

    if request.method == "POST":
        res = requests.post(API_LOGIN_URL, data={
            "username": request.POST.get("username"),
            "password": request.POST.get("password")
        })

        if res.status_code != 200:
            return render(request, "dashboard/login.html", {"error": True})

        request.session["token"] = res.json()["access_token"]
        return redirect("dashboard")

    return render(request, "dashboard/login.html")

def logout_view(request):
    request.session.flush()
    return redirect("login")

@require_login
def dashboard(request):
    tahun = request.GET.get("tahun_sp2dk", "All")
    seksi = request.GET.get("seksi", "All")
    ar = request.GET.get("ar", "All")
    kesimpulan_filter = request.GET.get("kesimpulan", "All")
    semester = request.GET.get("semester", "All")

    dpp_qs = DPP.objects.all()

    if tahun != "All":
        dpp_qs = dpp_qs.filter(tahun_pajak=tahun)
    if seksi != "All":
        dpp_qs = dpp_qs.filter(unit_kerja=seksi)
    if ar != "All":
        dpp_qs = dpp_qs.filter(petugas_pengawasan=ar)

    if semester == "1":
        dpp_qs = dpp_qs.filter(created_time__month__range=(1, 6))
    elif semester == "2":
        dpp_qs = dpp_qs.filter(created_time__month__range=(7, 12))

    dpp_df = pd.DataFrame(dpp_qs.values(
        "npwp",
        "tahun_pajak",
        "unit_kerja",
        "petugas_pengawasan",
        "nilai_potensi_awal_sp2dk"
    ))

    if dpp_df.empty:
        return render(request, "dashboard/index.html", {"menu": "ringkasan"})

    dpp_df["npwp"] = dpp_df["npwp"].astype(str).str.strip()
    dpp_df["nilai_potensi_awal_sp2dk"] = pd.to_numeric(
        dpp_df["nilai_potensi_awal_sp2dk"], errors="coerce"
    ).fillna(0)

    sp2dk_df = pd.DataFrame(
        SP2DKCurrent.objects.values(
            "npwp",
            "tahun_pajak",
            "nomor_sp2dk",
            "lhpt_nomor",
            "nomor_lhp2dk",
            "tanggal_sp2dk",
            "kesimpulan",
            "estimasi_potensi_lhp2dk",
            "realisasi"
        )
    )

    sp2dk_df["npwp"] = sp2dk_df["npwp"].astype(str).str.strip()
    sp2dk_df["estimasi_potensi_lhp2dk"] = pd.to_numeric(
        sp2dk_df["estimasi_potensi_lhp2dk"], errors="coerce"
    ).fillna(0)
    sp2dk_df["realisasi"] = pd.to_numeric(
        sp2dk_df["realisasi"], errors="coerce"
    ).fillna(0)

    merged = pd.merge(
        sp2dk_df,
        dpp_df,
        on=["npwp", "tahun_pajak"],
        how="left"
    )

    merged["lhpt_ada"] = merged["lhpt_nomor"].notna()
    merged["sp2dk_ada"] = merged["nomor_sp2dk"].notna()
    merged["lhp2dk_ada"] = merged["nomor_lhp2dk"].notna()

    merged["lhpt_sudah_sp2dk"] = merged["lhpt_ada"] & merged["sp2dk_ada"]
    merged["lhpt_belum_sp2dk"] = merged["lhpt_ada"] & ~merged["sp2dk_ada"]

    merged["sp2dk_sudah_lhp2dk"] = merged["sp2dk_ada"] & merged["lhp2dk_ada"]
    merged["sp2dk_belum_lhp2dk"] = merged["sp2dk_ada"] & ~merged["lhp2dk_ada"]

    merged["potensi_awal"] = merged["nilai_potensi_awal_sp2dk"].fillna(0)
    merged["potensi_akhir"] = merged["estimasi_potensi_lhp2dk"].fillna(0)

    if kesimpulan_filter != "All":
        merged = merged[merged["kesimpulan"] == kesimpulan_filter]

    unique_sp2dk = merged.drop_duplicates(subset=["npwp", "nomor_sp2dk"])
    seksi_summary = (
        unique_sp2dk.groupby("unit_kerja")
        .agg(
            dpp=("npwp", "count"),

            lhpt_total=("lhpt_ada", "sum"),
            lhpt_sudah_sp2dk=("lhpt_sudah_sp2dk", "sum"),
            lhpt_belum_sp2dk=("lhpt_belum_sp2dk", "sum"),

            sp2dk_total=("sp2dk_ada", "sum"),
            sp2dk_sudah_lhp2dk=("sp2dk_sudah_lhp2dk", "sum"),
            sp2dk_belum_lhp2dk=("sp2dk_belum_lhp2dk", "sum"),

            potensi_awal=("potensi_awal", "sum"),
            potensi_akhir=("potensi_akhir", "sum"),
            realisasi=("realisasi", "sum"),
        )
        .reset_index()
    )

    seksi_summary["lhpt_pct"] = (
        seksi_summary["lhpt_sudah_sp2dk"] / seksi_summary["lhpt_total"] * 100
    ).replace([float("inf")], 0).fillna(0).round(2)

    seksi_summary["sp2dk_pct"] = (
        seksi_summary["sp2dk_sudah_lhp2dk"] / seksi_summary["sp2dk_total"] * 100
    ).replace([float("inf")], 0).fillna(0).round(2)

    seksi_summary["success_rate"] = (
        seksi_summary["realisasi"] / seksi_summary["potensi_awal"] * 100
    ).replace([float("inf")], 0).fillna(0).round(2)

    seksi_summary["unit_key"] = (
        seksi_summary["unit_kerja"]
        .str.replace(" ", "_")
        .str.replace("/", "_")
        .str.replace("-", "_")
    )

    ar_detail = (
        unique_sp2dk.groupby(["unit_kerja", "petugas_pengawasan"])
        .agg(
            dpp=("npwp", "count"),

            lhpt_total=("lhpt_ada", "sum"),
            lhpt_sudah_sp2dk=("lhpt_sudah_sp2dk", "sum"),
            lhpt_belum_sp2dk=("lhpt_belum_sp2dk", "sum"),

            sp2dk_total=("sp2dk_ada", "sum"),
            sp2dk_sudah_lhp2dk=("sp2dk_sudah_lhp2dk", "sum"),
            sp2dk_belum_lhp2dk=("sp2dk_belum_lhp2dk", "sum"),

            potensi_awal=("potensi_awal", "sum"),
            potensi_akhir=("potensi_akhir", "sum"),
            realisasi=("realisasi", "sum"),
        )
        .reset_index()
    )

    ar_detail["lhpt_pct"] = (
        ar_detail["lhpt_sudah_sp2dk"] / ar_detail["lhpt_total"] * 100
    ).replace([float("inf")], 0).fillna(0).round(2)

    ar_detail["sp2dk_pct"] = (
        ar_detail["sp2dk_sudah_lhp2dk"] / ar_detail["sp2dk_total"] * 100
    ).replace([float("inf")], 0).fillna(0).round(2)

    ar_detail["success_rate"] = (
        ar_detail["realisasi"] / ar_detail["potensi_awal"] * 100
    ).replace([float("inf")], 0).fillna(0).round(2)

    ar_detail["unit_key"] = (
        ar_detail["unit_kerja"]
        .str.replace(" ", "_")
        .str.replace("/", "_")
        .str.replace("-", "_")
    )

    total_dpp = int(seksi_summary["dpp"].sum())

    total_lhp2dk = int(
        seksi_summary["sp2dk_sudah_lhp2dk"].sum()
    )

    total_outstanding = int(
        seksi_summary["sp2dk_belum_lhp2dk"].sum()
    )

    total_potensi_awal = seksi_summary["potensi_awal"].sum()
    total_potensi_akhir = seksi_summary["potensi_akhir"].sum()
    total_realisasi = seksi_summary["realisasi"].sum()

    kes = merged["kesimpulan"].fillna("Belum Ada Kesimpulan").value_counts()
    pie_labels = kes.index.tolist()
    pie_values = kes.values.tolist()

    merged["tanggal_sp2dk"] = pd.to_datetime(
        merged["tanggal_sp2dk"], errors="coerce"
    )
    merged["bulan"] = merged["tanggal_sp2dk"].dt.month_name()

    order = [
        "January","February","March","April","May","June",
        "July","August","September","October","November","December"
    ]

    bar_data = merged["bulan"].value_counts().reindex(order).fillna(0)

    indo = {
        "January":"Januari","February":"Februari","March":"Maret","April":"April",
        "May":"Mei","June":"Juni","July":"Juli","August":"Agustus",
        "September":"September","October":"Oktober","November":"November","December":"Desember"
    }

    bar_labels = [indo[b] for b in bar_data.index]
    bar_values = bar_data.values.tolist()

    return render(request, "dashboard/index.html", {
        "menu": "ringkasan",

        "seksi_summary": seksi_summary.to_dict("records"),
        "ar_detail": ar_detail.to_dict("records"),

        "total_dpp": total_dpp,
        "total_lhp2dk": total_lhp2dk,
        "total_outstanding": total_outstanding,
        "total_potensi_awal": total_potensi_awal,
        "total_potensi_akhir": total_potensi_akhir,
        "total_realisasi": total_realisasi,

        "tahun_list": DPP.objects.values_list("tahun_pajak", flat=True).distinct(),
        "seksi_list": DPP.objects.values_list("unit_kerja", flat=True).distinct(),
        "ar_list": DPP.objects.values_list("petugas_pengawasan", flat=True).distinct(),

        "selected_tahun_sp2dk": tahun,
        "selected_seksi": seksi,
        "selected_ar": ar,
        "selected_kesimpulan": kesimpulan_filter,
        "selected_semester": semester,

        "pie_labels": pie_labels,
        "pie_values": pie_values,
        "bar_labels": bar_labels,
        "bar_values": bar_values,
    })
    
@require_login
def sp2dk_closed(request):

    qs = SP2DKCurrent.objects.all()

    tahun = request.GET.get("tahun", "All")
    ar = request.GET.get("ar", "All")
    min_hari = request.GET.get("min_hari")
    max_hari = request.GET.get("max_hari")
    status_filter = request.GET.get("status", "All")

    if tahun != "All":
        qs = qs.filter(tahun_pajak=tahun)

    if ar != "All":
        qs = qs.filter(nama_ar=ar)

    today = date.today()

    rows = []
    total_potensi = 0
    total_realisasi = 0

    for obj in qs:

        if not obj.tanggal_sp2dk:
            continue

        if obj.tanggal_lhp2dk:
            hari = (obj.tanggal_lhp2dk - obj.tanggal_sp2dk).days

            if hari < 0:
                continue

            status = "Closed"
            waktu_closed = hari
        else:
            hari = (today - obj.tanggal_sp2dk).days
            status = "Open"
            waktu_closed = None

        if status_filter != "All" and status != status_filter:
            continue

        if min_hari and hari < int(min_hari):
            continue
        if max_hari and hari > int(max_hari):
            continue

        estimasi_sp2dk = obj.estimasi_potensi_sp2dk or Decimal("0")
        estimasi_lhp2dk = obj.estimasi_potensi_lhp2dk or Decimal("0")
        realisasi = obj.realisasi or Decimal("0")

        total_potensi += estimasi_lhp2dk
        total_realisasi += realisasi

        rows.append({
            "nip_ar": obj.nip_ar,
            "nama_ar": obj.nama_ar,
            "npwp": obj.npwp,
            "nama_wp": obj.nama_wp,
            "nomor_sp2dk": obj.nomor_sp2dk,
            "tanggal_sp2dk": obj.tanggal_sp2dk,
            "tahun_sp2dk": obj.tahun_pajak,
            "estimasi_potensi_sp2dk": estimasi_sp2dk,

            "nomor_lhp2dk": obj.nomor_lhp2dk,
            "tanggal_lhp2dk": obj.tanggal_lhp2dk,
            "kesimpulan": obj.kesimpulan,
            "estimasi_potensi_lhp2dk": estimasi_lhp2dk,
            "realisasi": realisasi,

            "hari": hari,
            "status": status,
            "waktu_closed": waktu_closed,
        })

    paginator = Paginator(rows, 15)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "dashboard/sp2dk_closed.html", {
        "menu": "closed",
        "data": page,

        "tahun_list": SP2DKCurrent.objects.values_list("tahun_pajak", flat=True).distinct(),
        "ar_list": SP2DKCurrent.objects.values_list("nama_ar", flat=True).distinct(),

        "selected_tahun": tahun,
        "selected_ar": ar,
        "selected_status": status_filter,
        "min_hari": min_hari,
        "max_hari": max_hari,

        "total_potensi": total_potensi,
        "total_realisasi": total_realisasi,
    })

@require_login
def sp2dk_outstanding(request):

    qs = SP2DKPrevious.objects.filter(nomor_lhp2dk__isnull=True)

    tahun = request.GET.get("tahun", "All")
    ar = request.GET.get("ar", "All")
    min_hari = request.GET.get("min_hari")
    max_hari = request.GET.get("max_hari")

    if tahun != "All":
        qs = qs.filter(tahun_pajak=tahun)

    if ar != "All":
        qs = qs.filter(nama_ar=ar)

    today = date.today()

    rows = []
    total_potensi = Decimal("0")
    total_realisasi = Decimal("0")

    for obj in qs:

        if obj.tanggal_sp2dk:
            hari = (today - obj.tanggal_sp2dk).days
            if hari < 0:
                hari = None
        else:
            hari = None

        if min_hari and hari is not None and hari < int(min_hari):
            continue
        if max_hari and hari is not None and hari > int(max_hari):
            continue

        estimasi = obj.estimasi_potensi_sp2dk or Decimal("0")
        realisasi = obj.realisasi or Decimal("0")

        total_potensi += estimasi
        total_realisasi += realisasi

        rows.append({
            "nip_ar": obj.nip_ar,
            "nama_ar": obj.nama_ar,
            "npwp": obj.npwp,
            "nama_wp": obj.nama_wp,
            "nomor_sp2dk": obj.nomor_sp2dk,
            "tanggal_sp2dk": obj.tanggal_sp2dk,
            "tahun_sp2dk": obj.tahun_pajak,
            "estimasi_potensi_sp2dk": estimasi,
            "realisasi": realisasi,
            "hari": hari,
        })

    paginator = Paginator(rows, 15)
    page = paginator.get_page(request.GET.get("page", 1))

    return render(request, "dashboard/sp2dk_outstanding.html", {
        "menu": "outstanding",
        "data": page,
        "tahun_list": SP2DKPrevious.objects.values_list("tahun_pajak", flat=True).distinct(),
        "ar_list": SP2DKPrevious.objects.values_list("nama_ar", flat=True).distinct(),
        "selected_tahun": tahun,
        "selected_ar": ar,
        "min_hari": min_hari,
        "max_hari": max_hari,

        "total_potensi": total_potensi,
        "total_realisasi": total_realisasi,
    })
    
@require_login
def upload_page(request):
    return render(request, "dashboard/upload_page.html", {
        "menu": "upload"
    })

@require_login
def upload_dpp(request):
    if request.method == "POST":
        file = request.FILES.get("file")
        if not file:
            messages.error(request, "File DPP wajib diupload")
            return redirect("upload_page")

        try:
            df = pd.read_csv(file, sep=";", encoding="latin1")

            now = timezone.now()
            current_month = now.month
            current_year = now.year

            last_data = DPP.objects.order_by("-created_time").first()

            if last_data and last_data.created_time.year != current_year:
                DPP.objects.all().delete()
            if 1 <= current_month <= 6:
                DPP.objects.filter(
                    created_time__year=current_year,
                    created_time__month__gte=1,
                    created_time__month__lte=6
                ).delete()

            elif 7 <= current_month <= 12:
                DPP.objects.filter(
                    created_time__year=current_year,
                    created_time__month__gte=7,
                    created_time__month__lte=12
                ).delete()

            objs = []

            for _, r in df.iterrows():
                objs.append(DPP(
                    no=to_int(r["NO"]),
                    npwp=str(r["NPWP"]).strip(),
                    nama_wp=r["Nama WP"],
                    unit_kerja=r["Unit Kerja"],
                    petugas_pengawasan=r["Petugas Pengawasan"],
                    tahun_pajak=to_int(r["Tahun Pajak"]),

                    nilai_potensi_lha=to_decimal(r["Nilai Potensi LHA"]),
                    nilai_data_pemicu=to_decimal(r["Nilai Data Pemicu"]),
                    nilai_potensi_analisis_mandiri=to_decimal(r["Nilai Potensi Analisis Mandiri"]),

                    estimasi_lha_mandiri=to_decimal(
                        r["Penghitungan Estimasi Potensi LHA dan Analisis Mandiri"]
                    ),
                    estimasi_data_lain=to_decimal(
                        r["Penghitungan Estimasi Potensi Data Pemicu dan/atau Data Lainnya"]
                    ),

                    total_estimasi_dpp=to_decimal(
                        r["Total Estimasi Potensi DPP"]
                    ),

                    jumlah_sp2dk=to_int(r["Jumlah SP2DK"]),
                    nilai_potensi_awal_sp2dk=to_decimal(
                        r["Nilai Potensi Awal SP2DK"]
                    ),

                    jumlah_lhp2dk_selesai=to_int(
                        r["Jumlah LHP2DK Selesai"]
                    ),
                    nilai_lhp2dk_selesai=to_decimal(
                        r["Nilai Potensi Akhir LHP2DK Selesai"]
                    ),

                    jumlah_usul_pemeriksaan=to_int(
                        r["Jumlah LHP2DK Usulan Pemeriksaan"]
                    ),
                    nilai_usul_pemeriksaan=to_decimal(
                        r["Nilai Potensi Akhir LHP2DK Usulan Pemeriksaan"]
                    ),

                    jumlah_usul_bukper=to_int(
                        r["Jumlah LHP2DK Usulan Bukper"]
                    ),
                    nilai_usul_bukper=to_decimal(
                        r["Nilai Potensi Akhir LHP2DK Usulan Bukper"]
                    ),

                    jumlah_dalam_pengawasan=to_int(
                        r["Jumlah LHP2DK Dalam Pengawasan"]
                    ),
                    nilai_dalam_pengawasan=to_decimal(
                        r["Nilai Potensi Akhir LHP2DK Dalam Pengawasan"]
                    ),

                    realisasi=to_decimal(r["Realisasi"]),
                    created_time=now,
                ))

            DPP.objects.bulk_create(objs)

            periode = "Jan–Jun" if current_month <= 6 else "Jul–Des"
            messages.success(
                request,
                f"Upload DPP berhasil ({len(objs)} data). Tahun {current_year}, Periode {periode}"
            )
            return redirect("upload_page")

        except Exception as e:
            messages.error(request, f"Gagal upload DPP: {e}")
            return redirect("upload_page")

    return redirect("upload_page")

def _import_sp2dk(df, model):
    model.objects.all().delete()
    objs = []

    for _, r in df.iterrows():
        objs.append(model(
            npwp=clean_str(r[1]),
            nama_wp=clean_str(r[2]),

            nip_ar=clean_str(r[3]),
            nama_ar=clean_str(r[4]),

            lhpt_nomor=clean_str(r[5]),
            lhpt_tanggal=clean_date(r[6]),

            nomor_sp2dk=clean_str(r[7]),
            tanggal_sp2dk=clean_date(r[8]),
            tahun_pajak=int(r[9]) if not pd.isna(r[9]) else None,
            estimasi_potensi_sp2dk=clean_decimal(r[10]),

            nomor_lhp2dk=clean_str(r[11]),
            tanggal_lhp2dk=clean_date(r[12]),
            keputusan=clean_str(r[13]),
            kesimpulan=clean_str(r[14]),
            estimasi_potensi_lhp2dk=clean_decimal(r[15]),
            realisasi=clean_decimal(r[16]),

            dspp_nomor=clean_str(r[17]),
            dspp_tanggal=clean_date(r[18]),

            np2_nomor=clean_str(r[19]),
            np2_tanggal=clean_date(r[20]),

            sp2_nomor=clean_str(r[21]),
            sp2_tanggal=clean_date(r[22]),
        ))

    model.objects.bulk_create(objs)
    
@require_login
def upload_sp2dk_current(request):
    if request.method == "POST":
        df = pd.read_excel(
            request.FILES["file"],
            header=None
        )

        df = df.iloc[5:]

        _import_sp2dk(df, SP2DKCurrent)
        messages.success(request, "Upload SP2DK Tahun Berjalan berhasil")

    return redirect("upload_page")

@require_login
def upload_sp2dk_previous(request):
    if request.method == "POST":
        df = pd.read_excel(
            request.FILES["file"],
            header=None
        )

        df = df.iloc[5:]

        _import_sp2dk(df, SP2DKPrevious)
        messages.success(request, "Upload SP2DK Tahun Sebelumnya berhasil")

    return redirect("upload_page")