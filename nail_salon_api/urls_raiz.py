from django.urls import path

from apps.settings.app_release.view import AppReleaseView
from apps.tenancy.views import pagina_publica

urlpatterns = [
    path("", pagina_publica, name="pagina_publica"),
    path("api/platform/app-release/", AppReleaseView.as_view(), name="app_release"),
]

handler400 = "apps.common.views.error_views.bad_request"
handler403 = "apps.common.views.error_views.permission_denied"
handler404 = "apps.common.views.error_views.page_not_found"
handler500 = "apps.common.views.error_views.server_error"
