from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path
from django_tenants.utils import get_public_schema_name, schema_exists
from simple_history.admin import SimpleHistoryAdmin

from apps.tenancy.alta import correo_de_acceso, dar_de_alta
from apps.tenancy.estados import cambiar_estado
from apps.tenancy.forms import AltaNegocioForm, CambiarEstadoForm, RestablecerClavePropietarioForm
from apps.tenancy.models import Dominio, Negocio, NegocioDireccion
from apps.tenancy.propietario import restablecer_clave_del_propietario
from apps.tenancy.tasks import preparar_negocio


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
        propias = [
            path("alta/", self.admin_site.admin_view(self.alta_view), name="tenancy_negocio_alta"),
            path("<int:pk>/estado/", self.admin_site.admin_view(self.estado_view), name="tenancy_negocio_estado"),
            path(
                "<int:pk>/clave-propietario/",
                self.admin_site.admin_view(self.clave_propietario_view),
                name="tenancy_negocio_clave_propietario",
            ),
            path("<int:pk>/reparar/", self.admin_site.admin_view(self.reparar_view), name="tenancy_negocio_reparar"),
        ]
        return [*propias, *super().get_urls()]

    def negocio_del_panel(self, request, pk):
        if not request.user.is_superuser:
            raise PermissionDenied
        return get_object_or_404(self.get_queryset(request), pk=pk)

    def contexto_del_panel(self, request, negocio, titulo, **extra):
        return {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": titulo,
            "negocio": negocio,
            **extra,
        }

    def clave_propietario_view(self, request, pk):
        negocio = self.negocio_del_panel(request, pk)
        if negocio.estado == Negocio.Estado.PREPARANDO or not schema_exists(negocio.schema_name):
            messages.error(request, "El negocio todavía no está listo: primero repara su alta.")
            return redirect("admin:tenancy_negocio_change", negocio.pk)
        form = RestablecerClavePropietarioForm(request.POST if request.method == "POST" else None)
        titulo = f"Restablecer la clave del propietario de «{negocio.nombre}»"
        if request.method == "POST" and form.is_valid():
            resultado = restablecer_clave_del_propietario(negocio, request.user)
            if resultado is None:
                messages.error(request, "Este negocio no tiene propietario: repara su alta.")
                return redirect("admin:tenancy_negocio_change", negocio.pk)
            correo, clave = resultado
            respuesta = TemplateResponse(
                request,
                "admin/tenancy/negocio/clave_propietario.html",
                self.contexto_del_panel(request, negocio, titulo, correo=correo, clave=clave),
            )
            respuesta["Cache-Control"] = "no-store"
            return respuesta
        return TemplateResponse(
            request,
            "admin/tenancy/negocio/clave_propietario.html",
            self.contexto_del_panel(request, negocio, titulo, form=form),
        )

    def reparar_view(self, request, pk):
        negocio = self.negocio_del_panel(request, pk)
        if negocio.estado != Negocio.Estado.PREPARANDO:
            messages.error(request, "Solo se reparan las altas que quedaron en «preparando».")
            return redirect("admin:tenancy_negocio_change", negocio.pk)
        correo = correo_de_acceso(negocio.titular)
        if request.method == "POST":
            if correo is None:
                messages.error(request, "El titular no tiene correo: agrégale uno en su ficha antes de reparar.")
            else:
                preparar_negocio.delay(negocio.pk, correo, None)
                messages.success(request, "La preparación se volvió a encolar. Revisa el estado en unos segundos.")
            return redirect("admin:tenancy_negocio_change", negocio.pk)
        return TemplateResponse(
            request,
            "admin/tenancy/negocio/reparar.html",
            self.contexto_del_panel(request, negocio, f"Reparar el alta de «{negocio.nombre}»", correo=correo),
        )

    def estado_view(self, request, pk):
        if not request.user.is_superuser:
            raise PermissionDenied
        negocio = get_object_or_404(self.get_queryset(request), pk=pk)
        form = CambiarEstadoForm(negocio, request.POST if request.method == "POST" else None)
        if request.method == "POST" and form.is_valid():
            cambiar_estado(negocio, form.cleaned_data["estado"], form.cleaned_data["motivo"], request.user)
            messages.success(request, f"«{negocio.nombre}» quedó {negocio.get_estado_display().lower()}.")
            return redirect("admin:tenancy_negocio_change", negocio.pk)
        return TemplateResponse(
            request,
            "admin/tenancy/negocio/estado.html",
            {
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "title": f"Cambiar el estado de «{negocio.nombre}»",
                "negocio": negocio,
                "form": form,
            },
        )

    def add_view(self, request, form_url="", extra_context=None):
        return redirect("admin:tenancy_negocio_alta")

    def alta_view(self, request):
        if not request.user.is_superuser:
            raise PermissionDenied
        form = AltaNegocioForm(request.POST if request.method == "POST" else None)
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
