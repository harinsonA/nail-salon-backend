from django.db import models
from django.db.models import ProtectedError
from model_utils.managers import SoftDeletableManager
from model_utils.models import SoftDeletableModel, TimeStampedModel

from apps.common.historial import HistorialRecords


class Persona(TimeStampedModel, SoftDeletableModel):
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100, blank=True, default="")
    notas = models.TextField(blank=True, null=True)

    history = HistorialRecords()

    objects = SoftDeletableManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "personas"
        verbose_name = "Persona"
        verbose_name_plural = "Personas"
        ordering = ["nombres", "apellidos"]

    def __str__(self):
        return self.nombre_completo

    @property
    def nombre_completo(self):
        return " ".join(parte for parte in (self.nombres, self.apellidos) if parte)

    def delete(self, using=None, *args, soft=True, **kwargs):
        negocios = self.negocios_como_titular.all()
        if soft and negocios.exists():
            raise ProtectedError(
                "No se puede eliminar a una persona que es titular de un negocio: primero cambia el titular.",
                set(negocios),
            )
        return super().delete(using, *args, soft=soft, **kwargs)
