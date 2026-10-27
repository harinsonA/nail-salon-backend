from django.db.models import Q
from django.http import JsonResponse
from django.views.generic import ListView
from apps.common.utils.search import search_ignoring_accents
from apps.common.views.base_views import ProtectedAjaxView


class AjaxListViewBase(ListView):
    http_method_names = ["get"]
    model = None
    filter_form_class = None
    field_list = []
    ordering_fields = {}
    _filters = {}
    include_options_column = True

    def get_pagination_length(self):
        pagination_start = int(self.request.GET.get("start", 0))
        pagination_length = int(self.request.GET.get("length", 10))
        return pagination_start, pagination_length + pagination_start

    def get_order_by(self) -> str:
        query_params = self.request.GET or {}
        column_to_order = query_params.get("order[0][column]", None)
        if not column_to_order:
            return ""

        field = self.ordering_fields.get(column_to_order, "name")
        direction = query_params.get("order[0][dir]", "asc")
        return (field,) if direction == "asc" else (f"-{field}",)

    def get_filter_by_search(self):
        search_value = self.request.GET.get("search[value]", "")
        if not search_value:
            return Q()
        return search_ignoring_accents(self.field_list, search_value)

    def get_filters(self):
        if not self.filter_form_class:
            return self._filters
        filter_form_class = self.filter_form_class(self.request.GET or None)
        if not filter_form_class.is_valid():
            return self._filters
        return {
            **self._filters,
            **filter_form_class.cleaned_data,
        }

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(**self.get_filters())

    def get_processed_queryset(self):
        """Queryset con filtros y orden aplicados, sin paginar."""
        queryset = self.get_queryset()
        ordering = self.get_order_by()
        if ordering:
            queryset = queryset.order_by(*ordering)
        return queryset

    def should_paginate(self) -> bool:
        """Punto de extensión: el ExcelExportMixin lo apaga al exportar."""
        return True

    def apply_pagination(self, queryset):
        if not self.should_paginate():
            return queryset
        page_start, page_end = self.get_pagination_length()
        return queryset[page_start:page_end]

    def is_export(self) -> bool:
        """Default; el ExcelExportMixin lo sobreescribe."""
        return False

    def get_values(self, queryset):
        return [*queryset.values(*self.field_list)]

    @staticmethod
    def add_options_column(data: list) -> list:
        return data

    @staticmethod
    def additional_data(queryset) -> dict:
        return {}

    def get_context_data(self, **kwargs):
        queryset = self.get_processed_queryset()

        total_records = queryset.count()

        search_filter = self.get_filter_by_search()
        filtered_records = total_records
        if search_filter:
            queryset = queryset.filter(search_filter)
            filtered_records = queryset.count()

        page = self.apply_pagination(queryset)
        data = self.get_values(page)
        if self.include_options_column:
            data = self.add_options_column(data)
        return {
            "data": data,
            "recordsTotal": total_records,
            "recordsFiltered": filtered_records,
            **self.additional_data(queryset),
        }

    def render_to_response(self, context, **response_kwargs):
        return JsonResponse(context)


class BaseListViewAjax(ProtectedAjaxView, AjaxListViewBase):
    pass
