from django.contrib import admin
from django.urls import path
from dashboard.views import dashboard, login_page, logout_view, sp2dk_closed

urlpatterns = [
    path("admin/", admin.site.urls),

    path("login/", login_page, name="login"),
    path("logout/", logout_view, name="logout"),
    path("sp2dk-closed/", sp2dk_closed, name="sp2dk_closed"),
    path("", dashboard, name="dashboard"),
]
