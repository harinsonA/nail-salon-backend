from django.urls import path

from apps.tenancy.views import pagina_publica

urlpatterns = [
    path("", pagina_publica, name="pagina_publica"),
]

handler400 = "apps.common.views.error_views.bad_request"
handler403 = "apps.common.views.error_views.permission_denied"
handler404 = "apps.common.views.error_views.page_not_found"
handler500 = "apps.common.views.error_views.server_error"
