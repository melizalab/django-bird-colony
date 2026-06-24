# -*- mode: python -*-
from django.contrib import admin
from django.contrib.auth import views as authviews
from django.urls import include, path

urlpatterns = [
    path("", include("birds.urls")),
    path("admin/", admin.site.urls),
    path("accounts/login/", authviews.LoginView.as_view(), name="login"),
    path("accounts/logout/", authviews.LogoutView.as_view(), name="logout"),
    path("accounts/api-auth/", include("rest_framework.urls")),
]
