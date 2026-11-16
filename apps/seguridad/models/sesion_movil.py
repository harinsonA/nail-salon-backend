from django.conf import settings
from django.db import models
from model_utils.models import TimeStampedModel

from apps.common.historial import HistorialRecords


class SesionMovil(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sesion_movil")
    llave_sesion = models.CharField(max_length=64, unique=True, null=True, blank=True)
    llave_sesion_vence = models.DateTimeField(null=True, blank=True)
    llave_telefono = models.CharField(max_length=64, unique=True, null=True, blank=True)
    llave_telefono_vence = models.DateTimeField(null=True, blank=True)
    firma_clave = models.CharField(max_length=128, null=True, blank=True)
    dispositivo = models.CharField(max_length=128, null=True, blank=True)
    version_app = models.CharField(max_length=20, null=True, blank=True)
    ultimo_uso = models.DateTimeField(null=True, blank=True)

    history = HistorialRecords()

    class Meta:
        db_table = "sesiones_moviles"
        verbose_name = "Sesión móvil"
        verbose_name_plural = "Sesiones móviles"

    def __str__(self):
        return f"Sesión móvil de {self.user}"
