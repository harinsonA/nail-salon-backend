from django.contrib import admin
from django.urls import path
from simple_history.admin import SimpleHistoryAdmin

from apps.panel.admin.mixins import DjangoPagesRedirectMixin
from apps.panel.views.people.view import (
    PersonCreateModalView,
    PersonDeleteModalView,
    PersonListAjaxView,
    PersonListView,
    PersonUpdateModalView,
)
from apps.tenancy.models import (
    Persona,
    PersonaCorreo,
    PersonaDireccion,
    PersonaTelefono,
)


class PersonaCorreoInline(admin.TabularInline):
    model = PersonaCorreo
    extra = 0
    fields = ("correo", "etiqueta", "es_principal", "rebota_desde")


class PersonaTelefonoInline(admin.TabularInline):
    model = PersonaTelefono
    extra = 0
    fields = (
        "codigo_pais",
        "numero",
        "tipo",
        "tiene_whatsapp",
        "etiqueta",
        "es_principal",
    )


class PersonaDireccionInline(admin.StackedInline):
    model = PersonaDireccion
    extra = 0


@admin.register(Persona)
class PersonaAdmin(DjangoPagesRedirectMixin, SimpleHistoryAdmin):
    list_display = ("nombre_completo", "correo_principal", "negocios")
    search_fields = ("nombres", "apellidos", "correos__correo", "telefonos__numero")
    fields = ("nombres", "apellidos", "notas")
    inlines = [PersonaCorreoInline, PersonaTelefonoInline, PersonaDireccionInline]

    def get_urls(self):
        list_ajax = PersonListAjaxView.as_view(
            admin_site=self.admin_site, model_admin=self
        )
        create_modal = PersonCreateModalView.as_view(
            admin_site=self.admin_site, model_admin=self
        )
        change_modal = PersonUpdateModalView.as_view(
            admin_site=self.admin_site, model_admin=self
        )
        delete_modal = PersonDeleteModalView.as_view(
            admin_site=self.admin_site, model_admin=self
        )
        return [
            path("list/", list_ajax, name="tenancy_persona_list_ajax"),
            path("add/modal/", create_modal, name="tenancy_persona_add_modal"),
            path(
                "<int:pk>/change/modal/",
                change_modal,
                name="tenancy_persona_change_modal",
            ),
            path(
                "<int:pk>/delete/modal/",
                delete_modal,
                name="tenancy_persona_delete_modal",
            ),
            *super().get_urls(),
        ]

    def changelist_view(self, request, extra_context=None):
        return PersonListView.as_view(admin_site=self.admin_site, model_admin=self)(
            request
        )

    @admin.display(description="Correo principal")
    def correo_principal(self, persona):
        correo = persona.correos.filter(es_principal=True).first()
        return correo.correo if correo else "—"

    @admin.display(description="Negocios")
    def negocios(self, persona):
        return (
            ", ".join(negocio.nombre for negocio in persona.negocios_como_titular.all())
            or "—"
        )
