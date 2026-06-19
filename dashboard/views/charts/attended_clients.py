from django.http import JsonResponse
from django.views.generic import View

from apps.common.views.base_views import ProtectedAjaxView
from dashboard.forms import DashboardFilterForm
from dashboard.services import metrics


class AttendedClientsChartAjax(ProtectedAjaxView, View):
    """Endpoint del gráfico "Clientes atendidos".

    Devuelve, para los últimos N meses, dos series mensuales: citas
    completadas y clientes únicos. Responde el contrato JSON uniforme
    (labels + datasets + meta).
    """

    def get(self, request, *args, **kwargs):
        form = DashboardFilterForm(request.GET)
        months = form.get_months()
        payload = metrics.attended_clients(months)
        return JsonResponse(payload)
