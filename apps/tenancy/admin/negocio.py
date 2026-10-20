from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path
from django_tenants.utils import get_public_schema_name
from simple_history.admin import SimpleHistoryAdmin

from apps.panel.views.businesses.view import (
    BusinessCreateView,
    BusinessHistoryListAjaxView,
    BusinessListAjaxView,
    BusinessListView,
    BusinessRepairModalView,
    BusinessStatusModalView,
    BusinessUpdateView,
    OwnerPasswordResetModalView,
    OwnerUnlockModalView,
)
from apps.panel.views.history.view import HistoryModalView
from apps.tenancy.models import Dominio, Negocio, NegocioDireccion


class DominioInline(admin.TabularInline):
    model = Dominio
    extra = 0
    fields = ("domain", "is_primary")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class NegocioDireccionInline(admin.StackedInline):
    model = NegocioDireccion
    extra = 0


@admin.register(Negocio)
class NegocioAdmin(SimpleHistoryAdmin):
    list_display = ("nombre", "subdominio", "estado", "titular", "rubro", "created")
    list_filter = ("estado", "rubro")
    search_fields = ("nombre", "schema_name", "titular__nombres", "titular__apellidos")
    fields = (
        "nombre",
        "schema_name",
        "titular",
        "rubro",
        "zona_horaria",
        "estado",
        "estado_desde",
        "error_preparacion",
        "notas_internas",
        "creado_por",
        "created",
        "modified",
    )
    readonly_fields = (
        "schema_name",
        "estado",
        "estado_desde",
        "error_preparacion",
        "creado_por",
        "created",
        "modified",
    )
    inlines = [DominioInline, NegocioDireccionInline]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .exclude(schema_name=get_public_schema_name())
            .select_related("titular", "rubro")
            .prefetch_related("domains")
        )

    @admin.display(description="Subdominio")
    def subdominio(self, negocio):
        dominio = next((d for d in negocio.domains.all() if d.is_primary), None)
        return dominio.domain if dominio else "—"

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        list_ajax = BusinessListAjaxView.as_view(
            admin_site=self.admin_site, model_admin=self
        )
        propias = [
            path("list/", list_ajax, name="tenancy_negocio_list_ajax"),
            path(
                "<int:pk>/history/list/",
                BusinessHistoryListAjaxView.as_view(admin_site=self.admin_site, model_admin=self),
                name="tenancy_negocio_history_list",
            ),
            path(
                "alta/",
                self.admin_site.admin_view(self.alta_view),
                name="tenancy_negocio_alta",
            ),
            path(
                "<int:pk>/estado/",
                BusinessStatusModalView.as_view(
                    admin_site=self.admin_site, model_admin=self
                ),
                name="tenancy_negocio_estado",
            ),
            path(
                "<int:pk>/clave-propietario/",
                OwnerPasswordResetModalView.as_view(
                    admin_site=self.admin_site, model_admin=self
                ),
                name="tenancy_negocio_clave_propietario",
            ),
            path(
                "<int:pk>/desbloquear-propietario/",
                OwnerUnlockModalView.as_view(
                    admin_site=self.admin_site, model_admin=self
                ),
                name="tenancy_negocio_desbloquear_propietario",
            ),
            path(
                "<int:pk>/reparar/",
                BusinessRepairModalView.as_view(
                    admin_site=self.admin_site, model_admin=self
                ),
                name="tenancy_negocio_reparar",
            ),
        ]
        return [*propias, *super().get_urls()]

    def changelist_view(self, request, extra_context=None):
        return BusinessListView.as_view(admin_site=self.admin_site, model_admin=self)(
            request
        )

    def add_view(self, request, form_url="", extra_context=None):
        return BusinessCreateView.as_view(admin_site=self.admin_site, model_admin=self)(
            request
        )

    def change_view(self, request, object_id, form_url="", extra_context=None):
        return BusinessUpdateView.as_view(admin_site=self.admin_site, model_admin=self)(
            request, pk=object_id
        )

    def history_view(self, request, object_id, extra_context=None):
        return HistoryModalView.as_view(admin_site=self.admin_site, model_admin=self)(request, pk=object_id)

    def history_form_view(self, request, object_id, version_id, extra_context=None):
        return redirect("admin:tenancy_negocio_change", object_id)

    def alta_view(self, request):
        return redirect("admin:tenancy_negocio_add")
