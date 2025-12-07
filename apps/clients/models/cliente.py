from django.db import models
from model_utils.models import TimeStampedModel, SoftDeletableModel
from simple_history.models import HistoricalRecords


class Cliente(TimeStampedModel, SoftDeletableModel):
    class EstadoChoices(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"

    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.ACTIVO,
        db_index=True,
    )
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100, blank=True, default="")
    telefono = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    notas = models.TextField(blank=True, null=True)

    # Auditoría completa
    history = HistoricalRecords(inherit=True)

    class Meta:
        app_label = "clients"
        db_table = "clientes"
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["-created"]  # Ordenar por fecha de creación (TimeStampedModel)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

    @property
    def nombre_completo(self):
        nombre_parts = [self.nombre]
        if self.apellido and self.apellido.strip():
            nombre_parts.append(self.apellido)
        return " ".join(nombre_parts)

    def get_citas_activas(self):
        """Retorna las citas no canceladas del cliente"""
        return self.citas.exclude(estado="CANCELADA")
