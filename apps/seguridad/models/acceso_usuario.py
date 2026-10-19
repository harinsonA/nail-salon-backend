from django.conf import settings
from django.db import models
from model_utils.models import TimeStampedModel

from apps.common.historial import HistorialRecords


class AccesoUsuario(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="acceso")
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    ultimo_intento_fallido = models.DateTimeField(null=True, blank=True)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    bloqueado = models.BooleanField(default=False)
    bloqueado_desde = models.DateTimeField(null=True, blank=True)
    token_sesion = models.UUIDField(null=True, blank=True)

    history = HistorialRecords()

    class Meta:
        db_table = "accesos_usuario"
        verbose_name = "Acceso de usuario"
        verbose_name_plural = "Accesos de usuarios"

    def __str__(self):
        return f"Acceso de {self.user}"
