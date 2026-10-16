from django.db import models


class Rubro(models.Model):
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=80)
    activo = models.BooleanField(default=True)
    # Obsoleto: ya no ordena los rubros ni se edita desde el panel. Se conserva en la base con 0 por defecto.
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "rubros"
        verbose_name = "Rubro"
        verbose_name_plural = "Rubros"
        ordering = ["nombre", "codigo"]

    def __str__(self):
        return self.nombre
