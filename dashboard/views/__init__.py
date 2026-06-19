from dashboard.views.shell import DashboardView
from dashboard.views.charts.attended_clients import AttendedClientsChartAjax
from dashboard.views.charts.income import IncomeChartAjax
from dashboard.views.charts.appointment_status import AppointmentStatusChartAjax
from dashboard.views.charts.payment_methods import PaymentMethodsChartAjax
from dashboard.views.charts.top_services import TopServicesChartAjax
from dashboard.views.charts.income_by_category import IncomeByCategoryChartAjax

__all__ = [
    "DashboardView",
    "AttendedClientsChartAjax",
    "IncomeChartAjax",
    "AppointmentStatusChartAjax",
    "PaymentMethodsChartAjax",
    "TopServicesChartAjax",
    "IncomeByCategoryChartAjax",
]
