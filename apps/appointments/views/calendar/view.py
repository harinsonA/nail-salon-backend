import calendar
from datetime import date
from django import forms
from django.views.generic import TemplateView
from django.urls import reverse_lazy
from apps.appointments.models.agenda import Cita
from apps.common.base_list_view_ajax import BaseListViewAjax
from apps.common.custom_time_fields import CustomMonthField


"""========================================================================="""
# region ........ Constants


WEEKDAYS = {
    1: {
        "id": "monday",
        "name": "Lunes",
    },
    2: {
        "id": "tuesday",
        "name": "Martes",
    },
    3: {
        "id": "wednesday",
        "name": "Miércoles",
    },
    4: {
        "id": "thursday",
        "name": "Jueves",
    },
    5: {
        "id": "friday",
        "name": "Viernes",
    },
    6: {
        "id": "saturday",
        "name": "Sábado",
    },
    7: {
        "id": "sunday",
        "name": "Domingo",
    },
}


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Form


class CalendarFilterForm(forms.Form):
    months = CustomMonthField(
        label="Mes",
        required=False,
    )

    def clean(self):
        cleaned_data = super().clean()
        first_day, last_day = cleaned_data.get("months", (None, None))
        return {
            "fecha_agenda__gte": first_day,
            "fecha_agenda__lte": last_day,
        }


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Views


class CalendarView(TemplateView):
    template_name = "calendar/list.html"

    @staticmethod
    def get_initial_month() -> str:
        today = date.today()
        return f"{today.strftime('%B %Y')}".capitalize()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "filter_form": CalendarFilterForm(
                    initial={"months": self.get_initial_month()}
                ),
                "url_calendar_list": reverse_lazy("calendar_list"),
            }
        )
        return context


class CalendarListView(BaseListViewAjax):
    model = Cita
    filter_form_class = CalendarFilterForm

    @staticmethod
    def get_detailed_weeks(year, month) -> dict:
        _calendar = calendar.Calendar(firstweekday=0)
        weeks = {}

        for week in _calendar.monthdatescalendar(year, month):
            for dt in week:
                week_number = dt.isocalendar()[1]
                if week_number not in weeks:
                    weeks[week_number] = []
                weeks[week_number].append(
                    {
                        "day": dt.day,
                        "date": dt,
                        "in_month": dt.month == month,
                    }
                )
        return weeks

    @staticmethod
    def get_calendar_data(weeks: dict) -> list:
        data = []
        _today = date.today()
        for week_number, days in weeks.items():
            base_week = {"week_id": week_number}
            for day in days:
                _date = day["date"]
                day_id = _date.isoweekday()
                week_day_info = WEEKDAYS.get(day_id)
                if not week_day_info:
                    continue
                base_week[week_day_info["id"]] = {
                    "day": day["day"],
                    "in_month": day["in_month"],
                    "is_today": _date == _today,
                    "calendar_appointments_url": reverse_lazy(
                        "calendar_appointments",
                        kwargs={"date": _date.strftime("%Y-%m-%d")},
                    ),
                }
            data.append(base_week)
        return data

    def get_context_data(self, **kwargs):
        _filters = self.get_filters()
        _date = _filters.get("fecha_agenda__gte")
        year = _date.year
        month = _date.month
        weeks = self.get_detailed_weeks(year, month)
        calendar_data = self.get_calendar_data(weeks)
        return {
            "data": calendar_data,
            "recordsTotal": len(calendar_data),
            "recordsFiltered": len(calendar_data),
        }


# endregion
"""========================================================================="""
