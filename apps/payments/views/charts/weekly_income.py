from django.http import JsonResponse
from django.views.generic import View

from apps.common.views.base_views import ProtectedAjaxView
from apps.payments.services.weekly_income import weekly_income
from apps.payments.views.payments.list import PaymentsFilterForm


class WeeklyIncomeChartAjax(ProtectedAjaxView, View):
    """Endpoint del gráfico "Ingresos por semana" de la página de pagos.

    Reusa PaymentsFilterForm para resolver el filtro `months` al rango del mes
    (cae al mes actual si llega vacío) y delega el cálculo en el servicio.
    """

    def get(self, request, *args, **kwargs):
        # is_valid() ejecuta full_clean y deja en cleaned_data el dict
        # {fecha_cita__gte, fecha_cita__lte} que arma PaymentsFilterForm.clean.
        # Se pasa request.GET tal cual (no `or None`): un QueryDict vacío sigue
        # siendo un form "bound", y CustomMonthField cae al mes actual cuando
        # `months` no viene.
        form = PaymentsFilterForm(request.GET)
        form.is_valid()
        cleaned = form.cleaned_data
        return JsonResponse(
            weekly_income(
                cleaned["fecha_cita__gte"],
                cleaned["fecha_cita__lte"],
            )
        )
