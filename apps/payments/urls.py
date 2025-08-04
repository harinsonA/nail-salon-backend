from django.urls import path, include
from rest_framework.routers import DefaultRouter
# from .views.pago_views import PagoViewSet

# Crear el router
router = DefaultRouter()
# router.register(r'pagos', PagoViewSet, basename='pago')

# URLs de la aplicación
urlpatterns = [
    path("", include(router.urls)),
]
