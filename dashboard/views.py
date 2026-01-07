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
from django.core.paginator import Paginator

API_LOGIN_URL = "http://127.0.0.1:8001/login"
API_ME_URL = "http://127.0.0.1:8001/me"

def require_login(view):
    def wrapper(request, *args, **kwargs):
        if not request.session.get("token"):
            return redirect("login")
        return view(request, *args, **kwargs)
    return wrapper


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

@require_login
def dashboard(request):
    tahun_sp2dk = request.GET.get("tahun_sp2dk", "All")
    seksi = request.GET.get("seksi", "All")
    ar = request.GET.get("ar", "All")
    kesimpulan_filter = request.GET.get("kesimpulan", "All")

    qs = SP2DK.objects.all()

    if tahun_sp2dk != "All":
        qs = qs.filter(tahun_pajak=tahun_sp2dk)

    if seksi != "All":
        qs = qs.filter(unit_kerja=seksi)

    if ar != "All":
        qs = qs.filter(petugas_pengawasan=ar)

    excel = os.path.join(settings.BASE_DIR, "dashboard/data/terbitsp2dk-060103137-2025.xlsx")

    df = pd.read_excel(excel, header=None, skiprows=5, usecols=range(23))

    df.columns = [
        "no","npwp","nama_wp","nip_ar","nama_ar",
        "lhpt_nomor","lhpt_tanggal",
        "nomor_sp2dk","tanggal_sp2dk","tahun_sp2dk",
        "estimasi_potensi_sp2dk",
        "nomor_lhp2dk","tanggal_lhp2dk",
        "keputusan","kesimpulan",
        "estimasi_potensi_lhp2dk","realisasi",
        "dspp_nomor","dspp_tanggal",
        "np2_nomor","np2_tanggal",
        "sp2_nomor","sp2_tanggal",
    ]

    df["npwp"] = df["npwp"].astype(str).str.replace(".", "").str.strip()
    df["tahun_sp2dk"] = pd.to_numeric(df["tahun_sp2dk"], errors="coerce")

    db_df = pd.DataFrame(qs.values(
        "npwp",
        "tahun_pajak",
        "total_estimasi_dpp",
        "unit_kerja",
        "petugas_pengawasan"
    ))

    db_df["npwp"] = db_df["npwp"].astype(str).str.replace(".", "").str.strip()

    merged = pd.merge(
        df,
        db_df,
        left_on=["npwp", "tahun_sp2dk"],
        right_on=["npwp", "tahun_pajak"],
        how="inner"
    )

    merged["kesimpulan"] = merged["kesimpulan"].astype(str).str.strip()

    if kesimpulan_filter != "All":
        merged = merged[merged["kesimpulan"] == kesimpulan_filter]

    merged["potensi_awal"] = pd.to_numeric(
        merged["estimasi_potensi_sp2dk"], errors="coerce"
    ).fillna(0).astype(float)
    merged["potensi_akhir"] = pd.to_numeric(
        merged["estimasi_potensi_lhp2dk"], errors="coerce"
    ).fillna(0).astype(float)

    merged["realisasi"] = merged["potensi_awal"]

    seksi_summary = (
        merged.groupby("unit_kerja")
        .agg(
            sp2dk=("nomor_sp2dk", "count"),
            lhp2dk=("nomor_lhp2dk", "count"),
            potensi_awal=("potensi_awal", "sum"),
            potensi_akhir=("potensi_akhir", "sum"),
            realisasi=("realisasi", "sum"),
        )
    ).reset_index()

    seksi_summary["outstanding"] = seksi_summary["sp2dk"] - seksi_summary["lhp2dk"]
    
    seksi_summary["success_rate"] = (
        (seksi_summary["lhp2dk"] / seksi_summary["sp2dk"]) * 100
    ).round(2).fillna(0)

    seksi_summary["unit_key"] = (
        seksi_summary["unit_kerja"]
        .str.replace(" ", "_")
        .str.replace("/", "_")
        .str.replace("-", "_")
    )

    ar_detail = (
        merged.groupby(["unit_kerja", "petugas_pengawasan"])
        .agg(
            sp2dk=("nomor_sp2dk", "count"),
            lhp2dk=("nomor_lhp2dk", "count"),
            outstanding=("nomor_sp2dk", "count"),
            potensi=("potensi_akhir", "sum"),
            realisasi=("realisasi", "sum"),
        )
    ).reset_index()

    ar_detail["unit_key"] = (
        ar_detail["unit_kerja"]
        .str.replace(" ", "_")
        .str.replace("/", "_")
        .str.replace("-", "_")
    )

    total_dpp = int(seksi_summary["sp2dk"].sum())
    total_lhp2dk = int(seksi_summary["lhp2dk"].sum())
    total_outstanding = total_dpp - total_lhp2dk

    total_potensi_awal = merged["potensi_awal"].sum()
    total_potensi_akhir = merged["potensi_akhir"].sum()
    total_realisasi = merged["realisasi"].sum()

    kes = merged["kesimpulan"].value_counts()
    pie_labels = kes.index.tolist()
    pie_values = kes.values.tolist()

    merged["tanggal_sp2dk"] = merged["tanggal_sp2dk"].astype(str).str.strip()
    merged["tanggal_sp2dk"] = pd.to_datetime(
        merged["tanggal_sp2dk"],
        format="%d-%m-%Y",
        errors="coerce"
    )
    merged["bulan"] = merged["tanggal_sp2dk"].dt.month_name()


    bar_data = merged["bulan"].value_counts().reindex([
        "January","February","March","April","May","June",
        "July","August","September","October","November","December"
    ]).fillna(0)

    bar_labels = list(bar_data.index)
    indo = {
        "January":"Januari","February":"Februari","March":"Maret","April":"April",
        "May":"Mei","June":"Juni","July":"Juli","August":"Agustus",
        "September":"September","October":"Oktober","November":"November","December":"Desember"
        }
    bar_labels = [indo[b] for b in bar_labels]

    bar_values = [float(v) for v in bar_data.values]

    return render(request, "dashboard/index.html", {
        "menu": "ringkasan",

        "seksi_summary": seksi_summary.to_dict(orient="records"),
        "ar_detail": ar_detail.to_dict(orient="records"),

        "total_dpp": total_dpp,
        "total_lhp2dk": total_lhp2dk,
        "total_outstanding": total_outstanding,
        "total_potensi_awal": total_potensi_awal,
        "total_potensi_akhir": total_potensi_akhir,
        "total_realisasi": total_realisasi,

        "tahun_list": SP2DK.objects.values_list("tahun_pajak", flat=True).distinct(),
        "seksi_list": SP2DK.objects.values_list("unit_kerja", flat=True).distinct(),
        "ar_list": SP2DK.objects.values_list("petugas_pengawasan", flat=True).distinct(),

        "selected_tahun_sp2dk": tahun_sp2dk,
        "selected_seksi": seksi,
        "selected_ar": ar,
        "selected_kesimpulan": kesimpulan_filter,

        "pie_labels": pie_labels,
        "pie_values": pie_values,
        "bar_labels": bar_labels,
        "bar_values": bar_values,
    })

