from datetime import datetime
from decimal import Decimal

from bootstrap_modal_forms.forms import BSModalModelForm
from django import forms
from django.db.models import Sum
from django.http import JsonResponse
from django.utils import timezone
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST

from apps.common.form_classes import (
    FORM_CONTROL_CLASS,
    FORM_CONTROL_TEXTAREA_CLASS,
    FORM_SELECT_CLASS,
)
from apps.common.form_fields import NoteField
from apps.common.utils.currency import format_money
from apps.common.utils.dates import format_date_time
from apps.common.utils.text import user_display_name
from apps.common.utils.utils import get_errors_to_response
from apps.payments.choices import EstadoPago, MetodoPago
from apps.payments.models import DetallePago, Pago

"""========================================================================="""
# region ........ Constants


DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M"
AMOUNT_REQUIRED = "El monto debe ser mayor a $0."
AMOUNT_TOO_HIGH = "No puede superar el saldo pendiente ({balance})."
REFERENCE_REQUIRED = "Ingresa la referencia del pago."
NO_BALANCE = "Este pago ya no tiene saldo pendiente."
METHOD_LABELS = dict(MetodoPago.CHOICES)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class AddPaymentForm(BSModalModelForm):
    full_payment = forms.BooleanField(
        label="Pagar el saldo completo",
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "role": "switch"}),
    )
    down_payment = forms.IntegerField(
        label="Monto abonado",
        min_value=0,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "min": "1",
                "step": "500",
                "inputmode": "numeric",
            }
        ),
    )
    payment_method = forms.ChoiceField(
        label="Método",
        choices=MetodoPago.CHOICES,
        initial=MetodoPago.EFECTIVO,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    payment_reference = forms.CharField(
        label="Referencia",
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "N° de comprobante o transferencia",
            }
        ),
    )
    payment_date = forms.DateField(
        label="Fecha",
        input_formats=[DATE_FORMAT],
        widget=forms.DateInput(
            format=DATE_FORMAT,
            attrs={"type": "date", "class": FORM_CONTROL_CLASS},
        ),
    )
    payment_time = forms.TimeField(
        label="Hora",
        input_formats=[TIME_FORMAT],
        widget=forms.TimeInput(
            format=TIME_FORMAT,
            attrs={"type": "time", "step": "60", "class": FORM_CONTROL_CLASS},
        ),
    )
    observations = NoteField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "class": FORM_CONTROL_TEXTAREA_CLASS,
                "placeholder": "Ej.: dejó el resto para el próximo viernes",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        self.pending_payment_amount = kwargs.pop("pending_payment_amount", 0)
        super().__init__(*args, **kwargs)
        now = timezone.localtime()
        self.fields["payment_date"].initial = now.date()
        self.fields["payment_time"].initial = now.strftime(TIME_FORMAT)

    class Meta:
        model = Pago
        fields = []

    def save(self, commit=False):
        return self.instance

    def clean_down_payment(self):
        if self.pending_payment_amount <= 0:
            raise forms.ValidationError(NO_BALANCE)
        if self.cleaned_data.get("full_payment"):
            return self.pending_payment_amount
        down_payment = self.cleaned_data.get("down_payment")
        if not down_payment:
            raise forms.ValidationError(AMOUNT_REQUIRED)
        if down_payment > self.pending_payment_amount:
            balance = format_money(self.pending_payment_amount)
            raise forms.ValidationError(AMOUNT_TOO_HIGH.format(balance=balance))
        return down_payment

    def clean_payment_reference(self):
        reference = (self.cleaned_data.get("payment_reference") or "").strip()
        method = self.cleaned_data.get("payment_method")
        if method and method != MetodoPago.EFECTIVO and not reference:
            raise forms.ValidationError(REFERENCE_REQUIRED)
        return reference


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Mixins


class PaymentInstallmentMixin:
    template_name = "debtors/_add_payment.html"
    model = Pago
    form_class = AddPaymentForm

    def installments(self):
        return self.object.detalles_pago.select_related("registrado_por").order_by(
            "fecha_pago", "pk"
        )

    def paid_amount(self):
        total = self.object.detalles_pago.aggregate(total=Sum("monto_pago"))["total"]
        return total or Decimal("0")

    def pending_amount(self):
        return max(Decimal("0"), self.object.monto_total_cita - self.paid_amount())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["pending_payment_amount"] = int(self.pending_amount())
        return kwargs

    def attended_by(self):
        payment = self.object
        if payment.atendido_por_id:
            return user_display_name(payment.atendido_por)
        return payment.atendido_por_nombre or "—"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment = self.object
        paid = self.paid_amount()
        pending = self.pending_amount()
        context.update(
            {
                "modal_url": self.request.path,
                "cliente_nombre": payment.cliente_nombre,
                "fecha_cita": format_date_time(payment.fecha_cita)
                if payment.fecha_cita
                else "—",
                "atendido_por": self.attended_by(),
                "total": format_money(payment.monto_total_cita),
                "pagado": format_money(paid),
                "saldo": format_money(pending),
                "payment_config": {
                    "total": int(payment.monto_total_cita),
                    "paid": int(paid),
                    "balance": int(pending),
                },
                "abonos": [
                    {
                        "when": format_date_time(item.fecha_pago),
                        "method": METHOD_LABELS.get(item.metodo_pago, item.metodo_pago),
                        "by": user_display_name(item.registrado_por)
                        if item.registrado_por
                        else "—",
                        "amount": format_money(item.monto_pago),
                    }
                    for item in self.installments()
                ],
            }
        )
        return context

    def save_installment(self, data):
        payment_date = timezone.make_aware(
            datetime.combine(data["payment_date"], data["payment_time"])
        )
        method = data["payment_method"]
        DetallePago.objects.create(
            pago=self.object,
            fecha_pago=payment_date,
            monto_pago=data["down_payment"],
            metodo_pago=method,
            referencia_pago=data["payment_reference"]
            if method != MetodoPago.EFECTIVO
            else None,
            notas_detalle=data["observations"],
            registrado_por=self.request.user,
        )

    def update_payment_status(self):
        if self.paid_amount() < self.object.monto_total_cita:
            return False
        self.object.estado_pago = EstadoPago.COMPLETADO
        self.object.fecha_pago_completado = timezone.now()
        self.object.save()
        return True

    def success_message(self, fully_paid):
        payment = self.object
        when = format_date_time(payment.fecha_cita) if payment.fecha_cita else "—"
        if fully_paid:
            return f"La deuda de {payment.cliente_nombre} para la cita del {when} fue pagada completamente."
        return f"Abono registrado para {payment.cliente_nombre}, cita del {when}."

    def form_valid(self, form):
        self.save_installment(form.cleaned_data)
        fully_paid = self.update_payment_status()
        return JsonResponse(
            {"message": self.success_message(fully_paid)}, status=HTTP_200_OK
        )

    def form_invalid(self, form):
        errors = get_errors_to_response(form.errors)
        return JsonResponse({"errors": errors}, status=HTTP_400_BAD_REQUEST)


# endregion
"""========================================================================="""
