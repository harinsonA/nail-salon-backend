from django import forms
from django.db.models import Sum, TextChoices
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from bootstrap_modal_forms.forms import BSModalForm

from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.utils.currency import format_currency
from apps.payments.models import Pago
from ...choices import EstadoPago, MetodoPago

"""========================================================================="""
# region ........ Constants

FORM_CONTROL_CLASS = "form-control form-control--custom"
FORM_SELECT_CLASS = "form-select form-select--custom"

# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Form


# class PaymentsFilterForm(BSModalForm):
#     class StatusChoices(TextChoices):
#         ALL = "all", "Todos"
#         PENDING = EstadoPago.PENDIENTE, "Pendientes"
#         COMPLETED = EstadoPago.COMPLETADO, "Completados"
#         REFUNDED = EstadoPago.REEMBOLSADO, "Reembolsados"
#         UNPAID = EstadoPago.IMPAGO, "Impagos"

#     class PaymentMethodChoices(TextChoices):
#         ALL = "all", "Todos"
#         CASH = MetodoPago.EFECTIVO, "Efectivo"
#         CARD = MetodoPago.TARJETA, "Tarjeta"
#         TRANSFER = MetodoPago.TRANSFERENCIA, "Transferencia"
#         CHECK = MetodoPago.CHEQUE, "Cheque"

#     status = forms.ChoiceField(
#         choices=StatusChoices.choices,
#         label="Estado",
#         initial=StatusChoices.ALL,
#         required=False,
#         widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
#     )

#     payment_method = forms.ChoiceField(
#         choices=PaymentMethodChoices.choices,
#         label="Método de Pago",
#         initial=PaymentMethodChoices.ALL,
#         required=False,
#         widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
#     )

#     date_from = forms.DateField(
#         label="Desde",
#         required=False,
#         widget=forms.DateInput(
#             attrs={
#                 "class": FORM_CONTROL_CLASS,
#                 "type": "date",
#             }
#         ),
#     )

#     date_to = forms.DateField(
#         label="Hasta",
#         required=False,
#         widget=forms.DateInput(
#             attrs={
#                 "class": FORM_CONTROL_CLASS,
#                 "type": "date",
#             }
#         ),
#     )

#     def clean(self):
#         cleaned_data = super().clean()
#         data_to_filter = {}

#         status = cleaned_data.get("status")
#         if status and status != self.StatusChoices.ALL:
#             data_to_filter["estado"] = status

#         payment_method = cleaned_data.get("payment_method")
#         if payment_method and payment_method != self.PaymentMethodChoices.ALL:
#             data_to_filter["metodo_pago"] = payment_method

#         date_from = cleaned_data.get("date_from")
#         if date_from:
#             data_to_filter["fecha__gte"] = date_from

#         date_to = cleaned_data.get("date_to")
#         if date_to:
#             data_to_filter["fecha__lte"] = date_to

#         return data_to_filter


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class PaymentsView(TemplateView):
    template_name = "payments/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "url_payments_list": reverse_lazy("payments_list"),
            }
        )
        return context


class PaymentsListView(BaseListViewAjax):
    model = Pago
    include_options_column = False
    _filters = {"estado_pago__in": [EstadoPago.COMPLETADO]}

    field_list = [
        "fecha_cita",
        "cliente_nombre",
        "descuento_total",
        "monto_total_cita",
        "fecha_pago_completado",
    ]

    ordering_fields = {
        "0": "cliente_nombre",
        "1": "fecha_cita",
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
        return {
            "monto_total_cita": format_currency(total),
            "descuento_total": format_currency(discount),
        }


# endregion
"""========================================================================="""
