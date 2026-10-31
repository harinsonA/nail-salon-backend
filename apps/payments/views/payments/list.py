from django import forms
from django.db.models import Sum
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView

from apps.appointments.models import Cita
from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.custom_time_fields import MONTH_NUMBER_TO_NAME, CustomMonthField
from apps.common.exports.columns import ExcelColumn
from apps.common.exports.excel_export_mixin import ExcelExportMixin
from apps.common.utils.currency import Money
from apps.common.utils.dates import format_short_date_time
from apps.common.views.base_views import ProtectedView
from apps.payments.accounting import PaymentExpressions
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
        year, month = timezone.localdate().strftime("%Y-%m").split("-")
        return f"{MONTH_NUMBER_TO_NAME[int(month)]} {year}"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "url_payments_list": reverse_lazy("payments_list"),
                "url_payments_export": reverse_lazy("payments_export"),
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
    _filters = {
        "estado_pago__in": [EstadoPago.COMPLETADO],
        "cita__estado": Cita.EstadoChoices.COMPLETADA,
    }

    field_list = [
        "fecha_cita",
        "cliente_nombre",
        "descuento_total",
        "total_cita",
        "fecha_pago_completado",
    ]

    ordering_fields = {
        "0": "fecha_cita",
        "1": "cliente_nombre",
        "2": "descuento_total",
        "3": "total_cita",
        "4": "fecha_pago_completado",
    }

    def get_queryset(self):
        return PaymentExpressions.with_appointment_summary(super().get_queryset())

    def get_values(self, queryset):
        values = super().get_values(queryset)
        for item in values:
            item.update(
                {
                    "fecha_cita_display": format_short_date_time(item.get("fecha_cita")),
                    "fecha_pago_completado_display": format_short_date_time(
                        item.get("fecha_pago_completado")
                    ),
                    "descuento_total_formatted": Money.format(
                        item.get("descuento_total")
                    ),
                    "total_cita_formatted": Money.format(item.get("total_cita")),
                }
            )
        return values

    def additional_data(self, queryset) -> dict:
        additional_data = queryset.aggregate(
            suma_total=Sum("total_cita"),
            descuento_total=Sum("descuento_total"),
        )
        total = additional_data.get("suma_total", 0)
        discount = additional_data.get("descuento_total", 0)
        _filters = self.get_filters()
        received = queryset.filter(
            fecha_pago_completado__gte=_filters.get("fecha_cita__gte"),
            fecha_pago_completado__lte=_filters.get("fecha_cita__lte"),
        ).aggregate(total=Sum("total_cita"))

        return {
            "total_cita": Money.format(total),
            "descuento_total": Money.format(discount),
            "monto_recibido_mes": Money.format(received.get("total", 0)),
        }


class PaymentsExportView(ExcelExportMixin, PaymentsListView):
    force_export = True
    excel_filename = "pagos"
    excel_sheet_title = "Pagos"

    excel_columns = [
        ExcelColumn("Fecha cita", "fecha_cita_display", width=20, align="center"),
        ExcelColumn("Cliente", "cliente_nombre", width=30),
        ExcelColumn("Descuento", "descuento_total_formatted", width=16, align="right"),
        ExcelColumn(
            "Total de la cita", "total_cita_formatted", width=16, align="right"
        ),
        ExcelColumn(
            "Fecha pago completado",
            "fecha_pago_completado_display",
            width=22,
            align="center",
        ),
    ]


# endregion
"""========================================================================="""
