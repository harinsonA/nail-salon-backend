from bootstrap_modal_forms.forms import BSModalForm
from bootstrap_modal_forms.generic import BSModalFormView
from django import forms
from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.db.models import Case, Count, Exists, F, OuterRef, Q, Subquery, Value, When
from django.db.models.functions import Concat, Trim
from django.forms import BaseFormSet
from django.http import Http404, JsonResponse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.views.generic import FormView, TemplateView
from django_tenants.utils import get_public_schema_name, schema_exists
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.common.form_classes import (
    FORM_CONTROL_CLASS,
    FORM_SELECT2_CLASS,
    FORM_SELECT_CLASS,
)
from apps.common.form_fields import (
    AlphabeticField,
    NoteField,
    SchemaField,
    SubdomainField,
)
from apps.common.forms import (
    OPTIONAL_FORM_OPTIONS,
    AddressForm,
    MainItemFormSet,
    main_item_formset,
    mark_invalid_fields,
)
from apps.common.utils.businesses import BUSINESS_NAME_MAX_LENGTH
from apps.common.utils.search import contains_ignoring_accents, search_ignoring_accents
from apps.common.utils.utils import get_errors_to_response
from apps.common.widgets import text_input
from apps.panel.views.base import (
    PanelAjaxView,
    PanelListViewAjax,
    PanelView,
    RelatedFormsMixin,
)
from apps.panel.views.history.view import HistoryListAjaxView
from apps.seguridad.access import describe_lock
from apps.tenancy.alta import correo_de_acceso, dar_de_alta, dominio_de, url_en_dominio
from apps.tenancy.estados import cambiar_estado, estados_posibles
from apps.tenancy.models import Dominio, Negocio, NegocioDireccion, Persona, Rubro
from apps.tenancy.models.negocio import FAILED_STATUS_KEY, FAILED_STATUS_LABEL
from apps.tenancy.propietario import (
    owner_lock_status,
    restablecer_clave_del_propietario,
    unlock_owner,
)
from apps.tenancy.tasks import preparar_negocio

"""========================================================================="""
# region ........ Constants


EMPTY = "—"
FAILED_PREPARATION = Q(estado=Negocio.Estado.PREPARANDO, error_preparacion__gt="")
NOT_READY_MESSAGE = "El negocio todavía no está listo: primero repara su alta."
NO_OWNER_MESSAGE = "Este negocio no tiene propietario: repara su alta."
NOT_LOCKED_MESSAGE = "El propietario no estaba bloqueado: no hubo cambios."
NOT_PREPARING_MESSAGE = "Solo se reparan las altas que quedaron en «preparando»."
NO_ACCESS_EMAIL_MESSAGE = (
    "El titular no tiene correo: agrégale uno en su ficha antes de reparar."
)
NO_STATUS_CHANGE_MESSAGE = "Mientras se prepara, el negocio no cambia de estado: queda activo solo al terminar la preparación."
STATUS_DESCRIPTIONS = {
    Negocio.Estado.ACTIVO: "Todos entran y trabajan con normalidad.",
    Negocio.Estado.MOROSO: "El equipo sigue trabajando; propietario y encargado ven el aviso de pago y no entran a la administración.",
    Negocio.Estado.PAUSADO: "Nadie entra: ven «Servicio suspendido».",
    Negocio.Estado.CANCELADO: "Nadie entra; los datos se conservan y se puede reactivar.",
}
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
CODE_INPUT_ATTRS = {
    "autocapitalize": "none",
    "autocomplete": "off",
    "spellcheck": "false",
}


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Helpers


def businesses():
    return Negocio.objects.exclude(schema_name=get_public_schema_name())


def status_key_expression():
    return Case(
        When(FAILED_PREPARATION, then=Value(FAILED_STATUS_KEY)), default=F("estado")
    )


def business_actions(pk, status):
    if status == Negocio.Estado.PREPARANDO:
        actions = [
            {
                "label": "Reparar alta",
                "link": reverse("admin:tenancy_negocio_reparar", args=[pk]),
                "modal": True,
                "in_list": True,
                "icon": "build",
                "description": "Vuelve a lanzar la preparación del negocio con el correo de acceso del titular.",
            }
        ]
    else:
        actions = [
            {
                "label": "Restablecer clave del propietario",
                "link": reverse("admin:tenancy_negocio_clave_propietario", args=[pk]),
                "modal": True,
                "icon": "key",
                "description": "Genera una clave temporal nueva para el propietario, lo desbloquea si estaba bloqueado y la muestra una sola vez.",
            },
            {
                "label": "Desbloquear propietario",
                "link": reverse(
                    "admin:tenancy_negocio_desbloquear_propietario", args=[pk]
                ),
                "modal": True,
                "icon": "lock_open",
                "description": "Quita el bloqueo por intentos fallidos sin cambiarle la clave.",
            },
        ]
    actions.append(
        {
            "label": "Cambiar estado",
            "link": reverse("admin:tenancy_negocio_estado", args=[pk]),
            "modal": True,
            "in_list": True,
            "icon": "sync_alt",
            "description": "Activa, pausa, marca como moroso o cancela el negocio. Pide un motivo para el historial.",
        }
    )
    return actions


