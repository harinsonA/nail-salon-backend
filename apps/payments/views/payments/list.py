from datetime import date

from django import forms
from django.db.models import Sum
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.custom_time_fields import CustomMonthField
from apps.common.utils.currency import format_currency
from apps.common.views.base_views import ProtectedView
from apps.payments.models import Pago
from ...choices import EstadoPago

"""========================================================================="""
# region ........ Form


class PaymentsFilterForm(forms.Form):
    months = CustomMonthField(
        label="Mes",
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        first_day, last_day = cleaned_data.get("months", (None, None))
        return {
            "fecha_cita__gte": first_day,
            "fecha_cita__lte": last_day,
        }


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class PaymentsView(ProtectedView, TemplateView):
    template_name = "payments/list.html"

    @staticmethod
    def get_initial_month() -> str:
        today = date.today()
        return f"{today.strftime('%B %Y')}".capitalize()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "url_payments_list": reverse_lazy("payments_list"),
                "filter_form": PaymentsFilterForm(
                    initial={"months": self.get_initial_month()}
                ),
            }
        )
        return context


class PaymentsListView(BaseListViewAjax):
    model = Pago
    include_options_column = False
    filter_form_class = PaymentsFilterForm
    _filters = {"estado_pago__in": [EstadoPago.COMPLETADO]}

    field_list = [
        "fecha_cita",
        "cliente_nombre",
        "descuento_total",
        "monto_total_cita",
        "fecha_pago_completado",
    ]

    ordering_fields = {
        "0": "fecha_cita",
        "1": "cliente_nombre",
        "2": "descuento_total",
        "3": "monto_total_cita",
        "4": "fecha_pago_completado",
    }

    @staticmethod
    def _format_datetime(value) -> str:
        if not value:
            return "-- --"
        return value.strftime("%d/%m/%Y %H:%M")

    def get_values(self, queryset):
        values = super().get_values(queryset)
        for item in values:
            item.update(
                {
                    "fecha_cita_display": self._format_datetime(item.get("fecha_cita")),
                    "fecha_pago_completado_display": self._format_datetime(
                        item.get("fecha_pago_completado")
                    ),
                    "descuento_total_formatted": format_currency(
                        item.get("descuento_total")
                    ),
                    "monto_total_cita_formatted": format_currency(
                        item.get("monto_total_cita")
                    ),
                }
            )
        return values

    def additional_data(self, queryset) -> dict:
        additional_data = queryset.aggregate(
            monto_total_cita=Sum("monto_total_cita"),
            descuento_total=Sum("descuento_total"),
        )
        total = additional_data.get("monto_total_cita", 0)
        discount = additional_data.get("descuento_total", 0)
        _filters = self.get_filters()
        received = queryset.filter(
            fecha_pago_completado__gte=_filters.get("fecha_cita__gte"),
            fecha_pago_completado__lte=_filters.get("fecha_cita__lte"),
        ).aggregate(total=Sum("monto_total_cita"))

        return {
            "monto_total_cita": format_currency(total),
            "descuento_total": format_currency(discount),
            "monto_recibido_mes": format_currency(received.get("total", 0)),
        }


# endregion
"""========================================================================="""
