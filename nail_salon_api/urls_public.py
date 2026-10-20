from django.contrib import admin
from django.urls import path
from django.views.generic import RedirectView
from rest_framework.authtoken.models import TokenProxy

if admin.site.is_registered(TokenProxy):
    admin.site.unregister(TokenProxy)

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="admin:index")),
    path("admin/", admin.site.urls),
]

handler400 = "apps.common.views.error_views.bad_request"
handler403 = "apps.common.views.error_views.permission_denied"
handler404 = "apps.common.views.error_views.page_not_found"
handler500 = "apps.common.views.error_views.server_error"
