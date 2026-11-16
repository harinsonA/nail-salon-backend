from bootstrap_modal_forms.forms import BSModalForm
from bootstrap_modal_forms.generic import BSModalFormView
from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView
from rest_framework.status import HTTP_400_BAD_REQUEST

from apps.common.form_classes import FORM_CONTROL_CLASS
from apps.common.form_fields import NoteField
from apps.common.utils.search import search_ignoring_accents
from apps.common.utils.utils import get_errors_to_response
from apps.panel.views.base import PanelAjaxView, PanelListViewAjax, PanelView
from apps.panel.views.history.view import (
    EMPTY,
    HISTORY_ACTIONS,
    author_of,
    format_datetime,
    summary_of,
)
from apps.settings.preferences.constants import Scope
from apps.settings.preferences.models import Preference
from apps.settings.preferences.registry import (
    APP_LATEST_VERSION,
    APP_MAINTENANCE,
    APP_MAINTENANCE_MESSAGE,
    APP_MINIMUM_VERSION,
)
from apps.settings.preferences.service import get_preferences, set_preference
from apps.settings.preferences.versions import AppVersion

"""========================================================================="""
# region ........ Constants


APP_PREFERENCES = (
    APP_MINIMUM_VERSION,
    APP_LATEST_VERSION,
    APP_MAINTENANCE,
    APP_MAINTENANCE_MESSAGE,
)
APP_PREFERENCE_KEYS = [definition.key for definition in APP_PREFERENCES]
EMPTY_LABELS = {
    APP_MINIMUM_VERSION.key: "Sin mínima",
    APP_LATEST_VERSION.key: "Sin registrar",
    APP_MAINTENANCE_MESSAGE.key: "Texto por defecto",
}
BOOLEAN_LABELS = {True: "Encendido", False: "Apagado"}
PANEL_REASON = "Edición desde el panel"
SUCCESS_MESSAGE = "App móvil actualizada exitosamente."
NO_CHANGES_MESSAGE = "No hubo cambios que guardar."
HISTORY_TITLE = "App móvil"
VERSION_PLACEHOLDER = "1.4.0"


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Helpers


def display_preference(definition, value):
    if isinstance(value, bool):
        return BOOLEAN_LABELS[value]
    if value in (None, ""):
        return EMPTY_LABELS.get(definition.key, EMPTY)
    return str(value)


def stored_value(definition, record):
    if record is None:
        return definition.default
    return definition.deserialize(record.value)


def preference_rows(values):
    return [
        {
            "key": definition.key,
            "label": definition.label,
            "help_text": definition.help_text,
            "value": display_preference(definition, values[definition.key]),
            "is_flag": isinstance(values[definition.key], bool),
            "flag": values[definition.key] is True,
        }
        for definition in APP_PREFERENCES
    ]


def app_preference_history():
    return Preference.history.filter(
        scope=Scope.PLATAFORMA, scope_id="", key__in=APP_PREFERENCE_KEYS
    ).select_related("history_user")


def record_changes(record):
    definition = next(item for item in APP_PREFERENCES if item.key == record.key)
    previous = None if record.history_type == "+" else record.prev_record
    old = stored_value(definition, previous)
    new = stored_value(definition, record)
    if record.history_type == "-" or old == new:
        return []
    return [
        {
            "field": definition.label,
            "old": display_preference(definition, old),
            "new": display_preference(definition, new),
        }
    ]


def history_row(record):
    action_key, action_label = HISTORY_ACTIONS.get(record.history_type, ("updated", "Modificado"))
    return {
        "pk": record.pk,
        "date": format_datetime(record.history_date),
        "author": author_of(record),
        "action_key": action_key,
        "action": action_label,
        "reason": record.history_change_reason or EMPTY,
        "changes": record_changes(record),
    }


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Forms


