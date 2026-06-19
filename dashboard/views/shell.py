from django.views.generic import TemplateView

from apps.common.views.base_views import ProtectedView


class DashboardView(ProtectedView, TemplateView):
    """Vista shell del dashboard: solo pinta la maqueta con los <canvas>.

    No conoce los datos; cada gráfico obtiene los suyos por AJAX desde su
    propio endpoint, cuya URL se inyecta como data-url en el canvas con
    {% url %} (los nombres de ruta son la única fuente de verdad).
    """

    template_name = "dashboard/index.html"