def action_option(action):
    option = {"label": action["label"], "link": action["link"], "icon": action["icon"]}
    if action.get("modal"):
        option.update({"bsModal": True, "className": "bs-modal"})
    return option


def has_errors(related_form):
    if isinstance(related_form, BaseFormSet):
        return any(related_form.errors) or bool(related_form.non_form_errors())
    return bool(related_form.errors)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Mixins


class BusinessFormMixin(RelatedFormsMixin):
    template_name = "panel/businesses/form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "list_url": reverse(
                    "admin:tenancy_negocio_changelist", current_app=self.admin_site.name
                ),
                "people_url": reverse(
                    "admin:tenancy_persona_changelist", current_app=self.admin_site.name
                ),
                "sections_with_errors": self.sections_with_errors(context["form"]),
            }
        )
        return context

    def sections_with_errors(self, form):
        if not form.is_bound:
            return []
        sections = {
            "basic": any(name != "notas_internas" for name in form.errors),
            "addresses": has_errors(self.related_forms()["addresses"]),
            "notes": "notas_internas" in form.errors,
        }
        return [name for name, with_errors in sections.items() if with_errors]

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        addresses = self.related_forms()["addresses"]
        if all([form.is_valid(), addresses.is_valid()]):
            return self.form_valid(form)
        mark_invalid_fields(form, addresses)
        return self.form_invalid(form)


class BusinessActionModalMixin(PanelAjaxView):
    def has_model_permission(self, request):
        return request.user.is_superuser and self.model_admin.has_change_permission(
            request, self.get_object()
        )

    def get_object(self):
        if not hasattr(self, "_object"):
            business = self.model_admin.get_object(self.request, str(self.kwargs["pk"]))
            if business is None:
                raise Http404
            self._object = business
        return self._object

    def not_ready_reason(self):
        business = self.get_object()
        if business.estado == Negocio.Estado.PREPARANDO or not schema_exists(
            business.schema_name
        ):
            return NOT_READY_MESSAGE
        return ""

    def business_url(self):
        domain = self.get_object().domains.filter(is_primary=True).first()
        return url_en_dominio(self.request, domain.domain) if domain else ""

    def get(self, request, *args, **kwargs):
        if request.headers.get("x-requested-with") != "XMLHttpRequest":
            return redirect("admin:tenancy_negocio_change", self.get_object().pk)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "modal_url": self.request.path,
            "business": self.get_object(),
            "business_url": self.business_url(),
            "blocked_reason": self.not_ready_reason(),
        }

    def form_invalid(self, form):
        return JsonResponse(
            {"errors": get_errors_to_response(form.errors)}, status=HTTP_400_BAD_REQUEST
        )


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class BusinessesFilterForm(forms.Form):
    status = forms.ChoiceField(
        choices=[
            (ALL, "Todos"),
            (Negocio.Estado.PREPARANDO, Negocio.Estado.PREPARANDO.label),
            (FAILED_STATUS_KEY, FAILED_STATUS_LABEL),
            *(
                choice
                for choice in Negocio.Estado.choices
                if choice[0] != Negocio.Estado.PREPARANDO
            ),
        ],
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
            filters["status_key"] = cleaned_data["status"]
        if cleaned_data.get("industry"):
            filters["rubro"] = cleaned_data["industry"]
        return filters


class OwnerPasswordResetForm(BSModalForm):
    identity_confirmed = forms.BooleanField(
        label="Confirmé la identidad del titular",
        help_text="Por ejemplo, llamándolo a su teléfono registrado antes de entregarle la clave.",
        error_messages={
            "required": "Confirma la identidad del titular antes de generar la clave."
        },
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )


class ConfirmActionForm(BSModalForm):
    pass


class BusinessStatusForm(BSModalForm):
    estado = forms.ChoiceField(
        label="Nuevo estado",
        widget=forms.Select(attrs={"class": FORM_SELECT_CLASS}),
    )
    motivo = NoteField(
        label="Motivo",
        help_text="Queda en el historial del negocio: por ejemplo, «dos meses sin pago». Hasta 250 caracteres.",
        widget=forms.Textarea(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "Dos meses sin pago.",
                "rows": 3,
            }
        ),
    )

    def __init__(self, *args, business=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["estado"].choices = [
            ("", "Selecciona un estado"),
            *((status.value, status.label) for status in estados_posibles(business)),
        ]


class BusinessAddressForm(AddressForm):
    class Meta(AddressForm.Meta):
        model = NegocioDireccion


class BusinessSettingsForm(forms.Form):
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


class BusinessCreateForm(BusinessSettingsForm):
    field_order = [
        "nombre",
        "subdominio",
        "esquema",
        "titular",
        "correo",
        "rubro",
        "zona_horaria",
        "notas_internas",
    ]

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
        empty_label="Selecciona un propietario",
        help_text="Si el propietario no existe, créalo primero en Propietarios.",
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
        if Negocio.objects.filter(schema_name=esquema).exists() or schema_exists(
            esquema
        ):
            raise forms.ValidationError(
                "Ya existe un esquema con ese nombre en la base."
            )
        return esquema

    def clean_correo(self):
        return self.cleaned_data["correo"].strip().lower()


class BusinessUpdateForm(BusinessSettingsForm):
    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)
        self.fields["rubro"].queryset = Rubro.objects.filter(
            Q(activo=True) | Q(pk=instance.rubro_id)
        )
        self.initial.update(
            {
                "rubro": instance.rubro_id,
                "zona_horaria": instance.zona_horaria,
                "notas_internas": instance.notas_internas or "",
            }
        )

    def save(self):
        business = self.instance
        business.rubro = self.cleaned_data["rubro"]
        business.zona_horaria = self.cleaned_data["zona_horaria"]
        business.notas_internas = self.cleaned_data["notas_internas"] or None
        business._change_reason = "Edición desde el panel"
        business.save()
        return business


