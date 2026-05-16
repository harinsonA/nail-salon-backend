from django import forms
from datetime import datetime
from decimal import Decimal

from django.db.models import Sum
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_200_OK
from apps.common.utils.currency import format_currency
from apps.common.utils.utils import get_errors_to_response
from apps.common.custom_time_fields import CustomDateField
from apps.common.form_classes import (
    FORM_CONTROL_CLASS,
    FORM_CONTROL_TEXTAREA_CLASS,
    FORM_SELECT_CLASS,
)
from apps.common.views.base_views import ProtectedView
from apps.payments.models import Pago, DetallePago
from apps.payments.choices import MetodoPago, EstadoPago
from bootstrap_modal_forms.forms import BSModalModelForm
from bootstrap_modal_forms.generic import BSModalUpdateView


"""========================================================================="""
# region ........ Forms


class AddPaymentForm(BSModalModelForm):
    payment_method = forms.ChoiceField(
        label="Método de pago",
        choices=MetodoPago.CHOICES,
        required=False,
        initial=MetodoPago.EFECTIVO,
        widget=forms.Select(
            attrs={
                "class": FORM_SELECT_CLASS,
            }
        ),
    )
    payment_reference = forms.CharField(
        label="Referencia de pago",
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "Nro. de recibo, transacción, etc.",
            }
        ),
    )
    full_payment = forms.BooleanField(
        label="Pago completo",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
            }
        ),
    )
    remaining_payment = forms.IntegerField(
        label="Restante",
        initial=0,
        min_value=0,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "min": "0",
                "placeholder": "0",
                "readonly": "readonly",
            }
        ),
    )
    down_payment = forms.IntegerField(
        label="Monto abonado",
        initial=0,
        min_value=0,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "min": "0",
                "placeholder": "0",
            }
        ),
    )
    payment_date = CustomDateField(
        required=True,
        label="Fecha del pago",
    )
    payment_time = forms.TimeField(
        required=True,
        label="Hora del pago",
        widget=forms.TimeInput(
            attrs={
                "type": "time",
                "class": FORM_CONTROL_CLASS,
                "format": "%H:%M",
            }
        ),
    )
    observations = forms.CharField(
        required=False,
        label="Observaciones",
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "class": FORM_CONTROL_TEXTAREA_CLASS,
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.pending_payment_amount = kwargs.pop("pending_payment_amount", 0)
        super().__init__(*args, **kwargs)
        now = timezone.localtime(timezone.now())
        self.fields["payment_date"].initial = now.strftime("%d/%m/%Y")
        self.fields["payment_time"].initial = now.strftime("%H:%M")

    class Meta:
        model = Pago
        fields = []

    def save(self, commit=False):
        return self.instance

    def clean_down_payment(self):
        full_payment = self.cleaned_data.get("full_payment", False)
        down_payment = self.cleaned_data.get("down_payment", 0)
        if full_payment:
            return self.pending_payment_amount
        if not full_payment and not down_payment:
            raise forms.ValidationError("Debe ingresar un monto a abonar mayor a 0.")
        if down_payment and down_payment >= self.pending_payment_amount:
            raise forms.ValidationError(
                "El monto abonado no puede ser mayor o igual al saldo pendiente."
            )
        return down_payment

    def clean_payment_date(self):
        payment_date = self.cleaned_data.get("payment_date")
        if not payment_date:
            raise forms.ValidationError("La fecha del pago es obligatoria.")
        return payment_date

    def clean_payment_time(self):
        payment_time = self.cleaned_data.get("payment_time")
        if not payment_time:
            raise forms.ValidationError("La hora del pago es obligatoria.")
        return payment_time

    def clean_payment_reference(self):
        payment_reference = self.cleaned_data.get("payment_reference", "")
        payment_method = self.cleaned_data.get("payment_method", "")

        is_cash = payment_method == MetodoPago.EFECTIVO
        has_no_reference = not payment_reference or not payment_reference.strip()

        if not is_cash and has_no_reference:
            raise forms.ValidationError("Debe ingresar una referencia de pago.")

        return payment_reference.strip()


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class AddPaymentModalView(ProtectedView, BSModalUpdateView):
    template_name = "debtors/_add_payment.html"
    model = Pago
    form_class = AddPaymentForm
    pending_payment_amount = 0

    def get_initial(self):
        total_paid = self.object.detalles_pago.aggregate(
            total=Sum("monto_pago"),
        )["total"] or Decimal("0")
        self.pending_payment_amount = self.object.monto_total_cita - total_paid
        return {
            "remaining_payment": int(self.pending_payment_amount),
        }

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pending_payment_amount"] = int(self.pending_payment_amount)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pago = self.object
        context.update(
            {
                "cliente_nombre": pago.cliente_nombre,
                "fecha_cita": pago.fecha_cita.strftime("%d/%m/%Y %H:%M")
                if pago.fecha_cita
                else "-- --",
                "monto_total_cita_formatted": format_currency(pago.monto_total_cita),
                "saldo_pendiente_formatted": format_currency(
                    self.pending_payment_amount
                ),
                "saldo_pendiente": int(self.pending_payment_amount),
            }
        )
        return context

    def __save_payment_detail(
        self,
        cleaned_data: dict,
    ) -> None:
        full_payment = cleaned_data.get("full_payment", False)
        amount_paid = (
            self.pending_payment_amount
            if full_payment
            else cleaned_data.get("down_payment", 0)
        )
        payment_date = cleaned_data.get("payment_date")
        payment_time = cleaned_data.get("payment_time")
        fecha_pago = timezone.make_aware(datetime.combine(payment_date, payment_time))
        payment_method = cleaned_data.get("payment_method", MetodoPago.EFECTIVO)
        observation = cleaned_data.get("observations", "")
        payment_detail = DetallePago(
            pago=self.object,
            fecha_pago=fecha_pago,
            monto_pago=amount_paid,
            metodo_pago=payment_method,
            notas_detalle=observation,
        )
        if payment_method != MetodoPago.EFECTIVO:
            payment_detail.referencia_pago = cleaned_data.get("payment_reference", "")
        payment_detail.save()

    def __update_payment_status(self) -> bool:
        total_paid = self.object.detalles_pago.aggregate(
            total=Sum("monto_pago"),
        )["total"] or Decimal("0")
        if total_paid >= self.object.monto_total_cita:
            self.object.estado_pago = EstadoPago.COMPLETADO
            self.object.fecha_pago_completado = timezone.now()
            self.object.save()
            return True
        return False

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        self.__save_payment_detail(cleaned_data)
        is_fully_paid = self.__update_payment_status()
        pago = self.object
        cliente = pago.cliente_nombre
        fecha = (
            pago.fecha_cita.strftime("%d/%m/%Y %H:%M") if pago.fecha_cita else "-- --"
        )
        if is_fully_paid:
            message = (
                "La deuda de %(cliente)s para la cita del %(fecha)s "
                "fue pagada completamente."
            ) % {"cliente": cliente, "fecha": fecha}
        else:
            message = (
                "Pago registrado exitosamente para %(cliente)s, cita del %(fecha)s."
            ) % {"cliente": cliente, "fecha": fecha}
        return JsonResponse({"message": message}, status=HTTP_200_OK)

    def form_invalid(self, form):
        errors = get_errors_to_response(form.errors)
        return JsonResponse({"errors": errors}, status=HTTP_400_BAD_REQUEST)


# endregion
"""========================================================================="""
