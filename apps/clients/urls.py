from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.cliente_views import ClienteViewSet

# Crear el router
router = DefaultRouter()
router.register(r"clientes", ClienteViewSet, basename="cliente")

# URLs de la aplicación
urlpatterns = [
    path("", include(router.urls)),
]
