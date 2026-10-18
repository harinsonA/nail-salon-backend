from django import forms
from django.conf import settings
from django.db.models import Count, Exists, F, OuterRef, Q, Subquery, Value
from django.db.models.functions import Concat, Trim
from django.urls import reverse
from django.template.response import TemplateResponse
from django.utils import timezone
from django.views.generic import FormView, TemplateView
from django_tenants.utils import get_public_schema_name, schema_exists

from apps.common.form_classes import FORM_CONTROL_CLASS, FORM_SELECT2_CLASS, FORM_SELECT_CLASS
from apps.common.form_fields import AlphabeticField, NoteField, SchemaField, SubdomainField
from apps.common.forms import OPTIONAL_FORM_OPTIONS, AddressForm, mark_invalid_fields
from apps.common.utils.businesses import BUSINESS_NAME_MAX_LENGTH
from apps.common.widgets import text_input
from apps.panel.views.base import PanelListViewAjax, PanelView, RelatedFormsMixin
from apps.tenancy.alta import dar_de_alta, dominio_de, url_en_dominio
from apps.tenancy.models import Dominio, Negocio, NegocioDireccion, Persona, Rubro

"""========================================================================="""
# region ........ Constants


EMPTY = "—"
ALL = "all"
DEFAULT_TIME_ZONE = "America/Santiago"
TIME_ZONES = [
    ("America/Santiago", "Chile (Santiago)"),
    ("America/Argentina/Buenos_Aires", "Argentina (Buenos Aires)"),
    ("America/Bogota", "Colombia (Bogotá)"),
    ("America/Guayaquil", "Ecuador (Guayaquil)"),
    ("America/Mexico_City", "México (Ciudad de México)"),
    ("America/Lima", "Perú (Lima)"),
    ("America/Santo_Domingo", "República Dominicana (Santo Domingo)"),
    ("America/Montevideo", "Uruguay (Montevideo)"),
    ("America/Caracas", "Venezuela (Caracas)"),
]
CODE_INPUT_ATTRS = {"autocapitalize": "none", "autocomplete": "off", "spellcheck": "false"}


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Helpers


