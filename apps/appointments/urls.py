from django.urls import path, include
from rest_framework.routers import DefaultRouter
# from .views.cita_views import CitaViewSet

# Crear el router
router = DefaultRouter()
# router.register(r'citas', CitaViewSet, basename='cita')

# URLs de la aplicación
urlpatterns = [
    path("", include(router.urls)),
]
