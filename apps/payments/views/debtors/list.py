from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import Coalesce
from django.urls import reverse_lazy
from django.views.generic import TemplateView

from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.utils.currency import format_currency
from apps.common.views.base_views import ProtectedView
from apps.payments.models import Pago
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
            }
        )
        return context


class DebtorsListView(BaseListViewAjax):
    model = Pago
    include_options_column = False
    _filters = {"estado_pago__in": [EstadoPago.PENDIENTE]}

    field_list = [
        "pk",
        "fecha_cita",
        "cliente_nombre",
        "monto_total_cita",
        "total_abonado",
        "saldo_pendiente",
    ]

    ordering_fields = {
        "0": "fecha_cita",
        "1": "cliente_nombre",
        "2": "monto_total_cita",
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
                total_abonado=Coalesce(
                    Sum("detalles_pago__monto_pago"),
                    Decimal("0"),
                ),
                saldo_pendiente=ExpressionWrapper(
                    F("monto_total_cita") - F("total_abonado"),
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
                    "monto_total_cita_formatted": format_currency(
                        item.get("monto_total_cita")
                    ),
                    "total_abonado_formatted": format_currency(
                        item.get("total_abonado")
                    ),
                    "saldo_pendiente_formatted": format_currency(
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
            monto_total_cita=Sum("monto_total_cita"),
            total_abonado=Sum("detalles_pago__monto_pago"),
        )
        total = additional_data.get("monto_total_cita", 0)
        total_abonado = additional_data.get("total_abonado", 0)
        return {
            "monto_total_cita": format_currency(total),
            "total_abonado": format_currency(total_abonado),
        }


# endregion
"""========================================================================="""
