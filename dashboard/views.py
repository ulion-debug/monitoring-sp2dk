from django.shortcuts import render, redirect
import requests

from .models import SP2DK
from django.db.models import Sum, Count, F
from django.shortcuts import render, redirect
from django.db.models.functions import ExtractMonth
from calendar import month_name
from .models import SP2DKClosed
import pandas as pd
from django.conf import settings
import os

API_LOGIN_URL = "http://127.0.0.1:8001/login"
API_ME_URL = "http://127.0.0.1:8001/me"


def login_page(request):
    if request.session.get("token"):
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        res = requests.post(API_LOGIN_URL, data={
            "username": username,
            "password": password
        })

        if res.status_code != 200:
            return render(request, "dashboard/login.html", {"error": True})

        token = res.json()["access_token"]
        request.session["token"] = token

        return redirect("dashboard")

    return render(request, "dashboard/login.html")


def logout_view(request):
    request.session.flush()
    return redirect("login")


def dashboard(request):
    tahun_sp2dk = request.GET.get("tahun_sp2dk", "All")
    seksi = request.GET.get("seksi", "All")
    ar = request.GET.get("ar", "All")

    qs = SP2DK.objects.all()

    if tahun_sp2dk != "All":
        qs = qs.filter(tahun_pajak=tahun_sp2dk)

    if seksi != "All":
        qs = qs.filter(unit_kerja=seksi)

    if ar != "All":
        qs = qs.filter(petugas_pengawasan=ar)

    seksi_summary = (
        qs.values("unit_kerja")
        .annotate(
            sp2dk=Sum("jumlah_sp2dk"),
            lhp2dk=Sum("jumlah_lhp2dk_selesai"),
            outstanding=Sum("jumlah_sp2dk") - Sum("jumlah_lhp2dk_selesai"),
            potensi=Sum("total_estimasi_dpp"),
            realisasi=Sum("realisasi"),
        )
        .order_by("unit_kerja")
    )

    seksi_summary = list(seksi_summary)

    for s in seksi_summary:
        pot = s["potensi"] or 0
        real = s["realisasi"] or 0

        if pot and pot != 0:
            s["success_rate"] = round((real / pot) * 100, 2)
        else:
            s["success_rate"] = 0

    ar_detail = (
        qs.values("unit_kerja", "petugas_pengawasan")
        .annotate(
            sp2dk=Sum("jumlah_sp2dk"),
            lhp2dk=Sum("jumlah_lhp2dk_selesai"),
            outstanding=Sum("jumlah_sp2dk") - Sum("jumlah_lhp2dk_selesai"),
            potensi=Sum("total_estimasi_dpp"),
            realisasi=Sum("realisasi"),
        )
        .order_by("unit_kerja", "petugas_pengawasan")
    )

    tahun_list = SP2DK.objects.values_list("tahun_pajak", flat=True).distinct()
    seksi_list = SP2DK.objects.values_list("unit_kerja", flat=True).distinct()
    ar_list = SP2DK.objects.values_list("petugas_pengawasan", flat=True).distinct()

    selesai = qs.aggregate(s=Sum("jumlah_lhp2dk_selesai"))["s"] or 0
    pemeriksaan = qs.aggregate(s=Sum("jumlah_usul_pemeriksaan"))["s"] or 0
    pengawasan = qs.aggregate(s=Sum("jumlah_dalam_pengawasan"))["s"] or 0

    pie_labels = ["Selesai", "Usul Pemeriksaan", "Dalam Pengawasan"]
    pie_values = [selesai, pemeriksaan, pengawasan]
    
    bar_data = (
        qs.values("tahun_pajak")
        .annotate(jumlah=Sum("jumlah_sp2dk"))
        .order_by("tahun_pajak")
    )

    bar_labels = [x["tahun_pajak"] for x in bar_data]
    bar_values = [x["jumlah"] for x in bar_data]

    return render(request, "dashboard/index.html", {
        "seksi_summary": seksi_summary,
        "ar_detail": ar_detail,

        "tahun_list": tahun_list,
        "seksi_list": seksi_list,
        "ar_list": ar_list,

        "selected_tahun_sp2dk": tahun_sp2dk,
        "selected_seksi": seksi,
        "selected_ar": ar,

        "pie_labels": pie_labels,
        "pie_values": pie_values,

        "bar_labels": bar_labels,
        "bar_values": bar_values,
    })

def sp2dk_closed(request):

    file_path = os.path.join(settings.BASE_DIR, "dashboard/data/sp2dk_terbit_2025.xlsx")

    df = pd.read_excel(
        file_path,
        header=None,
        skiprows=5,
        usecols=range(23)
    )

    df.columns = [
        "no",
        "npwp",
        "nama_wp",
        "nip_ar",
        "nama_ar",
        "lhpt_nomor",
        "lhpt_tanggal",
        "nomor_sp2dk",
        "tanggal_sp2dk",
        "tahun_sp2dk",
        "estimasi_potensi_sp2dk",
        "nomor_lhp2dk",
        "tanggal_lhp2dk",
        "keputusan",
        "kesimpulan",
        "estimasi_potensi_lhp2dk",
        "realisasi",
        "dspp_nomor",
        "dspp_tanggal",
        "np2_nomor",
        "np2_tanggal",
        "sp2_nomor",
        "sp2_tanggal",
    ]
    
    df["tahun_sp2dk"] = (
        pd.to_numeric(df["tahun_sp2dk"], errors="coerce")
        .astype("Int64")
    )

    df["nama_ar"] = df["nama_ar"].astype(str).str.strip()

    date_cols = [
        "lhpt_tanggal",
        "tanggal_sp2dk",
        "tanggal_lhp2dk",
        "dspp_tanggal",
        "np2_tanggal",
        "sp2_tanggal",
    ]

    for col in date_cols:
        df[col] = (
            pd.to_datetime(df[col], errors="coerce")
            .dt.strftime("%d-%m-%Y")
            .fillna("")
        )

    money_cols = [
        "estimasi_potensi_sp2dk",
        "estimasi_potensi_lhp2dk",
        "realisasi",
    ]

    for col in money_cols:
        df[col] = (
            pd.to_numeric(df[col], errors="coerce")
            .fillna(0)
            .astype(float)
        )

    tahun_list = sorted(df["tahun_sp2dk"].dropna().unique().tolist())
    ar_list = sorted(df["nama_ar"].dropna().unique().tolist())

    tahun = request.GET.get("tahun", "All")
    ar = request.GET.get("ar", "All")
    kesimpulan = request.GET.get("kesimpulan", "All")
    df_filtered = df.copy()

    if tahun != "All" and tahun != "" and tahun is not None:
        df_filtered = df_filtered[df_filtered["tahun_sp2dk"] == int(tahun)]

    if ar != "All" and ar != "" and ar is not None:
        df_filtered = df_filtered[df_filtered["nama_ar"] == ar]

    if kesimpulan != "All" and kesimpulan != "" and kesimpulan is not None:
        df_filtered = df_filtered[df_filtered["kesimpulan"] == kesimpulan]


    total_potensi = df_filtered["estimasi_potensi_sp2dk"].sum()
    total_realisasi = df_filtered["realisasi"].sum()

    data = df_filtered.to_dict(orient="records")

    return render(request, "dashboard/sp2dk_closed.html", {
        "data": data,

        "tahun_list": tahun_list,
        "ar_list": ar_list,

        "selected_tahun": tahun,
        "selected_ar": ar,
        "selected_kesimpulan": kesimpulan,

        "total_potensi": total_potensi,
        "total_realisasi": total_realisasi,
    })