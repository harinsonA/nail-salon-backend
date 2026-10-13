from django.contrib import admin
from django.urls import path
from rest_framework.authtoken.models import TokenProxy

if admin.site.is_registered(TokenProxy):
    admin.site.unregister(TokenProxy)

urlpatterns = [
    path("admin/", admin.site.urls),
]

handler403 = "apps.panel.views.sin_permiso.view.sin_permiso_en_el_panel"
