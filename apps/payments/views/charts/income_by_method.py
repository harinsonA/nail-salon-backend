from django.http import JsonResponse
from django.views.generic import View

from apps.common.views.base_views import ProtectedAjaxView
from apps.payments.services.income_by_method import income_by_method
from apps.payments.views.incomes.list import IncomesFilterForm


class IncomeByMethodChartAjax(ProtectedAjaxView, View):
    """Endpoint del gráfico "Ingresos por método de pago" de la página de ingresos.

    Reusa IncomesFilterForm para resolver exactamente los mismos filtros que la
    tabla (el rango de fechas, con su default de hoy-15, y el método si viene) y
    delega el cálculo en el servicio.
    """

    def get(self, request, *args, **kwargs):
        # is_valid() ejecuta full_clean y deja en cleaned_data el dict de
        # filtros ORM que arma IncomesFilterForm.clean. Se pasa request.GET tal
        # cual (no `or None`): un QueryDict vacío sigue siendo un form "bound",
        # y el form cae al rango por defecto cuando las fechas no vienen.
        form = IncomesFilterForm(request.GET)
        form.is_valid()
        return JsonResponse(income_by_method(form.cleaned_data))
