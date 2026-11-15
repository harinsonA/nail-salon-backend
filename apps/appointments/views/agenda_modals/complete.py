from bootstrap_modal_forms.forms import BSModalModelForm
from bootstrap_modal_forms.generic import BSModalUpdateView
from django import forms
from django.http import JsonResponse
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.appointments.access import AppointmentAccessMixin
from apps.appointments.engine import AppointmentCompletion, AppointmentRuleError
from apps.appointments.engine.messages import FULL_PAYMENT_LABEL
from apps.appointments.models import Cita
from apps.appointments.panel import AppointmentPanel, person_name
from apps.appointments.views.agenda_modals.common import AgendaBaseModalView
from apps.common.form_classes import (
    FORM_CONTROL_CLASS,
    FORM_CONTROL_TEXTAREA_CLASS,
    FORM_SELECT_CLASS,
)
from apps.common.form_fields import MoneyField, NoteField
from apps.common.utils.currency import Money
from apps.common.utils.utils import get_errors_to_response
from apps.payments.choices import MetodoPago

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
    down_payment = MoneyField(label="Monto abonado", initial=0, required=False)
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
        completion = form.completion
        services, subtotal, discounts, _ = AppointmentPanel(
            self.object, self.request.user
        ).services()
        total = completion.remaining
        advance = completion.advance_part()
        context.update(
            {
                "modal_url": self.request.path,
                "services": services,
                "subtotal": Money.format(subtotal),
                "discounts": Money.format(-discounts) if discounts else Money.format(0),
                "services_total": Money.format(completion.services_total),
                "prepaid": Money.format(-completion.prepaid) if completion.prepaid else "",
                "advance": Money.format(-advance) if advance else "",
                "reservation": completion.reservation_card(),
                "settled_hint": completion.settled_hint(),
                "total": Money.format(total),
                "total_value": int(total),
                "complete_config": {
                    "total": int(total),
                    "prepaid": int(completion.prepaid),
                    "servicesTotal": int(completion.services_total),
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

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        form.completion.complete(
            self.request.user,
            amount=form.amount_paid_now(),
            method=cleaned_data.get("payment_method", MetodoPago.EFECTIVO),
            reference=cleaned_data.get("payment_reference"),
            notes=cleaned_data.get("observations", ""),
        )
        message = self.__get_message_success()
        return JsonResponse({"message": message}, status=200)

    def form_invalid(self, form):
        errors = get_errors_to_response(form.errors)
        return JsonResponse({"errors": errors}, status=HTTP_400_BAD_REQUEST)


# endregion
"""========================================================================="""