class BusinessAddressFormSet(MainItemFormSet):
    item_name = "una dirección"


AddressFormSet = main_item_formset(Negocio, BusinessAddressForm, BusinessAddressFormSet)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class BusinessListView(PanelView, TemplateView):
    template_name = "panel/businesses/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_add = (
            self.request.user.is_superuser
            and self.model_admin.has_add_permission(self.request)
        )
        context.update(
            {
                "filter_form": BusinessesFilterForm(),
                "list_url": reverse(
                    "admin:tenancy_negocio_list_ajax", current_app=self.admin_site.name
                ),
                "add_url": reverse(
                    "admin:tenancy_negocio_add", current_app=self.admin_site.name
                )
                if can_add
                else "",
            }
        )
        return context


class BusinessListAjaxView(PanelListViewAjax):
    model = Negocio
    filter_form_class = BusinessesFilterForm
    field_list = [
        "pk",
        "nombre",
        "domain",
        "estado",
        "status_key",
        "owner_name",
        "industry_name",
        "created",
    ]
    ordering_fields = {
        "0": "nombre",
        "1": "domain",
        "2": "estado",
        "3": "owner_name",
        "4": "industry_name",
        "5": "created",
    }

    def get_queryset(self):
        primary_domain = Dominio.objects.filter(
            tenant=OuterRef("pk"), is_primary=True
        ).values("domain")[:1]
        return (
            businesses()
            .annotate(
                domain=Subquery(primary_domain),
                owner_name=Trim(
                    Concat("titular__nombres", Value(" "), "titular__apellidos")
                ),
                industry_name=F("rubro__nombre"),
                status_key=status_key_expression(),
            )
            .filter(**self.get_filters())
        )

    def get_filter_by_search(self):
        search_value = self.request.GET.get("search[value]", "")
        if not search_value:
            return Q()
        domains = Dominio.objects.filter(
            contains_ignoring_accents("domain", search_value), tenant=OuterRef("pk")
        )
        return (
            search_ignoring_accents(
                ["nombre", "schema_name", "titular__nombres", "titular__apellidos"],
                search_value,
            )
            | Q(Exists(domains))
        )

    def get_values(self, queryset):
        labels = {
            **dict(Negocio.Estado.choices),
            FAILED_STATUS_KEY: FAILED_STATUS_LABEL,
        }
        values = super().get_values(queryset)
        for value in values:
            value["status_label"] = labels.get(value["status_key"], value["status_key"])
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
                        "link": reverse(
                            "admin:tenancy_negocio_change", args=[item["pk"]]
                        ),
                        "icon": "edit_document",
                    }
                )
            if is_superuser:
                options += [
                    action_option(action)
                    for action in business_actions(item["pk"], item["estado"])
                    if action.get("in_list")
                ]
            item["options"] = options
        return data

    @staticmethod
    def additional_data(queryset):
        return businesses().aggregate(
            total_businesses=Count("pk"),
            active_businesses=Count("pk", filter=Q(estado=Negocio.Estado.ACTIVO)),
            overdue_businesses=Count("pk", filter=Q(estado=Negocio.Estado.MOROSO)),
            preparing_businesses=Count(
                "pk", filter=Q(estado=Negocio.Estado.PREPARANDO) & ~FAILED_PREPARATION
            ),
            failed_businesses=Count("pk", filter=FAILED_PREPARATION),
        )


