from django.contrib import admin
from django.urls import path
from dashboard.views import dashboard, login_page, logout_view, sp2dk_closed, sp2dk_outstanding,upload_page, upload_dpp, upload_sp2dk_current, upload_sp2dk_previous

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", login_page, name="login"),
    path("logout/", logout_view, name="logout"),
    path("sp2dk-closed/", sp2dk_closed, name="sp2dk_closed"),
    path("sp2dk-outstanding/", sp2dk_outstanding, name="sp2dk_outstanding"),
    path("dashboard", dashboard, name="dashboard"),
    path("upload/", upload_page, name="upload_page"),
    path("upload/dpp/", upload_dpp, name="upload_dpp"),
    path("upload/sp2dk-current/", upload_sp2dk_current, name="upload_sp2dk_current"),
    path("upload/sp2dk-previous/", upload_sp2dk_previous, name="upload_sp2dk_previous"),
]
