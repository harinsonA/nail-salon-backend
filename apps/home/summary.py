from django.utils import timezone

from apps.home.calendar_month import CalendarMonth
from apps.home.month_appointments import MonthAppointments
from apps.payments.accounting.collected_income import CollectedIncome
from apps.payments.accounting.debts import Debts
from apps.profiles.capabilities import Capabilities
from apps.tenancy.business_status import BusinessStatus


class HomeSummary:
    DEBTORS_ROUTE = "debtors"
    INCOMES_ROUTE = "incomes"

    def __init__(self, user, negocio, today=None):
        self.user = user
        self.capabilities = Capabilities(user, negocio)
        self.status = BusinessStatus(negocio)
        self.month = CalendarMonth(today or timezone.localdate())

    def shows(self, url_name):
        return self.capabilities.allows(url_name) and not self.status.pauses_section(url_name, self.user)

    def debtors(self):
        return Debts.count() if self.shows(self.DEBTORS_ROUTE) else None

    def incomes(self):
        if not self.shows(self.INCOMES_ROUTE):
            return None
        return [
            {
                "label": month.short_label,
                "start": month.start,
                "amount": CollectedIncome.between(month.start, month.end),
            }
            for month in (self.month.previous, self.month)
        ]

    def build(self):
        return {
            "month": MonthAppointments(self.user, self.month).counts(),
            "debtors": self.debtors(),
            "incomes": self.incomes(),
        }
