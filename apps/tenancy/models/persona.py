from django.db import models
from django.db.models import ProtectedError
from model_utils.managers import SoftDeletableManager
from model_utils.models import SoftDeletableModel, TimeStampedModel

from apps.common.historial import HistorialRecords
from apps.common.utils.countries.constants import Country


class Persona(TimeStampedModel, SoftDeletableModel):
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100, blank=True, default="")
    pais = models.CharField(max_length=2, choices=Country.choices, null=True, blank=True)
    tipo_identificador_nacional = models.CharField(max_length=20, null=True, blank=True)
    identificador_nacional = models.CharField(max_length=20, null=True, blank=True)
    notas = models.TextField(blank=True, null=True)

    history = HistorialRecords()

    objects = SoftDeletableManager()
    all_objects = models.Manager()

    class Meta:
        db_table = "personas"
        verbose_name = "Propietario"
        verbose_name_plural = "Propietarios"
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
                "No se puede eliminar a un propietario que es titular de un negocio: primero cambia el titular.",
                set(negocios),
            )
        return super().delete(using, *args, soft=soft, **kwargs)
