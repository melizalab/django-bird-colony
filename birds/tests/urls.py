from django.urls import include, re_path, path

from django.contrib import admin
from django.contrib.auth import views as authviews

urlpatterns = [
    re_path(r"^birds/", include("birds.urls")),
    re_path(r"^admin/", admin.site.urls),
    re_path(r"^accounts/login/$", authviews.LoginView.as_view(), name="login"),
    re_path(r"^accounts/logout/$", authviews.LogoutView.as_view(), name="logout"),
    re_path(r"^accounts/api-auth/", include("rest_framework.urls")),
]

