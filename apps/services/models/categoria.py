from django.db import models
from model_utils.models import TimeStampedModel, SoftDeletableModel
from simple_history.models import HistoricalRecords


class CategoriaActivaManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                estado=self.model.EstadoChoices.ACTIVO,
                is_removed=False,
            )
        )


class CategoriaInactivaManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(
                estado=self.model.EstadoChoices.INACTIVO,
                is_removed=False,
            )
        )


class CategoriasManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_removed=False)


class Categoria(TimeStampedModel, SoftDeletableModel):
    class EstadoChoices(models.TextChoices):
        ACTIVO = "activo", "Activo"
        INACTIVO = "inactivo", "Inactivo"

    estado = models.CharField(
        max_length=20,
        choices=EstadoChoices.choices,
        default=EstadoChoices.ACTIVO,
        db_index=True,
    )
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)

    # Auditoria completa (critico para cambios de precio)
    history = HistoricalRecords(inherit=True)

    # Managers
    objects = CategoriasManager()  # Manager por defecto (excluye eliminados)
    all_objects = models.Manager()  # Manager que incluye eliminados
    activos = CategoriaActivaManager()  # Solo activos
    inactivos = CategoriaInactivaManager()  # Solo inactivos

    class Meta:
        app_label = "services"
        db_table = "categoria"
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre
