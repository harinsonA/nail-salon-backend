from django.urls import path, include
from rest_framework.routers import DefaultRouter
# from .views.servicio_views import ServicioViewSet

# Crear el router
router = DefaultRouter()
# router.register(r'servicios', ServicioViewSet, basename='servicio')

# URLs de la aplicación
urlpatterns = [
    path("", include(router.urls)),
]
