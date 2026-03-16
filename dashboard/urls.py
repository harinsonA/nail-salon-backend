from django.urls import path
from django.views.generic import RedirectView
# from dashboard.views import DashboardView

urlpatterns = [
    # path("", DashboardView.as_view(), name="home"),
    path("", RedirectView.as_view(pattern_name="calendar", permanent=False)),
]
