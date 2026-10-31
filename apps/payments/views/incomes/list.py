from datetime import timedelta

from django import forms
from django.db.models import Sum
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import TemplateView

from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.custom_time_fields import CustomDateField
from apps.common.exports.columns import ExcelColumn
from apps.common.exports.excel_export_mixin import ExcelExportMixin
from apps.common.form_classes import FORM_SELECT_CLASS
from apps.common.utils.currency import Money
from apps.common.utils.dates import format_short_date_time
from apps.common.views.base_views import ProtectedView
from apps.payments.accounting import PaymentExpressions, PaymentLabels
from apps.payments.models import DetallePago

from ...choices import MetodoPago, TipoMovimiento

DEFAULT_RANGE_IN_DAYS = 15
DATE_FORMAT = "%d/%m/%Y"
ALL_PAYMENT_METHODS = ""
PAYMENT_METHOD_CHOICES = [(ALL_PAYMENT_METHODS, "Todos"), *MetodoPago.CHOICES]
VALID_PAYMENT_METHODS = {value for value, _ in MetodoPago.CHOICES}
ALL_MOVEMENTS = ""
MOVEMENT_CHOICES = [
    (ALL_MOVEMENTS, "Todos"),
    (TipoMovimiento.INGRESO, "Ingresos"),
    (TipoMovimiento.EGRESO, "Egresos"),
]
VALID_MOVEMENTS = {value for value, _ in TipoMovimiento.CHOICES}

"""========================================================================="""
# region ........ Helpers


def get_default_date_range():
    today = timezone.localdate()
    return today - timedelta(days=DEFAULT_RANGE_IN_DAYS), today


def movements():
    return DetallePago.objects.annotate(
        tipo_movimiento=PaymentExpressions.movement_kind(),
        monto_movimiento=PaymentExpressions.signed_amount(),
    )


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Form


class IncomesFilterForm(forms.Form):
    date_from = CustomDateField(
        label="Desde",
        required=False,
    )
    date_to = CustomDateField(
        label="Hasta",
        required=False,
    )
    payment_method = forms.CharField(
        label="Método de pago",
        initial=ALL_PAYMENT_METHODS,
        required=False,
        widget=forms.Select(
            choices=PAYMENT_METHOD_CHOICES,
            attrs={"class": FORM_SELECT_CLASS},
        ),
    )
    movement = forms.CharField(
        label="Movimiento",
        initial=ALL_MOVEMENTS,
        required=False,
        widget=forms.Select(
            choices=MOVEMENT_CHOICES,
            attrs={"class": FORM_SELECT_CLASS},
        ),
    )

    def clean(self):
        cleaned_data = super().clean()
        default_from, default_to = get_default_date_range()
        date_from = cleaned_data.get("date_from") or default_from
        date_to = cleaned_data.get("date_to") or default_to
        if date_from > date_to:
            date_from, date_to = date_to, date_from

        filters = {
            "fecha_pago__date__gte": date_from,
            "fecha_pago__date__lte": date_to,
        }
        payment_method = cleaned_data.get("payment_method")
        if payment_method in VALID_PAYMENT_METHODS:
            filters["metodo_pago"] = payment_method
        movement = cleaned_data.get("movement")
        if movement in VALID_MOVEMENTS:
            filters["tipo_movimiento"] = movement
        return filters


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class IncomesView(ProtectedView, TemplateView):
    template_name = "incomes/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        date_from, date_to = get_default_date_range()
        context.update(
            {
                "url_incomes_list": reverse_lazy("incomes_list"),
                "url_incomes_export": reverse_lazy("incomes_export"),
                "filter_form": IncomesFilterForm(
                    initial={
                        "date_from": date_from.strftime(DATE_FORMAT),
                        "date_to": date_to.strftime(DATE_FORMAT),
                    }
                ),
            }
        )
        return context


class IncomesListView(BaseListViewAjax):
    model = DetallePago
    queryset = movements()
    include_options_column = False
    filter_form_class = IncomesFilterForm
    _filters = {"pago__is_removed": False}

    field_list = [
        "fecha_pago",
        "pago__cliente_nombre",
        "pago__fecha_cita",
        "metodo_pago",
        "referencia_pago",
        "tipo_movimiento",
        "monto_movimiento",
    ]

    ordering_fields = {
        "0": "fecha_pago",
        "1": "pago__cliente_nombre",
        "2": "pago__fecha_cita",
        "3": "metodo_pago",
        "4": "referencia_pago",
        "5": "tipo_movimiento",
        "6": "monto_movimiento",
    }

    def get_order_by(self):
        ordering = super().get_order_by()
        if not ordering:
            return ordering
        return (*ordering, "-pk" if ordering[0].startswith("-") else "pk")

    def get_queryset(self):
        return super().get_queryset().select_related("pago")

    def get_values(self, queryset):
        values = super().get_values(queryset)
        for item in values:
            movement = item.get("tipo_movimiento")
            item.update(
                {
                    "fecha_pago_display": format_short_date_time(item.get("fecha_pago")),
                    "fecha_cita_display": format_short_date_time(
                        item.get("pago__fecha_cita")
                    ),
                    "cliente_nombre": item.get("pago__cliente_nombre"),
                    "metodo_pago_display": PaymentLabels.method(item.get("metodo_pago")),
                    "referencia_pago_display": item.get("referencia_pago") or "—",
                    "tipo_movimiento_display": PaymentLabels.movement(movement),
                    "es_egreso": movement == TipoMovimiento.EGRESO,
                    "monto_movimiento_formatted": Money.format(
                        item.get("monto_movimiento")
                    ),
                }
            )
        return values

    def additional_data(self, queryset) -> dict:
        additional_data = queryset.aggregate(
            total_ingresos=Sum("monto_pago", filter=PaymentExpressions.incoming()),
            total_egresos=Sum("monto_pago", filter=~PaymentExpressions.incoming()),
            total_neto=PaymentExpressions.net_paid(),
        )
        return {
            "total_ingresos": Money.format(additional_data.get("total_ingresos")),
            "total_egresos": Money.format(additional_data.get("total_egresos")),
            "total_neto": Money.format(additional_data.get("total_neto")),
        }


class IncomesExportView(ExcelExportMixin, IncomesListView):
    force_export = True
    excel_filename = "movimientos"
    excel_sheet_title = "Movimientos"

    excel_columns = [
        ExcelColumn("Fecha pago", "fecha_pago_display", width=20, align="center"),
        ExcelColumn("Cliente", "cliente_nombre", width=30),
        ExcelColumn("Fecha cita", "fecha_cita_display", width=20, align="center"),
        ExcelColumn("Método de pago", "metodo_pago_display", width=18, align="center"),
        ExcelColumn("Referencia", "referencia_pago_display", width=22),
        ExcelColumn("Tipo de movimiento", "tipo_movimiento_display", width=20, align="center"),
        ExcelColumn("Monto", "monto_movimiento_formatted", width=16, align="right"),
    ]


# endregion
"""========================================================================="""