@require_login
def sp2dk_closed(request):

    file_path = os.path.join(settings.BASE_DIR, "dashboard/data/terbitsp2dk-060103137-2025.xlsx")

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

    df["tahun_sp2dk"] = pd.to_numeric(df["tahun_sp2dk"], errors="coerce").astype("Int64")
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

    df["hari"] = (
        pd.to_datetime(df["tanggal_lhp2dk"], format="%d-%m-%Y", errors="coerce")
        - pd.to_datetime(df["tanggal_sp2dk"], format="%d-%m-%Y", errors="coerce")
    ).dt.days

    df["hari"] = df["hari"].astype("Int64")
    
    df["tanggal_sp2dk_dt"] = pd.to_datetime(df["tanggal_sp2dk"], errors="coerce")
    df["tanggal_lhp2dk_dt"] = pd.to_datetime(df["tanggal_lhp2dk"], errors="coerce")
    
    df["status"] = df["nomor_lhp2dk"].apply(
        lambda x: "Closed" if pd.notna(x) and str(x).strip() != "" else "Open"
    )
    
    df["waktu_closed"] = df["hari"]

    money_cols = [
        "estimasi_potensi_sp2dk",
        "estimasi_potensi_lhp2dk",
        "realisasi",
    ]
    
    for col in ["tanggal_sp2dk_dt", "tanggal_lhp2dk_dt"]:
        df[col.replace("_dt", "")] = df[col].dt.strftime("%d-%m-%Y")
        df[col.replace("_dt", "")] = df[col.replace("_dt", "")].fillna("").replace("nan", "")

    for col in money_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(float)

    tahun_list = sorted(df["tahun_sp2dk"].dropna().unique().tolist())
    ar_list = sorted(df["nama_ar"].dropna().unique().tolist())

    tahun = request.GET.get("tahun", "All")
    ar = request.GET.get("ar", "All")
    kesimpulan = request.GET.get("kesimpulan", "All")
    min_hari = request.GET.get("min_hari")
    max_hari = request.GET.get("max_hari")
    status = request.GET.get("status", "All")

    df_filtered = df.copy()

    if tahun != "All":
        df_filtered = df_filtered[df_filtered["tahun_sp2dk"] == int(tahun)]

    if ar != "All":
        df_filtered = df_filtered[df_filtered["nama_ar"] == ar]

    if kesimpulan != "All":
        df_filtered = df_filtered[df_filtered["kesimpulan"] == kesimpulan]

    if min_hari:
        df_filtered = df_filtered[df_filtered["hari"] >= int(min_hari)]

    if max_hari:
        df_filtered = df_filtered[df_filtered["hari"] <= int(max_hari)]
        
    if status != "All":
        df_filtered = df_filtered[df_filtered["status"] == status]

    total_potensi = df_filtered["estimasi_potensi_sp2dk"].sum()
    total_realisasi = df_filtered["realisasi"].sum()

    data = df_filtered.to_dict(orient="records")
    page_number = request.GET.get("page", 1)
    paginator = Paginator(data, 10)
    page_obj = paginator.get_page(page_number)

    return render(request, "dashboard/sp2dk_closed.html", {
        "menu": "closed",
        "data": page_obj,

        "tahun_list": tahun_list,
        "ar_list": ar_list,

        "selected_tahun": tahun,
        "selected_ar": ar,
        "selected_kesimpulan": kesimpulan,

        "total_potensi": total_potensi,
        "total_realisasi": total_realisasi,

        "min_hari": min_hari,
        "max_hari": max_hari,
    })
   
