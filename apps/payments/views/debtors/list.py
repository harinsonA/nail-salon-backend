from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from apps.appointments.models import Cita
from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.exports.columns import ExcelColumn
from apps.common.exports.excel_export_mixin import ExcelExportMixin
from apps.common.utils.currency import Money
from apps.common.views.base_views import ProtectedView
from apps.payments.models import Pago
from apps.payments.services.account import net_paid, retained_amount

from ...choices import EstadoPago

"""========================================================================="""
# region ........ Views


class DebtorsView(ProtectedView, TemplateView):
    template_name = "debtors/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "url_debtors_list": reverse_lazy("debtors_list"),
                "url_debtors_export": reverse_lazy("debtors_export"),
            }
        )
        return context


class DebtorsListView(BaseListViewAjax):
    model = Pago
    include_options_column = False
    _filters = {
        "estado_pago__in": [EstadoPago.PENDIENTE],
        "cita__estado": Cita.EstadoChoices.COMPLETADA,
    }

    field_list = [
        "pk",
        "fecha_cita",
        "cliente_nombre",
        "total_cita",
        "total_abonado",
        "saldo_pendiente",
    ]

    ordering_fields = {
        "0": "fecha_cita",
        "1": "cliente_nombre",
        "2": "total_cita",
        "3": "total_abonado",
        "4": "saldo_pendiente",
    }

    @staticmethod
    def _format_datetime(value) -> str:
        if not value:
            return "-- --"
        return value.strftime("%d/%m/%Y %H:%M")

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(
                total_pagado=net_paid("detalles_pago__"),
                total_retenido=retained_amount("detalles_pago__"),
            )
            .annotate(
                total_cita=ExpressionWrapper(
                    F("monto_total_cita") - F("total_retenido"),
                    output_field=DecimalField(),
                ),
                total_abonado=ExpressionWrapper(
                    F("total_pagado") - F("total_retenido"),
                    output_field=DecimalField(),
                ),
                saldo_pendiente=ExpressionWrapper(
                    F("monto_total_cita") - F("total_pagado"),
                    output_field=DecimalField(),
                ),
            )
        )

    def get_values(self, queryset):
        values = super().get_values(queryset)
        for item in values:
            payment_id = item.get("pk")
            item.update(
                {
                    "fecha_cita_display": self._format_datetime(item.get("fecha_cita")),
                    "total_cita_formatted": Money.format(item.get("total_cita")),
                    "total_abonado_formatted": Money.format(
                        item.get("total_abonado")
                    ),
                    "saldo_pendiente_formatted": Money.format(
                        item.get("saldo_pendiente")
                    ),
                    "debt_detail_url": reverse_lazy(
                        "debt_detail_modal", kwargs={"pk": payment_id}
                    ),
                    "add_payment_url": reverse_lazy(
                        "add_payment_modal", kwargs={"pk": payment_id}
                    ),
                }
            )
        return values

    def additional_data(self, queryset) -> dict:
        additional_data = queryset.aggregate(
            suma_pendiente=Sum("saldo_pendiente"),
            suma_abonado=Sum("total_abonado"),
        )
        return {
            "total_pendiente": Money.format(additional_data.get("suma_pendiente")),
            "total_abonado": Money.format(additional_data.get("suma_abonado")),
        }


class DebtorsExportView(ExcelExportMixin, DebtorsListView):
    force_export = True
    excel_filename = "deudores"
    excel_sheet_title = "Deudores"

    excel_columns = [
        ExcelColumn("Fecha cita", "fecha_cita_display", width=20, align="center"),
        ExcelColumn("Cliente", "cliente_nombre", width=30),
        ExcelColumn(
            "Total de la cita", "total_cita_formatted", width=16, align="right"
        ),
        ExcelColumn(
            "Total abonado", "total_abonado_formatted", width=16, align="right"
        ),
        ExcelColumn(
            "Total pendiente", "saldo_pendiente_formatted", width=16, align="right"
        ),
    ]


# endregion
"""========================================================================="""
