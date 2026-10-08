from django.urls import path

from apps.tenancy.views import pagina_publica_pendiente

urlpatterns = [
    path("", pagina_publica_pendiente),
]
