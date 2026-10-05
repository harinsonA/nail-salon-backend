from django.db import models
from django.db.models.functions import Lower
from model_utils.models import TimeStampedModel

from apps.common.historial import HistorialRecords
from apps.common.models import ConPrincipal


class PersonaCorreo(TimeStampedModel, ConPrincipal):
    campo_dueno = "persona"

    persona = models.ForeignKey("tenancy.Persona", on_delete=models.CASCADE, related_name="correos")
    correo = models.EmailField(max_length=254)
    etiqueta = models.CharField(max_length=30, blank=True, default="")
    rebota_desde = models.DateTimeField(null=True, blank=True)

    history = HistorialRecords()

    class Meta:
        db_table = "personas_correos"
        verbose_name = "Correo de persona"
        verbose_name_plural = "Correos de personas"
        constraints = [
            models.UniqueConstraint(fields=["persona", "correo"], name="%(app_label)s_%(class)s_correo_unico"),
            models.CheckConstraint(
                condition=models.Q(correo=Lower("correo")),
                name="%(app_label)s_%(class)s_correo_en_minusculas",
            ),
            ConPrincipal.restriccion_principal("persona"),
        ]

    def __str__(self):
        return self.correo

    def save(self, *args, **kwargs):
        self.correo = self.correo.strip().lower()
        super().save(*args, **kwargs)