@require_login 
def sp2dk_outstanding(request):

    file_path = os.path.join(settings.BASE_DIR, "dashboard/data/terbitsp2dk-060103137-2025.xlsx")
    df = pd.read_excel(file_path, header=None, skiprows=5, usecols=range(23))
    
    df.columns = [
        "no","npwp","nama_wp","nip_ar","nama_ar",
        "lhpt_nomor","lhpt_tanggal",
        "nomor_sp2dk","tanggal_sp2dk","tahun_sp2dk",
        "estimasi_potensi_sp2dk",
        "nomor_lhp2dk","tanggal_lhp2dk",
        "keputusan","kesimpulan",
        "estimasi_potensi_lhp2dk","realisasi",
        "dspp_nomor","dspp_tanggal",
        "np2_nomor","np2_tanggal",
        "sp2_nomor","sp2_tanggal",
    ]

    df["tahun_sp2dk"] = pd.to_numeric(df["tahun_sp2dk"], errors="coerce").astype("Int64")
    df["nama_ar"] = df["nama_ar"].astype(str).str.strip()

    df["tanggal_sp2dk_dt"] = pd.to_datetime(df["tanggal_sp2dk"], errors="coerce")

    df = df[df["nomor_lhp2dk"].isna()]

    today = pd.Timestamp.today().normalize()
    df["hari"] = (today - df["tanggal_sp2dk_dt"]).dt.days
    df["hari"] = df["hari"].astype("Int64")

    df["estimasi_potensi_sp2dk"] = pd.to_numeric(df["estimasi_potensi_sp2dk"], errors="coerce").fillna(0)
    df["realisasi"] = pd.to_numeric(df["realisasi"], errors="coerce").fillna(0)

    tahun = request.GET.get("tahun", "All")
    ar    = request.GET.get("ar", "All")

    min_hari = request.GET.get("min_hari")
    max_hari = request.GET.get("max_hari")

    if tahun != "All":
        df = df[df["tahun_sp2dk"] == int(tahun)]

    if ar != "All":
        df = df[df["nama_ar"] == ar]

    if min_hari:
        df = df[df["hari"] >= int(min_hari)]

    if max_hari:
        df = df[df["hari"] <= int(max_hari)]

    tahun_list = sorted(df["tahun_sp2dk"].dropna().unique().tolist())
    ar_list = sorted(df["nama_ar"].dropna().unique().tolist())

    df["tanggal_sp2dk"] = df["tanggal_sp2dk_dt"].dt.strftime("%d-%m-%Y").fillna("-")

    paginator = Paginator(df.to_dict(orient="records"), 15)
    page = request.GET.get("page", 1)
    data_page = paginator.get_page(page)

    total_potensi = df["estimasi_potensi_sp2dk"].sum()
    total_realisasi = df["realisasi"].sum()

    return render(request, "dashboard/sp2dk_outstanding.html",{
        "menu": "outstanding",

        "data": data_page,

        "tahun_list": tahun_list,
        "ar_list": ar_list,

        "selected_tahun": tahun,
        "selected_ar": ar,

        "total_potensi": total_potensi,
        "total_realisasi": total_realisasi,

        "min_hari": min_hari,
        "max_hari": max_hari,
    })