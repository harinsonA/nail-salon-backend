from bootstrap_modal_forms.generic import BSModalReadView
from django.db.models import DecimalField, ExpressionWrapper, F
from django.urls import reverse_lazy

from apps.appointments.models import DetalleCita
from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.utils.currency import format_currency
from apps.common.views.base_views import ProtectedView
from apps.payments.choices import MetodoPago, TipoDetallePago
from apps.payments.models import DetallePago, Pago
from apps.payments.services.account import PaymentAccount, appointment_payment_filter

"""========================================================================="""
# region ........ Views


class DebtDetailModalView(ProtectedView, BSModalReadView):
    template_name = "debtors/_debt_detail_modal.html"
    model = Pago

    def get_object(self):
        return (
            self.model.objects.select_related("cita__cliente")
            .filter(pk=self.kwargs.get("pk"))
            .first()
        )

    @staticmethod
    def get_cliente_data(client):
        return {
            "client_full_name": client.nombre_completo,
            "client_phone": client.telefono or "—",
            "client_email": client.email or "—",
            "client_status": client.get_estado_display(),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pago = self.object
        account = PaymentAccount(pago)
        context.update(
            {
                "object": pago,
                "total_cita": format_currency(account.appointment_total()),
                "total_pagado": format_currency(account.appointment_paid()),
                "total_pendiente": format_currency(account.balance()),
                "appointment_id": pago.cita_id,
                "services_detail_list_url": reverse_lazy(
                    "services_detail_list",
                    kwargs={"pk": pago.pk, "appointment_id": pago.cita_id},
                ),
                "payment_detail_list_url": reverse_lazy(
                    "payment_detail_list",
                    kwargs={"pk": pago.pk},
                ),
                **self.get_cliente_data(pago.cita.cliente),
            }
        )
        return context


class ServicesDetailListView(BaseListViewAjax):
    model = DetalleCita
    include_options_column = False

    field_list = [
        "pk",
        "nombre_servicio",
        "precio_servicio",
        "cantidad_servicios",
        "total_servicio",
        "precio_acordado",
        "descuento",
        "servicio__categoria__nombre",
    ]

    ordering_fields = {
        "0": "nombre_servicio",
        "1": "servicio__categoria__nombre",
        "2": "precio_servicio",
        "3": "cantidad_servicios",
        "4": "total_servicio",
        "5": "descuento",
        "6": "precio_acordado",
    }

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                cita_id=self.kwargs.get("appointment_id"),
            )
            .annotate(
                total_servicio=ExpressionWrapper(
                    F("precio_servicio") * F("cantidad_servicios"),
                    output_field=DecimalField(max_digits=10, decimal_places=0),
                )
            )
        )

    def get_values(self, queryset):
        values = super().get_values(queryset)
        for item in values:
            item.update(
                {
                    "precio_formatted": format_currency(item.get("precio_servicio")),
                    "total_servicio_formatted": format_currency(
                        item.get("total_servicio")
                    ),
                    "descuento_formatted": format_currency(item.get("descuento")),
                    "precio_acordado_formatted": format_currency(
                        item.get("precio_acordado")
                    ),
                }
            )
        return values


class PaymentDetailListView(BaseListViewAjax):
    model = DetallePago
    include_options_column = False

    field_list = [
        "pk",
        "fecha_pago",
        "tipo_detalle",
        "metodo_pago",
        "referencia_pago",
        "monto_pago",
    ]

    ordering_fields = {
        "0": "fecha_pago",
        "1": "tipo_detalle",
        "2": "metodo_pago",
        "3": "referencia_pago",
        "4": "monto_pago",
    }

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                appointment_payment_filter(),
                pago_id=self.kwargs.get("pk"),
            )
        )

    def get_values(self, queryset):
        values = super().get_values(queryset)
        payment_method_display = dict(MetodoPago.CHOICES)
        type_display = dict(TipoDetallePago.CHOICES)
        for item in values:
            item.update(
                {
                    "tipo_detalle_display": type_display[
                        item.get("tipo_detalle") or TipoDetallePago.ABONO
                    ],
                    "fecha_pago_display": item.get("fecha_pago").strftime(
                        "%d/%m/%Y %H:%M"
                    )
                    if item.get("fecha_pago")
                    else "-- --",
                    "metodo_pago_display": payment_method_display.get(
                        item.get("metodo_pago"), item.get("metodo_pago")
                    ),
                    "monto_pago_formatted": format_currency(item.get("monto_pago")),
                }
            )
        return values


# endregion
"""========================================================================="""
