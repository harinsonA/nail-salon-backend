from django.http import HttpResponseNotFound
from django.views import defaults


def pagina_publica_pendiente(request):
    return HttpResponseNotFound()


def sin_permiso_en_el_panel(request, exception=None):
    return defaults.permission_denied(request, exception, template_name="admin/sin_permiso.html")
