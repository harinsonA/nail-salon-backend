from django.contrib import admin
from .models.servicio import Servicio


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    """
    Configuración del admin para Servicio
    """

    list_display = [
        "servicio_id",
        "nombre_servicio",
        "categoria",
        "precio_formateado",
        "duracion_formateada",
        "activo",
        "fecha_creacion",
    ]

    list_filter = [
        "activo",
        "categoria",
        "fecha_creacion",
        "fecha_actualizacion",
    ]

    search_fields = [
        "nombre_servicio",
        "descripcion",
        "categoria",
    ]

    ordering = ["nombre_servicio"]

    readonly_fields = [
        "servicio_id",
        "fecha_creacion",
        "fecha_actualizacion",
        "precio_formateado",
        "duracion_formateada",
    ]

    fieldsets = (
        (
            "Información Básica",
            {
                "fields": (
                    "nombre_servicio",
                    "descripcion",
                    "categoria",
                )
            },
        ),
        (
            "Detalles del Servicio",
            {
                "fields": (
                    "precio",
                    "precio_formateado",
                    "duracion_estimada",
                    "duracion_formateada",
                    "activo",
                )
            },
        ),
        ("Imagen", {"fields": ("imagen",), "classes": ("collapse",)}),
        (
            "Información del Sistema",
            {
                "fields": (
                    "servicio_id",
                    "fecha_creacion",
                    "fecha_actualizacion",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    list_per_page = 25
    list_max_show_all = 100
    list_editable = ["activo"]

    def precio_formateado(self, obj):
        """Muestra el precio formateado con símbolo de moneda"""
        return f"${obj.precio:,.0f}"

    precio_formateado.short_description = "Precio"
    precio_formateado.admin_order_field = "precio"

    def duracion_formateada(self, obj):
        """Muestra la duración en formato legible"""
        if obj.duracion_estimada:
            total_seconds = obj.duracion_estimada.total_seconds()
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            if hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        return "No especificado"

    duracion_formateada.short_description = "Duración"
    duracion_formateada.admin_order_field = "duracion_estimada"

    def get_queryset(self, request):
        """Optimizar consultas"""
        return super().get_queryset(request)

    # Acciones personalizadas
    actions = ["activar_servicios", "desactivar_servicios"]

    def activar_servicios(self, request, queryset):
        """Activa los servicios seleccionados"""
        updated = queryset.update(activo=True)
        self.message_user(request, f"{updated} servicios activados exitosamente.")

    activar_servicios.short_description = "Activar servicios seleccionados"

    def desactivar_servicios(self, request, queryset):
        """Desactiva los servicios seleccionados"""
        updated = queryset.update(activo=False)
        self.message_user(request, f"{updated} servicios desactivados exitosamente.")

    desactivar_servicios.short_description = "Desactivar servicios seleccionados"
