from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views.cita_views import CitaViewSet
from .views.detalle_cita_views import DetalleCitaViewSet

# Crear el router
router = DefaultRouter()
router.register(r"citas", CitaViewSet, basename="cita")
router.register(r"detalles-cita", DetalleCitaViewSet, basename="detalle-cita")

# URLs de la aplicación
urlpatterns = [
    path("", include(router.urls)),
]
