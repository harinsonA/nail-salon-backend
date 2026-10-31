from bootstrap_modal_forms.forms import BSModalModelForm
from bootstrap_modal_forms.generic import BSModalUpdateView
from django import forms
from django.db import transaction
from django.http import JsonResponse
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.appointments.access import AppointmentAccessMixin
from apps.appointments.models import Cita
from apps.appointments.panel import AppointmentPanel, person_name
from apps.appointments.views.agenda_modals.common import AgendaBaseModalView
from apps.common.form_classes import (
    FORM_CONTROL_CLASS,
    FORM_CONTROL_TEXTAREA_CLASS,
    FORM_SELECT_CLASS,
)
from apps.common.form_fields import NoteField
from apps.common.utils.currency import Money
from apps.common.utils.utils import CommonCleaner, get_errors_to_response
from apps.payments.accounting import (
    ZERO,
    AppointmentLedger,
    AppointmentPaymentService,
    PaymentAccount,
    PaymentHeader,
)
from apps.payments.choices import MetodoPago

"""========================================================================="""
# region ........ Constants


FULL_PAYMENT_LABEL = "Paga el total ahora"
BALANCE_PAYMENT_LABEL = "Paga el saldo ahora"
AMOUNT_TOO_HIGH = 'Si paga {total} o más, activa "{label}".'
PREPAID_TOO_HIGH = (
    "Lo pagado antes ({paid}) supera el total de los servicios ({total}). "
    "Edita la cita antes de completarla."
)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class AgendaConfirmationForm(BSModalModelForm):
    full_payment = forms.BooleanField(
        label=FULL_PAYMENT_LABEL,
        required=False,
        initial=True,
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "role": "switch"}
        ),
    )
    down_payment = forms.IntegerField(
        label="Monto abonado",
        initial=0,
        required=False,
        widget=forms.NumberInput(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "min": "0",
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
    observations = NoteField(
        label="Observaciones",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 2,
                "class": FORM_CONTROL_TEXTAREA_CLASS,
                "placeholder": "Ej.: pagará el resto la próxima semana",
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.payment = AppointmentLedger.for_appointment(self.instance).payment
        self.services_total = PaymentHeader(self.instance).services_total()
        self.prepaid = PaymentAccount(self.payment).credit() if self.payment else ZERO
        self.remaining_payment_value = max(ZERO, self.services_total - self.prepaid)
        if self.prepaid:
            self.fields["full_payment"].label = BALANCE_PAYMENT_LABEL

    class Meta:
        model = Cita
        fields = []

    def save(self, commit=False):
        return self.instance

    def clean_down_payment(self):
        down_payment = self.cleaned_data.get("down_payment")
        if self.prepaid > self.services_total:
            raise forms.ValidationError(
                PREPAID_TOO_HIGH.format(
                    paid=Money.format(self.prepaid),
                    total=Money.format(self.services_total),
                )
            )
        if not self.remaining_payment_value:
            return 0
        if self.cleaned_data.get("full_payment"):
            return down_payment
        result = CommonCleaner.clean_amount_field("monto abonado", down_payment)
        if result.is_err():
            raise forms.ValidationError(result.err_value)
        down_payment = result.ok_value
        if down_payment >= self.remaining_payment_value:
            total = Money.format(self.remaining_payment_value)
            label = self.fields["full_payment"].label
            raise forms.ValidationError(AMOUNT_TOO_HIGH.format(total=total, label=label))
        return down_payment

    def amount_paid_now(self):
        if not self.remaining_payment_value:
            return ZERO
        if self.cleaned_data.get("full_payment"):
            return self.remaining_payment_value
        return self.cleaned_data.get("down_payment") or ZERO


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class AgendaConfirmationModal(
    AppointmentAccessMixin, AgendaBaseModalView, BSModalUpdateView
):
    template_name = "appointments/agenda_confirmation_modal.html"
    model = Cita
    form_class = AgendaConfirmationForm

    def get_queryset(self):
        return super().get_queryset().filter(estado=Cita.EstadoChoices.PENDIENTE)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = context["form"]
        services, subtotal, discounts, _ = AppointmentPanel(
            self.object, self.request.user
        ).services()
        total = form.remaining_payment_value
        context.update(
            {
                "modal_url": self.request.path,
                "services": services,
                "subtotal": Money.format(subtotal),
                "discounts": Money.format(-discounts) if discounts else Money.format(0),
                "services_total": Money.format(form.services_total),
                "prepaid": Money.format(-form.prepaid) if form.prepaid else "",
                "total": Money.format(total),
                "total_value": int(total),
                "complete_config": {
                    "total": int(total),
                    "prepaid": int(form.prepaid),
                    "servicesTotal": int(form.services_total),
                    "fullLabel": form.fields["full_payment"].label,
                },
                "attended_by": person_name(self.request.user, self.request.user),
            }
        )
        return context

    def __get_message_success(self) -> str:
        return (
            "La cita de %(client_name)s para el día %(date)s a las %(time)s fue "
            "completada."
        ) % {
            "client_name": self._get_client_full_name(self.object),
            "date": self._get_date_formatted(self.object),
            "time": self._get_time_formatted(self.object),
        }

    @transaction.atomic
    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        AppointmentPaymentService(self.object, self.request.user).complete(
            amount=form.amount_paid_now(),
            method=cleaned_data.get("payment_method", MetodoPago.EFECTIVO),
            reference=cleaned_data.get("payment_reference"),
            notes=cleaned_data.get("observations", ""),
        )
        self.object.estado = Cita.EstadoChoices.COMPLETADA
        self.object.save()
        message = self.__get_message_success()
        return JsonResponse({"message": message}, status=200)

    def form_invalid(self, form):
        errors = get_errors_to_response(form.errors)
        return JsonResponse({"errors": errors}, status=HTTP_400_BAD_REQUEST)


# endregion
"""========================================================================="""