class BusinessCreateView(BusinessFormMixin, PanelView, FormView):
    form_class = BusinessCreateForm

    def has_model_permission(self, request):
        return request.user.is_superuser and self.model_admin.has_add_permission(
            request
        )

    def get_related_forms(self, data):
        return {
            "addresses": BusinessAddressForm(
                data, prefix="address", **OPTIONAL_FORM_OPTIONS
            )
        }

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "title": "Nuevo negocio"}

    def form_valid(self, form):
        address_form = self.related_forms()["addresses"]
        address = (
            address_form.save(commit=False) if address_form.has_changed() else None
        )
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
                "business_url": url_en_dominio(
                    self.request, business.domains.get(is_primary=True).domain
                ),
                "list_url": reverse(
                    "admin:tenancy_negocio_changelist", current_app=self.admin_site.name
                ),
            },
        )
        response["Cache-Control"] = "no-store"
        return response


class BusinessUpdateView(BusinessFormMixin, PanelView, FormView):
    form_class = BusinessUpdateForm

    def has_model_permission(self, request):
        return request.user.is_superuser and self.model_admin.has_change_permission(
            request, self.get_object()
        )

    def get_object(self):
        if not hasattr(self, "_object"):
            business = self.model_admin.get_object(self.request, str(self.kwargs["pk"]))
            if business is None:
                raise Http404
            self._object = business
        return self._object

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "instance": self.get_object()}

    def get_related_forms(self, data):
        return {
            "addresses": AddressFormSet(
                data, instance=self.get_object(), prefix="direcciones"
            )
        }

    def owner_access(self, business):
        if business.estado == Negocio.Estado.PREPARANDO or not schema_exists(
            business.schema_name
        ):
            return None
        return owner_lock_status(business)

    def get_context_data(self, **kwargs):
        business = self.get_object()
        domain = business.domains.filter(is_primary=True).first()
        owner_access = self.owner_access(business)
        return {
            **super().get_context_data(**kwargs),
            "title": f"Editar negocio · {business.nombre}",
            "business": business,
            "domain": domain.domain if domain else EMPTY,
            "business_url": url_en_dominio(self.request, domain.domain)
            if domain
            else "",
            "access_email": correo_de_acceso(business.titular)
            if business.titular
            else None,
            "owner_access": describe_lock(owner_access) if owner_access else "",
            "owner_locked": bool(owner_access and owner_access.is_locked),
            "actions": [
                *business_actions(business.pk, business.estado),
                {
                    "label": "Ver historial",
                    "link": reverse(
                        "admin:tenancy_negocio_history", args=[business.pk]
                    ),
                    "modal": True,
                    "modal_size": "xl",
                    "icon": "history",
                    "description": "Todos los cambios del negocio, con quién los hizo y su motivo.",
                },
            ],
        }

    def form_valid(self, form):
        addresses = self.related_forms()["addresses"]
        with transaction.atomic():
            business = form.save()
            addresses.save()
        changed = [str(form.fields[name].label) for name in form.changed_data]
        if addresses.has_changed():
            changed.append("Direcciones")
        self.model_admin.log_change(
            self.request,
            business,
            [{"changed": {"fields": changed}}] if changed else [],
        )
        messages.success(
            self.request, f"«{business.nombre}» se actualizó exitosamente."
        )
        return redirect("admin:tenancy_negocio_change", business.pk)


