from django.db import models


class ActiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(activo=True)


class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100, blank=True, default="")
    telefono = models.CharField(max_length=20, blank=True, default="")
    email = models.EmailField(blank=True, default="")
    fecha_registro = models.DateField(auto_now_add=True)

    # Campos adicionales para gestión
    activo = models.BooleanField(default=True)
    notas = models.TextField(blank=True, null=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    objects = models.Manager()
    active_objects = ActiveManager()

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
        nombre_parts = [self.nombre]
        if self.apellido and self.apellido.strip():
            nombre_parts.append(self.apellido)
        return " ".join(nombre_parts)

    def get_citas_activas(self):
        """Retorna las citas no canceladas del cliente"""
        return self.citas.exclude(estado="CANCELADA")
