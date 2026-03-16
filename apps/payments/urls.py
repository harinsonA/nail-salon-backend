from django.urls import path
from apps.payments.views.payments.list import PaymentsView, PaymentsListView
from apps.payments.views.debtors.list import DebtorsView, DebtorsListView
from apps.payments.views.debtors.debt_detail import (
    DebtDetailModalView,
    ServicesDetailListView,
    PaymentDetailListView,
)

urlpatterns = [
    path(
        "pagos/",
        PaymentsView.as_view(),
        name="payments",
    ),
    path(
        "pagos/lista/ajax",
        PaymentsListView.as_view(),
        name="payments_list",
    ),
    path(
        "deudores/",
        DebtorsView.as_view(),
        name="debtors",
    ),
    path(
        "deudores/lista/ajax",
        DebtorsListView.as_view(),
        name="debtors_list",
    ),
    path(
        "deudores/<int:pk>/detalle-deudor/",
        DebtDetailModalView.as_view(),
        name="debt_detail_modal",
    ),
    path(
        "deudores/<int:pk>/detalle-deudor/pagos",
        PaymentDetailListView.as_view(),
        name="payment_detail_list",
    ),
    path(
        "deudores/<int:pk>/detalle-deudor/servicios/<int:appointment_id>/",
        ServicesDetailListView.as_view(),
        name="services_detail_list",
    ),
]
