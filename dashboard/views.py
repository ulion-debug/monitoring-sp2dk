from django.shortcuts import render, redirect
import requests

from .models import SP2DK
from django.db.models import Sum, Count
from django.db.models.functions import ExtractMonth


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

    token = request.session.get("token")
    if not token:
        return redirect("login")

    auth_res = requests.get(
        API_ME_URL,
        headers={"Authorization": f"Bearer {token}"}
    )

    if auth_res.status_code != 200:
        return redirect("login")

    seksi = request.GET.get("seksi", "All")
    kesimpulan = request.GET.get("kesimpulan", "All")
    
    qs = SP2DK.objects.all()

    if seksi != "All":
        qs = qs.filter(nama_ar=seksi)

    if kesimpulan != "All":
        qs = qs.filter(kesimpulan=kesimpulan)

    records = [
        {
            "NAMA_WP": q.nama_wp,
            "NAMA_AR": q.nama_ar,

            "SP2DK_NOMOR": q.sp2dk_nomor,
            "SP2DK_TANGGAL": q.sp2dk_tanggal,
            "TAHUN": q.tahun,

            "POTENSI": q.potensi,
            "OUTSTANDING": q.outstanding,

            "LHP2DK_NOMOR": q.lhp2dk_nomor,
            "LHP2DK_TANGGAL": q.lhp2dk_tanggal,
            "KESIMPULAN": q.kesimpulan,

            "REALISASI": q.realisasi,

            "SUCCESS_RATE": q.success_rate(),
        }
        for q in qs
    ]


    seksi_list = SP2DK.objects.values_list("nama_ar", flat=True).distinct()
    kesimpulan_list = SP2DK.objects.values_list("kesimpulan", flat=True).distinct()

    pie = qs.values("kesimpulan").annotate(total=Count("id"))
    pie_labels = [p["kesimpulan"] for p in pie]
    pie_values = [p["total"] for p in pie]

    month_data = (
        qs.annotate(bulan=ExtractMonth("sp2dk_tanggal"))
        .values("bulan")
        .annotate(jumlah=Count("id"))
        .order_by("bulan")
    )

    bulan = [m["bulan"] for m in month_data]
    sp2dk_bulanan = [m["jumlah"] for m in month_data]

    return render(request, "dashboard/index.html", {
        "records": records,
        "seksi_list": seksi_list,
        "kesimpulan_list": kesimpulan_list,
        "pie_labels": pie_labels,
        "pie_values": pie_values,
        "bulan": bulan,
        "sp2dk_bulanan": sp2dk_bulanan,
        "selected_seksi": seksi,
        "selected_kesimpulan": kesimpulan,
    })
