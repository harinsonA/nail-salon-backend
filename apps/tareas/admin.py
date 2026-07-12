from django.contrib import admin

from apps.tareas.models import TareaEnProceso


@admin.register(TareaEnProceso)
class TareaEnProcesoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre_proceso",
        "origen",
        "estado",
        "porcentaje",
        "progreso_actual",
        "total_registros",
        "created",
        "finalizado_en",
    )
    list_filter = ("estado", "origen")
    search_fields = ("nombre_proceso", "celery_task_id")
    readonly_fields = ("created", "modified", "finalizado_en", "celery_task_id")
    ordering = ("-created",)
