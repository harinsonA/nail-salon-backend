from django.db import models
from utils.validators import validate_telefono


class Cliente(models.Model):
    cliente_id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    telefono = models.CharField(
        max_length=20, validators=[validate_telefono], unique=True
    )
    email = models.EmailField(unique=True)
    fecha_registro = models.DateField(auto_now_add=True)

    # Campos adicionales para gestión
    activo = models.BooleanField(default=True)
    notas = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "clients"
        db_table = "clientes"
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["-fecha_registro"]

    def __str__(self):
        return f"{self.nombre} {self.apellido}"

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"

    def get_citas_activas(self):
        """Retorna las citas no canceladas del cliente"""
        return self.citas.exclude(estado_cita="CANCELADA")
