from django import forms


class DashboardFilterForm(forms.Form):
    """Filtros del dashboard. Por ahora solo `months`; preparado para añadir
    `date_from`/`date_to` sin cambiar la firma de los endpoints."""

    DEFAULT_MONTHS = 6
    MIN_MONTHS = 1
    MAX_MONTHS = 24

    months = forms.IntegerField(
        required=False,
        min_value=MIN_MONTHS,
        max_value=MAX_MONTHS,
    )

    def get_months(self):
        """Número de meses válido. Cae al default si falta o viene mal."""
        if self.is_valid():
            return self.cleaned_data.get("months") or self.DEFAULT_MONTHS
        return self.DEFAULT_MONTHS
