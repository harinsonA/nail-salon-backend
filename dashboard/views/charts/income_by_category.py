from django.http import JsonResponse
from django.views.generic import View

from apps.common.views.base_views import ProtectedAjaxView
from dashboard.forms import DashboardFilterForm
from dashboard.services import metrics


class IncomeByCategoryChartAjax(ProtectedAjaxView, View):
    """Endpoint del gráfico "Ingresos por categoría"."""

    def get(self, request, *args, **kwargs):
        period = DashboardFilterForm(request.GET).get_period()
        return JsonResponse(metrics.income_by_category(period))
