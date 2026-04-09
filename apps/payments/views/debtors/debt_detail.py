from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.urls import reverse_lazy

from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.utils.currency import format_currency
from apps.common.views.base_views import ProtectedView
from apps.payments.models import Pago, DetallePago
from apps.payments.choices import MetodoPago
from apps.appointments.models import DetalleCita
from bootstrap_modal_forms.generic import BSModalReadView


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
        pago = self.get_object()
        context.update(
            {
                "object": pago,
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
    ]

    ordering_fields = {
        "0": "nombre_servicio",
        "1": "precio_servicio",
        "2": "cantidad_servicios",
        "3": "total_servicio",
        "4": "descuento",
        "5": "precio_acordado",
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

    @staticmethod
    def additional_data(queryset):
        additional_data = queryset.aggregate(
            total_price=Sum("precio_acordado"),
        )
        total_price = additional_data.get("total_price") or 0
        return {
            "total_price_formatted": format_currency(total_price),
            "total_price": total_price,
        }


class PaymentDetailListView(BaseListViewAjax):
    model = DetallePago
    include_options_column = False

    field_list = [
        "pk",
        "fecha_pago",
        "metodo_pago",
        "referencia_pago",
        "monto_pago",
    ]

    ordering_fields = {
        "0": "fecha_pago",
        "1": "metodo_pago",
        "2": "referencia_pago",
        "3": "monto_pago",
    }

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                pago_id=self.kwargs.get("pk"),
            )
        )

    def get_values(self, queryset):
        values = super().get_values(queryset)
        payment_method_display = dict(MetodoPago.CHOICES)
        for item in values:
            item.update(
                {
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

    @staticmethod
    def additional_data(queryset):
        additional_data = queryset.aggregate(total_paid=Sum("monto_pago"))
        total_paid = additional_data.get("total_paid") or 0
        return {
            "total_paid_formatted": format_currency(total_paid),
            "total_paid": total_paid,
        }


# endregion
"""========================================================================="""
