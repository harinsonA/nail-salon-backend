from django.urls import path
from apps.payments.views.list import PaymentsView, PaymentsListView

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
]
