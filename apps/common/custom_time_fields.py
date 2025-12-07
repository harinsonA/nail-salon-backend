from datetime import timedelta, datetime
from calendar import monthrange
from django import forms
from django.db.models import TextChoices

from .widgets import MonthPickerWidget, DatePickerWidget


class MonthChoiceField(TextChoices):
    JANUARY = "Enero", "1"
    FEBRUARY = "Febrero", "2"
    MARCH = "Marzo", "3"
    APRIL = "Abril", "4"
    MAY = "Mayo", "5"
    JUNE = "Junio", "6"
    JULY = "Julio", "7"
    AUGUST = "Agosto", "8"
    SEPTEMBER = "Septiembre", "9"
    OCTOBER = "Octubre", "10"
    NOVEMBER = "Noviembre", "11"
    DECEMBER = "Diciembre", "12"


"""========================================================================="""
# region ........ Minutes


class DurationInMinutesField(forms.IntegerField):
    def to_python(self, value):
        value = super().to_python(value)
        if value is not None:
            return timedelta(minutes=value)
        return value


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Dates


class CustomDateField(forms.CharField):
    widget = DatePickerWidget

    def to_python(self, value):
        value = super().to_python(value)
        if not value:
            return None
        print(value)
        return value


class CustomMonthField(forms.CharField):
    widget = MonthPickerWidget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.months = dict(MonthChoiceField.choices)

    def __get_formatted_month(
        self, day: int, month: str, year: str, is_last_day: bool = False
    ) -> datetime:
        date_time = {
            "hour": 23 if is_last_day else 0,
            "minute": 59 if is_last_day else 0,
        }
        return datetime(
            day=day,
            month=int(self.months.get(month, "1")),
            year=int(year),
            **date_time,
        )

    def to_python(self, value):
        value = super().to_python(value)
        if not value:
            return None

        period_selected = value.strip().replace(" ", "-")
        month, year = period_selected.split("-")
        _, last_day = monthrange(int(year), int(self.months.get(month, "1")))
        first_day = self.__get_formatted_month(1, month, year)
        last_day = self.__get_formatted_month(last_day, month, year, is_last_day=True)
        return [first_day, last_day]


# endregion
"""========================================================================="""
