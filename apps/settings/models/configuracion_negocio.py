from django.db import models


class ConfiguracionNegocio(models.Model):
    nombre_visible = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "settings"
        db_table = "configuracion_negocio"
        verbose_name = "Configuración del negocio"
        verbose_name_plural = "Configuraciones del negocio"

    def __str__(self):
        return self.nombre_visible