class OwnerPasswordResetModalView(BusinessActionModalMixin, BSModalFormView):
    template_name = "panel/businesses/owner_password_modal.html"
    form_class = OwnerPasswordResetForm

    def form_valid(self, form):
        reason = self.not_ready_reason()
        if reason:
            return JsonResponse({"message": reason}, status=HTTP_400_BAD_REQUEST)
        business = self.get_object()
        result = restablecer_clave_del_propietario(business, self.request.user)
        if result is None:
            return JsonResponse(
                {"message": NO_OWNER_MESSAGE}, status=HTTP_400_BAD_REQUEST
            )
        email, password = result
        self.model_admin.log_change(
            self.request, business, "Clave del propietario restablecida."
        )
        response = JsonResponse(
            {
                "message": "Se generó una clave temporal nueva.",
                "email": email,
                "password": password,
            }
        )
        response["Cache-Control"] = "no-store"
        return response


class OwnerUnlockModalView(BusinessActionModalMixin, BSModalFormView):
    template_name = "panel/businesses/owner_unlock_modal.html"
    form_class = ConfirmActionForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if context["blocked_reason"]:
            return context
        status = owner_lock_status(self.get_object())
        if status is None:
            context["blocked_reason"] = NO_OWNER_MESSAGE
            return context
        return {**context, "status": status, "lock_description": describe_lock(status)}

    def form_valid(self, form):
        reason = self.not_ready_reason()
        if reason:
            return JsonResponse({"message": reason}, status=HTTP_400_BAD_REQUEST)
        business = self.get_object()
        result = unlock_owner(business, self.request.user)
        if result is None:
            return JsonResponse(
                {"message": NO_OWNER_MESSAGE}, status=HTTP_400_BAD_REQUEST
            )
        email, unlocked = result
        if not unlocked:
            return JsonResponse(
                {"message": NOT_LOCKED_MESSAGE}, status=HTTP_400_BAD_REQUEST
            )
        self.model_admin.log_change(self.request, business, "Propietario desbloqueado.")
        return JsonResponse(
            {"message": "El propietario quedó desbloqueado.", "email": email}
        )


class BusinessStatusModalView(BusinessActionModalMixin, BSModalFormView):
    template_name = "panel/businesses/business_status_modal.html"
    form_class = BusinessStatusForm

    def not_ready_reason(self):
        return "" if estados_posibles(self.get_object()) else NO_STATUS_CHANGE_MESSAGE

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "business": self.get_object()}

    def get_context_data(self, **kwargs):
        business = self.get_object()
        return {
            **super().get_context_data(**kwargs),
            "status_options": [
                {"label": status.label, "description": STATUS_DESCRIPTIONS[status]}
                for status in estados_posibles(business)
            ],
        }

    def form_valid(self, form):
        reason = self.not_ready_reason()
        if reason:
            return JsonResponse({"message": reason}, status=HTTP_400_BAD_REQUEST)
        business = self.get_object()
        cambiar_estado(
            business,
            form.cleaned_data["estado"],
            form.cleaned_data["motivo"],
            self.request.user,
        )
        status = business.get_estado_display()
        self.model_admin.log_change(
            self.request,
            business,
            f"Estado cambiado a {status}: {form.cleaned_data['motivo']}",
        )
        return JsonResponse(
            {
                "message": f"«{business.nombre}» quedó {status.lower()}.",
                "status": status,
                "reason": form.cleaned_data["motivo"],
            }
        )


class BusinessRepairModalView(BusinessActionModalMixin, BSModalFormView):
    template_name = "panel/businesses/business_repair_modal.html"
    form_class = ConfirmActionForm

    def access_email(self):
        titular = self.get_object().titular
        return correo_de_acceso(titular) if titular else None

    def not_ready_reason(self):
        if self.get_object().estado != Negocio.Estado.PREPARANDO:
            return NOT_PREPARING_MESSAGE
        if self.access_email() is None:
            return NO_ACCESS_EMAIL_MESSAGE
        return ""

    def get_context_data(self, **kwargs):
        return {
            **super().get_context_data(**kwargs),
            "access_email": self.access_email(),
        }

    def form_valid(self, form):
        reason = self.not_ready_reason()
        if reason:
            return JsonResponse({"message": reason}, status=HTTP_400_BAD_REQUEST)
        business = self.get_object()
        email = self.access_email()
        preparar_negocio.delay(business.pk, email, None)
        self.model_admin.log_change(
            self.request, business, "Preparación encolada de nuevo."
        )
        return JsonResponse(
            {"message": "La preparación se volvió a encolar.", "email": email}
        )


class BusinessHistoryListAjaxView(HistoryListAjaxView):
    ignored_fields = ("modified", "estado_desde")
    field_labels = {
        "schema_name": "Esquema",
        "zona_horaria": "Zona horaria",
        "error_preparacion": "Error de preparación",
        "notas_internas": "Notas internas",
        "creado_por": "Creado por",
    }


# endregion
"""========================================================================="""
