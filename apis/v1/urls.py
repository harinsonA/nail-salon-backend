from django.urls import path

from apis.v1.startup.view import StartupView

urlpatterns = [
    path("startup/", StartupView.as_view(), name="api_startup"),
]
