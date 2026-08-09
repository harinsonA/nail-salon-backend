from django.urls import path

from apps.payments.views.charts.weekly_income import WeeklyIncomeChartAjax
from apps.payments.views.debtors.add_payment import AddPaymentModalView
from apps.payments.views.debtors.debt_detail import (
    DebtDetailModalView,
    PaymentDetailListView,
    ServicesDetailListView,
)
from apps.payments.views.debtors.list import (
    DebtorsExportView,
    DebtorsListView,
    DebtorsView,
)
from apps.payments.views.incomes.list import (
    IncomesExportView,
    IncomesListView,
    IncomesView,
)
from apps.payments.views.payments.list import (
    PaymentsExportView,
    PaymentsListView,
    PaymentsView,
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
        "pagos/exportar/",
        PaymentsExportView.as_view(),
        name="payments_export",
    ),
    path(
        "pagos/ingresos-semana/ajax",
        WeeklyIncomeChartAjax.as_view(),
        name="payments_weekly_income_ajax",
    ),
    path(
        "ingresos/",
        IncomesView.as_view(),
        name="incomes",
    ),
    path(
        "ingresos/lista/ajax",
        IncomesListView.as_view(),
        name="incomes_list",
    ),
    path(
        "ingresos/exportar/",
        IncomesExportView.as_view(),
        name="incomes_export",
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
        "deudores/exportar/",
        DebtorsExportView.as_view(),
        name="debtors_export",
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
        "deudores/<int:pk>/detalle-deudor/agregar-pago/",
        AddPaymentModalView.as_view(),
        name="add_payment_modal",
    ),
    path(
        "deudores/<int:pk>/detalle-deudor/servicios/<int:appointment_id>/",
        ServicesDetailListView.as_view(),
        name="services_detail_list",
    ),
]
