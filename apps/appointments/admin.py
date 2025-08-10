from django.contrib import admin
from .models.cita import Cita
from .models.detalle_cita import DetalleCita


class DetalleCitaInline(admin.TabularInline):
    """
    Inline para mostrar detalles de cita en la vista de Cita
    """

    model = DetalleCita
    extra = 1
    readonly_fields = ["subtotal", "precio_unitario_con_descuento", "fecha_creacion"]
    fields = [
        "servicio",
        "precio_acordado",
        "cantidad_servicios",
        "descuento",
        "subtotal",
        "notas_detalle",
    ]


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = [
        "cita_id",
        "cliente",
        "fecha_hora_cita",
        "estado_cita",
        "monto_total_display",
        "cantidad_servicios_display",
        "fecha_creacion",
    ]
    list_filter = [
        "estado_cita",
        "fecha_hora_cita",
        "fecha_creacion",
        "cliente__activo",
    ]
    search_fields = [
        "cliente__nombre",
        "cliente__apellido",
        "cliente__telefono",
        "cliente__email",
        "observaciones",
    ]
    ordering = ["-fecha_hora_cita"]
    readonly_fields = [
        "cita_id",
        "monto_total",
        "duracion_total",
        "puede_ser_modificada",
        "fecha_creacion",
        "fecha_actualizacion",
    ]

    fieldsets = (
        (
            "Información Básica",
            {"fields": ("cliente", "fecha_hora_cita", "estado_cita", "observaciones")},
        ),
        (
            "Información Calculada",
            {
                "fields": (
                    "monto_total",
                    "duracion_total",
                    "puede_ser_modificada",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Información del Sistema",
            {
                "fields": (
                    "cita_id",
                    "creado_por",
                    "fecha_creacion",
                    "fecha_actualizacion",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    inlines = [DetalleCitaInline]

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editando un objeto existente
            return self.readonly_fields + ["cliente"]  # No permitir cambiar cliente
        return self.readonly_fields

    def monto_total_display(self, obj):
        """Mostrar monto total formateado"""
        return f"${obj.monto_total:,.2f}" if obj.monto_total else "$0.00"

    monto_total_display.short_description = "Monto Total"

    def cantidad_servicios_display(self, obj):
        """Mostrar cantidad de servicios"""
        return obj.detalles.count()

    cantidad_servicios_display.short_description = "Servicios"

    def save_model(self, request, obj, form, change):
        if not change:  # Solo al crear
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(DetalleCita)
class DetalleCitaAdmin(admin.ModelAdmin):
    list_display = [
        "detalle_cita_id",
        "cita",
        "servicio",
        "precio_acordado",
        "cantidad_servicios",
        "descuento",
        "subtotal_display",
        "fecha_creacion",
    ]
    list_filter = ["servicio", "fecha_creacion", "cita__estado_cita"]
    search_fields = [
        "cita__cliente__nombre",
        "cita__cliente__apellido",
        "servicio__nombre_servicio",
        "notas_detalle",
    ]
    ordering = ["-fecha_creacion"]
    readonly_fields = [
        "detalle_cita_id",
        "subtotal",
        "precio_unitario_con_descuento",
        "fecha_creacion",
    ]

    fieldsets = (
        (
            "Información del Servicio",
            {
                "fields": (
                    "cita",
                    "servicio",
                    "precio_acordado",
                    "cantidad_servicios",
                    "descuento",
                )
            },
        ),
        (
            "Información Calculada",
            {
                "fields": (
                    "subtotal",
                    "precio_unitario_con_descuento",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Información Adicional",
            {
                "fields": (
                    "notas_detalle",
                    "detalle_cita_id",
                    "fecha_creacion",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def subtotal_display(self, obj):
        """Mostrar subtotal formateado"""
        return f"${obj.subtotal:,.2f}" if obj.subtotal else "$0.00"

    subtotal_display.short_description = "Subtotal"

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editando un objeto existente
            # No permitir cambiar cita y servicio si ya existe
            return self.readonly_fields + ["cita", "servicio"]
        return self.readonly_fields
