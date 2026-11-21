import json

from bootstrap_modal_forms.forms import BSModalForm
from django import forms
from django.contrib.auth import get_user_model

from apps.appointments.engine import AppointmentDraft, AppointmentRuleError
from apps.appointments.engine.messages import (
    ADVANCES_INVALID,
    RESERVATION_INVALID,
    SERVICES_INVALID,
)
from apps.clients.models import Cliente
from apps.common.form_classes import (
    FORM_CONTROL_CLASS,
    FORM_CONTROL_TEXTAREA_CLASS,
    FORM_SELECT2_CLASS,
)
from apps.common.form_fields import NoteField
from apps.common.utils.text import user_display_name

User = get_user_model()

DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M"


def initial_from(appointment):
    return {
        "client": appointment.cliente,
        "assigned_to": appointment.asignado_a,
        "date": appointment.fecha_agenda,
        "time": appointment.hora_agenda,
        "observations": appointment.observaciones or "",
    }


class StaffChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return user_display_name(obj)


class AppointmentForm(BSModalForm):
    client = forms.ModelChoiceField(
        queryset=Cliente.objects.none(),
        label="Cliente",
        empty_label="Selecciona un cliente",
        widget=forms.Select(attrs={"class": FORM_SELECT2_CLASS}),
    )
    assigned_to = StaffChoiceField(
        queryset=User.objects.none(),
        label="Asignada a",
        empty_label=None,
        widget=forms.Select(attrs={"class": FORM_SELECT2_CLASS}),
    )
    date = forms.DateField(
        label="Fecha",
        input_formats=[DATE_FORMAT],
        widget=forms.DateInput(
            format=DATE_FORMAT,
            attrs={"type": "date", "class": FORM_CONTROL_CLASS},
        ),
    )
    time = forms.TimeField(
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
                "placeholder": "Alergias, preferencias, diseño que quiere…",
            }
        ),
    )
    services = forms.CharField(required=False, widget=forms.HiddenInput)
    advances = forms.CharField(required=False, widget=forms.HiddenInput)
    reservation = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance = instance
        self.draft = AppointmentDraft(self.request.user, instance)
        if instance:
            self.initial = {**initial_from(instance), **self.initial}
        current_client = instance.cliente if instance else None
        current_staff = instance.asignado_a if instance else None
        assignment = self.draft.assignment
        self.fields["client"].queryset = assignment.clients(current_client)
        self.fields["assigned_to"].queryset = assignment.staff(current_staff)
        if assignment.collaborator:
            self.fields["assigned_to"].disabled = True
            self.fields["assigned_to"].initial = self.request.user

    @staticmethod
    def decode(raw, message):
        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            raise forms.ValidationError(message) from error

    @staticmethod
    def apply(rule, value):
        try:
            return rule(value)
        except AppointmentRuleError as error:
            raise forms.ValidationError(error.message) from error

    def clean_services(self):
        lines = self.decode(self.cleaned_data.get("services") or "[]", SERVICES_INVALID)
        return self.apply(self.draft.services.clean, lines)

    def clean_assigned_to(self):
        return self.draft.assignment.resolve(self.cleaned_data["assigned_to"])

    def clean_advances(self):
        advances = self.decode(self.cleaned_data.get("advances") or "[]", ADVANCES_INVALID)
        return self.apply(self.draft.advances.clean, advances)

    def clean_reservation(self):
        raw = self.cleaned_data.get("reservation")
        if not self.draft.reservation.available or not raw:
            return {}
        data = self.decode(raw, RESERVATION_INVALID)
        return self.apply(self.draft.reservation_change.clean, data)

    def clean(self):
        cleaned_data = super().clean()
        lines = cleaned_data.get("services")
        if not lines or "advances" not in cleaned_data or "reservation" not in cleaned_data:
            return cleaned_data
        error = self.draft.limit.check(
            lines, cleaned_data["advances"], cleaned_data["reservation"]
        )
        if error:
            self.add_error(error.field, error.message)
        return cleaned_data
