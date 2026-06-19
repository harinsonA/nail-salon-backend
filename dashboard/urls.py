from django.urls import path
from django.views.generic import RedirectView

from dashboard.views import (
    DashboardView,
    AttendedClientsChartAjax,
    IncomeChartAjax,
    AppointmentStatusChartAjax,
    PaymentMethodsChartAjax,
    TopServicesChartAjax,
    IncomeByCategoryChartAjax,
)

urlpatterns = [
    # La raíz sigue redirigiendo al calendario; el dashboard vive en /dashboard/
    path("", RedirectView.as_view(pattern_name="calendar", permanent=False)),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    # Endpoints AJAX (uno por gráfico)
    path(
        "dashboard/clientes-atendidos/ajax/",
        AttendedClientsChartAjax.as_view(),
        name="dashboard_attended_clients_ajax",
    ),
    path(
        "dashboard/ingresos/ajax/",
        IncomeChartAjax.as_view(),
        name="dashboard_income_ajax",
    ),
    path(
        "dashboard/estado-citas/ajax/",
        AppointmentStatusChartAjax.as_view(),
        name="dashboard_appointment_status_ajax",
    ),
    path(
        "dashboard/metodos-pago/ajax/",
        PaymentMethodsChartAjax.as_view(),
        name="dashboard_payment_methods_ajax",
    ),
    path(
        "dashboard/servicios-top/ajax/",
        TopServicesChartAjax.as_view(),
        name="dashboard_top_services_ajax",
    ),
    path(
        "dashboard/ingresos-categoria/ajax/",
        IncomeByCategoryChartAjax.as_view(),
        name="dashboard_income_by_category_ajax",
    ),
]
