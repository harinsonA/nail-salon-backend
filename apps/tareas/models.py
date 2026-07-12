from django.db import models
from django.utils import timezone
from model_utils.models import TimeStampedModel


class TareaEnProceso(TimeStampedModel):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        EN_PROCESO = "en_proceso", "En proceso"
        COMPLETADO = "completado", "Completado"
        FALLIDO = "fallido", "Fallido"

    celery_task_id = models.CharField(max_length=255, blank=True, default="")
    nombre_proceso = models.CharField(max_length=100)
    origen = models.CharField(max_length=50, db_index=True)

    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        db_index=True,
    )
    progreso_actual = models.PositiveIntegerField(default=0)
    total_registros = models.PositiveIntegerField(default=0)

    datos_entrada = models.JSONField(default=dict, blank=True)
    resultado_metadata = models.JSONField(default=dict, blank=True)

    finalizado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "tareas_en_proceso"
        ordering = ["-created"]
        verbose_name = "Tarea en proceso"
        verbose_name_plural = "Tareas en proceso"

    def __str__(self):
        return f"{self.nombre_proceso} · {self.get_estado_display()}"

    @property
    def porcentaje(self):
        if not self.total_registros:
            return 0
        return round(self.progreso_actual * 100 / self.total_registros)

    @property
    def activa(self):
        return self.estado in (self.Estado.PENDIENTE, self.Estado.EN_PROCESO)

    def iniciar(self, total=0):
        self.estado = self.Estado.EN_PROCESO
        self.total_registros = total
        self.save(update_fields=["estado", "total_registros", "modified"])

    def avanzar(self, procesados, **metadata):
        self.progreso_actual = procesados
        campos = ["progreso_actual", "modified"]
        if metadata:
            self.resultado_metadata = {**self.resultado_metadata, **metadata}
            campos.append("resultado_metadata")
        self.save(update_fields=campos)

    def completar(self, **metadata):
        self.estado = self.Estado.COMPLETADO
        self.progreso_actual = self.total_registros or self.progreso_actual
        self.resultado_metadata = {**self.resultado_metadata, **metadata}
        self.finalizado_en = timezone.now()
        self.save(
            update_fields=[
                "estado",
                "progreso_actual",
                "resultado_metadata",
                "finalizado_en",
                "modified",
            ]
        )

    def fallar(self, error, **metadata):
        self.estado = self.Estado.FALLIDO
        self.resultado_metadata = {
            **self.resultado_metadata,
            "error_detalle": str(error),
            "detenida_en": self.progreso_actual,
            **metadata,
        }
        self.finalizado_en = timezone.now()
        self.save(
            update_fields=[
                "estado",
                "resultado_metadata",
                "finalizado_en",
                "modified",
            ]
        )
