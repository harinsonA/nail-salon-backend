from django.db import models
from utils.validators import validate_precio_positivo, validate_duracion_positiva


class Servicio(models.Model):
    servicio_id = models.AutoField(primary_key=True)
    nombre_servicio = models.CharField(max_length=200)
    precio = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[validate_precio_positivo]
    )
    descripcion = models.TextField(blank=True, null=True)
    duracion_estimada = models.DurationField(
        validators=[validate_duracion_positiva], blank=True, null=True
    )

    # Campos adicionales
    activo = models.BooleanField(default=True)
    categoria = models.CharField(max_length=100, blank=True)
    imagen = models.ImageField(upload_to="servicios/", blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "services"
        db_table = "servicios"
        verbose_name = "Servicio"
        verbose_name_plural = "Servicios"
        ordering = ["nombre_servicio"]

    def __str__(self):
        return self.nombre_servicio

    @property
    def id(self):
        """Alias para servicio_id para compatibilidad con tests y API estándar"""
        return self.servicio_id

    @property
    def duracion_en_minutos(self):
        """Retorna la duración en minutos"""
        if self.duracion_estimada:
            return int(self.duracion_estimada.total_seconds() / 60)
        return 0

    def get_precio_formateado(self):
        """Retorna el precio formateado como string"""
        return f"${self.precio:,.0f}"
