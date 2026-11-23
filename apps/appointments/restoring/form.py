import json

from django import forms

from apps.appointments.engine import AppointmentRuleError
from apps.appointments.engine.messages import RESTORED_INVALID


class RestorePrepaidForm(forms.Form):
    restored = forms.CharField(required=False)

    def __init__(self, *args, engine, **kwargs):
        super().__init__(*args, **kwargs)
        self.engine = engine

    def clean_restored(self):
        try:
            value = json.loads(self.cleaned_data.get("restored") or "[]")
            return self.engine.clean_restored(value)
        except json.JSONDecodeError as error:
            raise forms.ValidationError(RESTORED_INVALID) from error
        except AppointmentRuleError as error:
            raise forms.ValidationError(error.message) from error
