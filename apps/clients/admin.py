from django.contrib import admin
from .models.cliente import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = [
        "cliente_id",
        "nombre",
        "apellido",
        "telefono",
        "email",
        "fecha_registro",
        "activo",
    ]
    list_filter = ["activo", "fecha_registro", "fecha_creacion"]
    search_fields = ["nombre", "apellido", "telefono", "email"]
    ordering = ["-fecha_registro"]
    readonly_fields = [
        "cliente_id",
        "fecha_registro",
        "fecha_creacion",
        "fecha_actualizacion",
    ]

    fieldsets = (
        (
            "Información Personal",
            {"fields": ("nombre", "apellido", "telefono", "email")},
        ),
        ("Estado y Notas", {"fields": ("activo", "notas")}),
        (
            "Información del Sistema",
            {
                "fields": (
                    "cliente_id",
                    "fecha_registro",
                    "fecha_creacion",
                    "fecha_actualizacion",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editando un objeto existente
            return self.readonly_fields
        return ["cliente_id", "fecha_creacion", "fecha_actualizacion"]
