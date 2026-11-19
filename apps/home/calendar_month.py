from datetime import date

MONTH_NAMES = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
    "Octubre",
    "Noviembre",
    "Diciembre",
]


class CalendarMonth:
    def __init__(self, day):
        self.start = day.replace(day=1)

    @property
    def end(self):
        if self.start.month == 12:
            return date(self.start.year + 1, 1, 1)
        return date(self.start.year, self.start.month + 1, 1)

    @property
    def previous(self):
        if self.start.month == 1:
            return CalendarMonth(date(self.start.year - 1, 12, 1))
        return CalendarMonth(date(self.start.year, self.start.month - 1, 1))

    @property
    def label(self):
        return MONTH_NAMES[self.start.month - 1]

    @property
    def short_label(self):
        return f"{self.label[:3].lower()}."
