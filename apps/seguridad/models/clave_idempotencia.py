from django.conf import settings
from django.db import models
from model_utils.models import TimeStampedModel


class ClaveIdempotencia(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="claves_idempotencia"
    )
    clave = models.CharField(max_length=64)
    metodo = models.CharField(max_length=10)
    ruta = models.CharField(max_length=255)
    codigo_respuesta = models.PositiveSmallIntegerField()
    respuesta = models.JSONField()

    class Meta:
        db_table = "claves_idempotencia"
        verbose_name = "Clave de idempotencia"
        verbose_name_plural = "Claves de idempotencia"
        constraints = [
            models.UniqueConstraint(fields=["user", "clave"], name="clave_idempotencia_por_usuario")
        ]

    def __str__(self):
        return f"{self.metodo} {self.ruta} ({self.clave})"