def businesses():
    return Negocio.objects.exclude(schema_name=get_public_schema_name())


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class BusinessesFilterForm(forms.Form):
    status = forms.ChoiceField(
        choices=[(ALL, "Todos"), *Negocio.Estado.choices],
        label="Estado",
        initial=ALL,
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    industry = forms.ModelChoiceField(
        queryset=Rubro.objects.all(),
        label="Rubro",
        empty_label="Todos",
        required=False,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )

    def clean(self):
        cleaned_data = super().clean()
        filters = {}
        if cleaned_data.get("status") not in (None, "", ALL):
            filters["estado"] = cleaned_data["status"]
        if cleaned_data.get("industry"):
            filters["rubro"] = cleaned_data["industry"]
        return filters


class BusinessAddressForm(AddressForm):
    class Meta(AddressForm.Meta):
        model = NegocioDireccion


class BusinessCreateForm(forms.Form):
    nombre = AlphabeticField(
        label="Nombre del negocio",
        max_length=150,
        widget=text_input("Barbería El Corte"),
    )
    subdominio = SubdomainField(
        label="Subdominio",
        max_length=BUSINESS_NAME_MAX_LENGTH,
        widget=text_input("el-corte", **CODE_INPUT_ATTRS),
    )
    esquema = SchemaField(
        label="Esquema",
        max_length=BUSINESS_NAME_MAX_LENGTH,
        help_text=(
            "Nombre interno de la base del negocio: minúsculas sin tilde separadas con guion bajo. "
            "Se completa con el subdominio, pero puedes cambiarlo."
        ),
        widget=text_input("el_corte", **CODE_INPUT_ATTRS),
    )
    titular = forms.ModelChoiceField(
        label="Titular",
        queryset=Persona.objects.order_by("nombres", "apellidos"),
        empty_label="Selecciona una persona",
        help_text="Si la persona no existe, créala primero en Personas.",
        widget=forms.Select(attrs={"class": FORM_SELECT2_CLASS}),
    )
    correo = forms.EmailField(
        label="Correo de acceso del propietario",
        max_length=254,
        help_text="Con este correo entra a su negocio. Si el titular no lo tiene, se suma a su ficha.",
        widget=forms.EmailInput(
            attrs={"class": FORM_CONTROL_CLASS, "placeholder": "carlos@elcorte.cl"}
        ),
    )
    rubro = forms.ModelChoiceField(
        label="Rubro",
        queryset=Rubro.objects.filter(activo=True),
        empty_label="Selecciona un rubro",
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    zona_horaria = forms.ChoiceField(
        label="Zona horaria",
        choices=TIME_ZONES,
        initial=DEFAULT_TIME_ZONE,
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    notas_internas = NoteField(
        label="Notas internas",
        required=False,
        help_text="Solo las ve el equipo de Hi Agenda. Hasta 250 caracteres.",
        widget=forms.Textarea(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "Acordamos el primer mes sin costo.",
                "rows": 4,
            }
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subdominio"].help_text = (
            "Minúsculas sin tilde separadas con guion. Será la dirección del negocio: "
            f"subdominio.{settings.DOMINIO_BASE}"
        )

    def clean_subdominio(self):
        subdominio = self.cleaned_data["subdominio"]
        if Dominio.objects.filter(domain=dominio_de(subdominio)).exists():
            raise forms.ValidationError("Ese subdominio ya lo usa otro negocio.")
        return subdominio

    def clean_esquema(self):
        esquema = self.cleaned_data["esquema"]
        if Negocio.objects.filter(schema_name=esquema).exists() or schema_exists(esquema):
            raise forms.ValidationError("Ya existe un esquema con ese nombre en la base.")
        return esquema

    def clean_correo(self):
        return self.cleaned_data["correo"].strip().lower()


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class BusinessListView(PanelView, TemplateView):
    template_name = "panel/businesses/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_add = self.request.user.is_superuser and self.model_admin.has_add_permission(self.request)
        context.update(
            {
                "filter_form": BusinessesFilterForm(),
                "list_url": reverse("admin:tenancy_negocio_list_ajax", current_app=self.admin_site.name),
                "add_url": reverse("admin:tenancy_negocio_add", current_app=self.admin_site.name) if can_add else "",
            }
        )
        return context


class BusinessListAjaxView(PanelListViewAjax):
    model = Negocio
    filter_form_class = BusinessesFilterForm
    field_list = ["pk", "nombre", "domain", "estado", "owner_name", "industry_name", "created"]
    ordering_fields = {
        "0": "nombre",
        "1": "domain",
        "2": "estado",
        "3": "owner_name",
        "4": "industry_name",
        "5": "created",
    }

    def get_queryset(self):
        primary_domain = Dominio.objects.filter(tenant=OuterRef("pk"), is_primary=True).values("domain")[:1]
        return (
            businesses()
            .annotate(
                domain=Subquery(primary_domain),
                owner_name=Trim(Concat("titular__nombres", Value(" "), "titular__apellidos")),
                industry_name=F("rubro__nombre"),
            )
            .filter(**self.get_filters())
        )

    def get_filter_by_search(self):
        search_value = self.request.GET.get("search[value]", "")
        if not search_value:
            return Q()
        domains = Dominio.objects.filter(tenant=OuterRef("pk"), domain__icontains=search_value)
        return (
            Q(nombre__icontains=search_value)
            | Q(schema_name__icontains=search_value)
            | Q(titular__nombres__icontains=search_value)
            | Q(titular__apellidos__icontains=search_value)
            | Q(Exists(domains))
        )

    def get_values(self, queryset):
        labels = dict(Negocio.Estado.choices)
        values = super().get_values(queryset)
        for value in values:
            value["status_label"] = labels.get(value["estado"], value["estado"])
            value["domain"] = value["domain"] or EMPTY
            value["industry_name"] = value["industry_name"] or EMPTY
            value["created"] = timezone.localtime(value["created"]).strftime("%d/%m/%Y")
        return values

    def add_options_column(self, data):
        can_change = self.model_admin.has_change_permission(self.request)
        is_superuser = self.request.user.is_superuser
        for item in data:
            options = []
            if can_change:
                options.append(
                    {
                        "label": "Editar",
                        "link": reverse("admin:tenancy_negocio_change", args=[item["pk"]]),
                        "icon": "edit_document",
                    }
                )
            if is_superuser:
                if item["estado"] == Negocio.Estado.PREPARANDO:
                    options.append(
                        {"label": "Reparar alta", "link": reverse("admin:tenancy_negocio_reparar", args=[item["pk"]])}
                    )
                else:
                    options.append(
                        {
                            "label": "Restablecer clave del propietario",
                            "link": reverse("admin:tenancy_negocio_clave_propietario", args=[item["pk"]]),
                        }
                    )
                options.append(
                    {"label": "Cambiar estado", "link": reverse("admin:tenancy_negocio_estado", args=[item["pk"]])}
                )
            item["options"] = options
        return data

    @staticmethod
    def additional_data(queryset):
        return businesses().aggregate(
            total_businesses=Count("pk"),
            active_businesses=Count("pk", filter=Q(estado=Negocio.Estado.ACTIVO)),
            overdue_businesses=Count("pk", filter=Q(estado=Negocio.Estado.MOROSO)),
            preparing_businesses=Count("pk", filter=Q(estado=Negocio.Estado.PREPARANDO)),
        )


class BusinessCreateView(RelatedFormsMixin, PanelView, FormView):
    template_name = "panel/businesses/create.html"
    form_class = BusinessCreateForm

    def has_model_permission(self, request):
        return request.user.is_superuser and self.model_admin.has_add_permission(request)

    def get_related_forms(self, data):
        return {"address_form": BusinessAddressForm(data, prefix="address", **OPTIONAL_FORM_OPTIONS)}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "title": "Nuevo negocio",
                "list_url": reverse("admin:tenancy_negocio_changelist", current_app=self.admin_site.name),
                "people_url": reverse("admin:tenancy_persona_changelist", current_app=self.admin_site.name),
                "sections_with_errors": self.sections_with_errors(context["form"]),
            }
        )
        return context

    def sections_with_errors(self, form):
        if not form.is_bound:
            return []
        sections = {
            "basic": any(name != "notas_internas" for name in form.errors),
            "address": bool(self.related_forms()["address_form"].errors),
            "notes": "notas_internas" in form.errors,
        }
        return [name for name, has_errors in sections.items() if has_errors]

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        address_form = self.related_forms()["address_form"]
        if all([form.is_valid(), address_form.is_valid()]):
            return self.form_valid(form)
        mark_invalid_fields(form, address_form)
        return self.form_invalid(form)

    def form_valid(self, form):
        address_form = self.related_forms()["address_form"]
        address = address_form.save(commit=False) if address_form.has_changed() else None
        business, password = dar_de_alta(form.cleaned_data, self.request.user, address)
        self.model_admin.log_addition(self.request, business, [{"added": {}}])
        response = TemplateResponse(
            self.request,
            "panel/businesses/created.html",
            {
                **self.admin_site.each_context(self.request),
                "title": "Negocio creado",
                "business": business,
                "email": form.cleaned_data["correo"],
                "password": password,
                "business_url": url_en_dominio(self.request, business.domains.get(is_primary=True).domain),
                "list_url": reverse("admin:tenancy_negocio_changelist", current_app=self.admin_site.name),
            },
        )
        response["Cache-Control"] = "no-store"
        return response


# endregion
"""========================================================================="""
