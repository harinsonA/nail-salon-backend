from django.urls import path

from apps.tenancy.views import pagina_publica

urlpatterns = [
    path("", pagina_publica, name="pagina_publica"),
]
