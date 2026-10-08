from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]

handler403 = "apps.tenancy.views.sin_permiso_en_el_panel"