class VersionField(forms.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault(
            "widget",
            forms.TextInput(
                attrs={
                    "class": FORM_CONTROL_CLASS,
                    "placeholder": VERSION_PLACEHOLDER,
                    "maxlength": 20,
                    "inputmode": "decimal",
                    "autocomplete": "off",
                }
            ),
        )
        super().__init__(*args, **kwargs)

    def clean(self, value):
        try:
            return AppVersion.clean(super().clean(value))
        except ValidationError as error:
            raise forms.ValidationError(error.messages)


class AppMobileForm(BSModalForm):
    app_version_minima = VersionField(
        label=APP_MINIMUM_VERSION.label,
        help_text="Quien tenga una versión anterior no puede usar la app hasta actualizar. Vacía, no bloquea a nadie.",
    )
    app_version_ultima = VersionField(
        label=APP_LATEST_VERSION.label,
        help_text="La registra la publicación automática; mientras no exista, se escribe aquí. Vacía, no sugiere actualizar.",
    )
    app_mantenimiento = forms.BooleanField(
        label=APP_MAINTENANCE.label,
        help_text=APP_MAINTENANCE.help_text,
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input", "role": "switch"}),
    )
    app_mantenimiento_mensaje = NoteField(
        label=APP_MAINTENANCE_MESSAGE.label,
        help_text=APP_MAINTENANCE_MESSAGE.help_text,
        required=False,
        widget=forms.Textarea(attrs={"class": FORM_CONTROL_CLASS, "rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current = get_preferences(APP_PREFERENCE_KEYS)
        self.initial.update(self.current)

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data
        try:
            AppVersion.check_range(
                cleaned_data[APP_MINIMUM_VERSION.key], cleaned_data[APP_LATEST_VERSION.key]
            )
        except ValidationError as error:
            self.add_error(APP_MINIMUM_VERSION.key, error.messages)
        return cleaned_data

    def changed_keys(self):
        return [key for key in APP_PREFERENCE_KEYS if self.cleaned_data[key] != self.current[key]]

    def save(self):
        changed = self.changed_keys()
        for key in changed:
            set_preference(key, self.cleaned_data[key], reason=PANEL_REASON)
        return changed


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class AppMobileView(PanelView, TemplateView):
    template_name = "panel/app_mobile/detail.html"

    def get_context_data(self, **kwargs):
        can_change = self.model_admin.has_change_permission(self.request)
        return {
            **super().get_context_data(**kwargs),
            "rows": preference_rows(get_preferences(APP_PREFERENCE_KEYS)),
            "change_modal_url": (
                reverse("admin:settings_preferenciaplataforma_change_modal", current_app=self.admin_site.name)
                if can_change
                else ""
            ),
            "history_modal_url": reverse(
                "admin:settings_preferenciaplataforma_history_modal", current_app=self.admin_site.name
            ),
        }


class AppMobileUpdateModalView(PanelAjaxView, BSModalFormView):
    template_name = "panel/app_mobile/app_mobile_modal.html"
    form_class = AppMobileForm

    def has_model_permission(self, request):
        return self.model_admin.has_change_permission(request)

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "modal_url": self.request.path}

    def form_invalid(self, form):
        return JsonResponse(
            {"errors": get_errors_to_response(form.errors)}, status=HTTP_400_BAD_REQUEST
        )

    def form_valid(self, form):
        changed = form.save()
        return JsonResponse({"message": SUCCESS_MESSAGE if changed else NO_CHANGES_MESSAGE})


class AppMobileHistoryModalView(PanelAjaxView, TemplateView):
    template_name = "panel/history_modal.html"

    def get(self, request, *args, **kwargs):
        if request.headers.get("x-requested-with") != "XMLHttpRequest":
            return redirect("admin:settings_preferenciaplataforma_changelist")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        history = app_preference_history()
        return {
            **super().get_context_data(**kwargs),
            "object": HISTORY_TITLE,
            "total": history.count(),
            "created": summary_of(history.order_by("history_date").first()),
            "last_change": summary_of(history.order_by("-history_date").first()),
            "list_url": reverse(
                "admin:settings_preferenciaplataforma_history_list", current_app=self.admin_site.name
            ),
        }


class AppMobileHistoryListAjaxView(PanelListViewAjax):
    include_options_column = False
    ordering_fields = {
        "1": "history_date",
        "2": "history_user__username",
        "3": "history_type",
        "4": "history_change_reason",
    }

    def get_queryset(self):
        return app_preference_history()

    def get_order_by(self):
        if self.request.GET.get("order[0][column]") not in self.ordering_fields:
            return ("-history_date",)
        return super().get_order_by()

    def get_filter_by_search(self):
        search_value = self.request.GET.get("search[value]", "").strip()
        if not search_value:
            return Q()
        return search_ignoring_accents(
            [
                "history_change_reason",
                "history_user__username",
                "history_user__first_name",
                "history_user__last_name",
            ],
            search_value,
        )

    def get_values(self, queryset):
        return [history_row(record) for record in queryset]


# endregion
"""========================================================================="""
