from django.http import JsonResponse
from django.views.generic import View

from apps.common.views.base_views import ProtectedAjaxView
from dashboard.forms import DashboardFilterForm
from dashboard.services import metrics


class PaymentMethodsChartAjax(ProtectedAjaxView, View):
    """Endpoint del gráfico "Métodos de pago": cobrado por método."""

    def get(self, request, *args, **kwargs):
        months = DashboardFilterForm(request.GET).get_months()
        return JsonResponse(metrics.payment_methods(months))
