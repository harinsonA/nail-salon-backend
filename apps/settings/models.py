from django.db import models


# Modelo básico para configuraciones del salón
class ConfiguracionSalon(models.Model):
    nombre_salon = models.CharField(max_length=200, default="Mi Salón de Uñas")
    direccion = models.TextField(blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "settings"
        db_table = "configuracion_salon"
        verbose_name = "Configuración del Salón"
        verbose_name_plural = "Configuraciones del Salón"

    def __str__(self):
        return self.nombre_salon
