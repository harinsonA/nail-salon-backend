from bootstrap_modal_forms.forms import BSModalModelForm
from django import forms

from apps.appointments.engine import AppointmentCompletion, AppointmentRuleError
from apps.appointments.engine.messages import FULL_PAYMENT_LABEL, REFERENCE_MAX_LENGTH
from apps.appointments.models import Cita
from apps.common.form_classes import (
    FORM_CONTROL_CLASS,
    FORM_CONTROL_TEXTAREA_CLASS,
    FORM_SELECT_CLASS,
)
from apps.common.form_fields import MoneyField, NoteField
from apps.payments.choices import MetodoPago


class CompletionForm(BSModalModelForm):
    full_payment = forms.BooleanField(
        label=FULL_PAYMENT_LABEL,
        required=False,
        initial=True,
        widget=forms.CheckboxInput(
            attrs={"class": "form-check-input", "role": "switch"}
        ),
    )
    down_payment = MoneyField(label="Monto abonado", initial=0, required=False)
    payment_method = forms.ChoiceField(
        label="Método",
        choices=MetodoPago.CHOICES,
        initial=MetodoPago.EFECTIVO,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    payment_reference = forms.CharField(
        label="Referencia",
        max_length=REFERENCE_MAX_LENGTH,
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
        self.completion = AppointmentCompletion(self.instance)
        self.fields["full_payment"].label = self.completion.full_payment_label()

    class Meta:
        model = Cita
        fields = []

    def save(self, commit=False):
        return self.instance

    def clean_down_payment(self):
        try:
            return self.completion.clean_amount(
                self.cleaned_data.get("full_payment"),
                self.cleaned_data.get("down_payment"),
            )
        except AppointmentRuleError as error:
            raise forms.ValidationError(error.message) from error

    def amount_paid_now(self):
        return self.completion.amount_paid_now(
            self.cleaned_data.get("full_payment"),
            self.cleaned_data.get("down_payment"),
        )

    def complete(self, user):
        cleaned_data = self.cleaned_data
        return self.completion.complete(
            user,
            amount=self.amount_paid_now(),
            method=cleaned_data.get("payment_method") or MetodoPago.EFECTIVO,
            reference=cleaned_data.get("payment_reference"),
            notes=cleaned_data.get("observations", ""),
        )
