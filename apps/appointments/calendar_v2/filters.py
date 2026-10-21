from django import forms

from apps.common.form_fields import AlphabeticField

"""========================================================================="""
# region ........ Constants


MAX_RANGE_DAYS = 42
VIEW_MONTH = "mes"


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class CalendarFilterForm(forms.Form):
    vista = forms.ChoiceField(choices=[(VIEW_MONTH, "Mes")])
    desde = forms.DateField(input_formats=["%Y-%m-%d"])
    hasta = forms.DateField(input_formats=["%Y-%m-%d"])
    buscar = AlphabeticField(label="Búsqueda", required=False, max_length=100)

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get("desde")
        end = cleaned_data.get("hasta")
        if start and end:
            if end < start:
                raise forms.ValidationError("La fecha final no puede ser anterior a la inicial.")
            if (end - start).days >= MAX_RANGE_DAYS:
                raise forms.ValidationError(f"El rango no puede superar {MAX_RANGE_DAYS} días.")
        return cleaned_data


# endregion
"""========================================================================="""
