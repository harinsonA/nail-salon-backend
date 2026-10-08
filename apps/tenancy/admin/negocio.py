from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import path
from django_tenants.utils import get_public_schema_name
from simple_history.admin import SimpleHistoryAdmin

from apps.tenancy.alta import dar_de_alta
from apps.tenancy.forms import AltaNegocioForm
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
        alta = path("alta/", self.admin_site.admin_view(self.alta_view), name="tenancy_negocio_alta")
        return [alta, *super().get_urls()]

    def add_view(self, request, form_url="", extra_context=None):
        return redirect("admin:tenancy_negocio_alta")

    def alta_view(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied
        form = AltaNegocioForm(request.POST or None)
        contexto = {**self.admin_site.each_context(request), "opts": self.model._meta}
        if request.method == "POST" and form.is_valid():
            negocio, clave = dar_de_alta(form.cleaned_data, request.user)
            respuesta = TemplateResponse(
                request,
                "admin/tenancy/negocio/alta_lista.html",
                {
                    **contexto,
                    "title": "Negocio dado de alta",
                    "negocio": negocio,
                    "correo": form.cleaned_data["correo"],
                    "clave": clave,
                    "url_negocio": self.url_del_negocio(request, negocio),
                },
            )
            respuesta["Cache-Control"] = "no-store"
            return respuesta
        return TemplateResponse(
            request,
            "admin/tenancy/negocio/alta.html",
            {**contexto, "title": "Dar de alta un negocio", "form": form},
        )

    @staticmethod
    def url_del_negocio(request, negocio):
        dominio = negocio.domains.get(is_primary=True).domain
        puerto = request.get_port()
        sufijo = "" if puerto in ("80", "443") else f":{puerto}"
        return f"{request.scheme}://{dominio}{sufijo}/"
