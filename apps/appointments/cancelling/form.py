import json

from django import forms

from apps.appointments.engine import AppointmentRuleError
from apps.appointments.engine.messages import REFUNDS_INVALID


class CancelRefundsForm(forms.Form):
    refunds = forms.CharField(required=False)

    def __init__(self, *args, engine, **kwargs):
        super().__init__(*args, **kwargs)
        self.engine = engine

    def clean_refunds(self):
        try:
            value = json.loads(self.cleaned_data.get("refunds") or "[]")
            return self.engine.clean_refunds(value)
        except json.JSONDecodeError as error:
            raise forms.ValidationError(REFUNDS_INVALID) from error
        except AppointmentRuleError as error:
            raise forms.ValidationError(error.message) from error
