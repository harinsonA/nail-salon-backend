from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from apps.tenancy.models import Persona, PersonaCorreo, PersonaDireccion, PersonaTelefono


class PersonaCorreoInline(admin.TabularInline):
    model = PersonaCorreo
    extra = 0
    fields = ("correo", "etiqueta", "es_principal", "rebota_desde")


class PersonaTelefonoInline(admin.TabularInline):
    model = PersonaTelefono
    extra = 0
    fields = ("codigo_pais", "numero", "tipo", "tiene_whatsapp", "etiqueta", "es_principal")


class PersonaDireccionInline(admin.StackedInline):
    model = PersonaDireccion
    extra = 0


@admin.register(Persona)
class PersonaAdmin(SimpleHistoryAdmin):
    list_display = ("nombre_completo", "correo_principal", "negocios")
    search_fields = ("nombres", "apellidos", "correos__correo", "telefonos__numero")
    fields = ("nombres", "apellidos", "notas")
    inlines = [PersonaCorreoInline, PersonaTelefonoInline, PersonaDireccionInline]

    @admin.display(description="Correo principal")
    def correo_principal(self, persona):
        correo = persona.correos.filter(es_principal=True).first()
        return correo.correo if correo else "—"

    @admin.display(description="Negocios")
    def negocios(self, persona):
        return ", ".join(negocio.nombre for negocio in persona.negocios_como_titular.all()) or "—"
