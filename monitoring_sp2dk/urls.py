from django.contrib import admin
from django.urls import path
from dashboard.views import dashboard, login_page, logout_view

urlpatterns = [
    path("admin/", admin.site.urls),

    path("login/", login_page, name="login"),
    path("logout/", logout_view, name="logout"),

    path("", dashboard, name="dashboard"),
]
