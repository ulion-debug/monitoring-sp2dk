from django.shortcuts import render, redirect
import requests

from .models import SP2DK
from django.db.models import Sum, Count, F
from django.shortcuts import render, redirect
from django.db.models.functions import ExtractMonth
from calendar import month_name

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

    # === FILTER ===
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

    # =========================
    #  RINGKASAN PER SEKSI
    # =========================
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

    # konversi ke list supaya bisa diedit nilainya
    seksi_summary = list(seksi_summary)

    for s in seksi_summary:
        pot = s["potensi"] or 0
        real = s["realisasi"] or 0

        if pot and pot != 0:
            s["success_rate"] = round((real / pot) * 100, 2)
        else:
            s["success_rate"] = 0

    # =========================
    #  DETAIL PER AR
    # =========================
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

    # =========================
    # DROPDOWN DATA
    # =========================
    tahun_list = SP2DK.objects.values_list("tahun_pajak", flat=True).distinct()
    seksi_list = SP2DK.objects.values_list("unit_kerja", flat=True).distinct()
    ar_list = SP2DK.objects.values_list("petugas_pengawasan", flat=True).distinct()

    # =========================
    # PIE CHART
    # =========================
    selesai = qs.aggregate(s=Sum("jumlah_lhp2dk_selesai"))["s"] or 0
    pemeriksaan = qs.aggregate(s=Sum("jumlah_usul_pemeriksaan"))["s"] or 0
    pengawasan = qs.aggregate(s=Sum("jumlah_dalam_pengawasan"))["s"] or 0

    pie_labels = ["Selesai", "Usul Pemeriksaan", "Dalam Pengawasan"]
    pie_values = [selesai, pemeriksaan, pengawasan]

    # =========================
    # BAR CHART PER TAHUN
    # =========================
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
