from datetime import datetime

from django.db.models import Q
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from apps.panel.views.base import PanelAjaxView, PanelListViewAjax

"""========================================================================="""
# region ........ Constants


EMPTY = "—"
SYSTEM_AUTHOR = "Sistema"
DATETIME_FORMAT = "%d/%m/%Y %H:%M"
HISTORY_ACTIONS = {
    "+": ("created", "Creado"),
    "~": ("updated", "Modificado"),
    "-": ("deleted", "Eliminado"),
}
DEFAULT_IGNORED_FIELDS = ("modified",)


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Helpers


def format_datetime(value):
    return timezone.localtime(value).strftime(DATETIME_FORMAT)


def author_of(record):
    user = record.history_user
    if user is None:
        return SYSTEM_AUTHOR
    return user.get_full_name() or user.get_username()


def related_label(field, value):
    model = field.related_model
    manager = getattr(model, "all_objects", model._default_manager)
    related = manager.filter(pk=value).first()
    return str(related) if related else f"#{value}"


def display_value(model, field_name, value):
    if value in (None, ""):
        return EMPTY
    field = model._meta.get_field(field_name)
    if field.choices:
        return str(dict(field.flatchoices).get(value, value))
    if field.is_relation:
        return related_label(field, value)
    if isinstance(value, bool):
        return "Sí" if value else "No"
    if isinstance(value, datetime):
        return format_datetime(value)
    return str(value)


def field_label(model, field_name, field_labels):
    if field_name in field_labels:
        return field_labels[field_name]
    return str(model._meta.get_field(field_name).verbose_name).capitalize()


def record_changes(model, record, ignored_fields, field_labels):
    if record.history_type != "~":
        return []
    previous = record.prev_record
    if previous is None:
        return []
    delta = record.diff_against(previous, excluded_fields=ignored_fields)
    return [
        {
            "field": field_label(model, change.field, field_labels),
            "old": display_value(model, change.field, change.old),
            "new": display_value(model, change.field, change.new),
        }
        for change in delta.changes
    ]


def history_row(model, record, ignored_fields, field_labels):
    action_key, action_label = HISTORY_ACTIONS.get(record.history_type, ("updated", "Modificado"))
    return {
        "pk": record.pk,
        "date": format_datetime(record.history_date),
        "author": author_of(record),
        "action_key": action_key,
        "action": action_label,
        "reason": record.history_change_reason or EMPTY,
        "changes": record_changes(model, record, ignored_fields, field_labels),
    }


def summary_of(record):
    if record is None:
        return None
    return {"date": format_datetime(record.history_date), "author": author_of(record)}


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Mixins


class HistoryObjectMixin:
    ignored_fields = DEFAULT_IGNORED_FIELDS
    field_labels = {}

    def has_model_permission(self, request):
        return self.model_admin.has_view_permission(request, self.get_object())

    def get_object(self):
        if not hasattr(self, "_object"):
            obj = self.model_admin.get_object(self.request, str(self.kwargs["pk"]))
            if obj is None:
                raise Http404
            self._object = obj
        return self._object

    def url_name(self, suffix):
        opts = self.model_admin.model._meta
        return f"admin:{opts.app_label}_{opts.model_name}_{suffix}"


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Views


class HistoryModalView(HistoryObjectMixin, PanelAjaxView, TemplateView):
    template_name = "panel/history_modal.html"

    def get(self, request, *args, **kwargs):
        if request.headers.get("x-requested-with") != "XMLHttpRequest":
            return redirect(self.url_name("change"), self.get_object().pk)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        obj = self.get_object()
        history = obj.history.select_related("history_user")
        return {
            **super().get_context_data(**kwargs),
            "object": obj,
            "total": history.count(),
            "created": summary_of(history.last()),
            "last_change": summary_of(history.first()),
            "list_url": reverse(self.url_name("history_list"), args=[obj.pk]),
        }


class HistoryListAjaxView(HistoryObjectMixin, PanelListViewAjax):
    include_options_column = False
    ordering_fields = {
        "1": "history_date",
        "2": "history_user__username",
        "3": "history_type",
        "4": "history_change_reason",
    }

    def get_queryset(self):
        return self.get_object().history.select_related("history_user")

    def get_order_by(self):
        if self.request.GET.get("order[0][column]") not in self.ordering_fields:
            return ("-history_date",)
        return super().get_order_by()

    def get_filter_by_search(self):
        search_value = self.request.GET.get("search[value]", "").strip()
        if not search_value:
            return Q()
        return (
            Q(history_change_reason__icontains=search_value)
            | Q(history_user__username__icontains=search_value)
            | Q(history_user__first_name__icontains=search_value)
            | Q(history_user__last_name__icontains=search_value)
        )

    def get_values(self, queryset):
        model = self.model_admin.model
        return [history_row(model, record, self.ignored_fields, self.field_labels) for record in queryset]


# endregion
"""========================================================================="""
