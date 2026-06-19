from django import forms

from apps.common.custom_time_fields import CustomDateField
from dashboard.services import periods


class DashboardFilterForm(forms.Form):
    """Filtro global del dashboard.

    Dos modos excluyentes:
      - `months`: presets de "últimos N meses" (3 / 6 / 12 …).
      - `date_from` + `date_to`: rango personalizado.

    Si llega un rango válido, manda; si no, se usa `months` (default 6).
    Resuelve a un `periods.Period` que consumen las funciones de metrics.
    """

    DEFAULT_MONTHS = 6
    MIN_MONTHS = 1
    MAX_MONTHS = 36

    months = forms.IntegerField(
        required=False,
        min_value=MIN_MONTHS,
        max_value=MAX_MONTHS,
    )
    date_from = CustomDateField(required=False)
    date_to = CustomDateField(required=False)

    def get_period(self):
        """Resuelve el filtro a un Period, cayendo al default ante datos inválidos."""
        if not self.is_valid():
            return periods.last_months(self.DEFAULT_MONTHS)

        date_from = self.cleaned_data.get("date_from")
        date_to = self.cleaned_data.get("date_to")
        if date_from and date_to:
            return periods.between(date_from, date_to)

        months = self.cleaned_data.get("months") or self.DEFAULT_MONTHS
        return periods.last_months(months)
