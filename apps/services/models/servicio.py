import datetime
from django.db import models


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(activo=True)


class Servicio(models.Model):
    nombre = models.CharField(max_length=200)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    descripcion = models.TextField(blank=True, null=True)
    duracion_estimada = models.DurationField(
        blank=True, null=True, default=datetime.timedelta(minutes=30)
    )
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    active_objects = ActiveManager()

    class Meta:
        app_label = "services"
        db_table = "servicios"
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def id(self):
        """Alias para pk para compatibilidad con tests y API estándar"""
        return self.pk

    @property
    def duracion_en_minutos(self):
        """Retorna la duración en minutos"""
        if self.duracion_estimada:
            return int(self.duracion_estimada.total_seconds() / 60)
        return 0

    def get_precio_formateado(self):
        """Retorna el precio formateado como string"""
        return f"${self.precio:,.0f}"
