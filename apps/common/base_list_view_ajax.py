import operator
from functools import reduce

from django.db.models import Q
from django.http import JsonResponse
from django.views.generic import ListView


class BaseListViewAjax(ListView):
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
        return reduce(
            operator.or_,
            (Q(**{f"{field}__icontains": search_value}) for field in self.field_list),
        )

    def get_filters(self):
        if not self.filter_form_class:
            return self._filters
        filter_form_class = self.filter_form_class(self.request.GET or None)
        if not filter_form_class.is_valid():
            return self._filters
        return {**filter_form_class.cleaned_data}

    def get_queryset(self):
        queryset = super().get_queryset()
        return queryset.filter(**self.get_filters())

    def get_values(self, queryset):
        return self.get_data(values=[*queryset.values(*self.field_list)])

    def get_data_length(self, values):
        page_start, page_end = self.get_pagination_length()
        return values[page_start:page_end]

    def get_data(self, values):
        return self.get_data_length(values)

    @staticmethod
    def add_options_column(data: list) -> list:
        return data

    def get_context_data(self, **kwargs):
        queryset = self.get_queryset()

        ordering = self.get_order_by()
        if ordering:
            queryset = queryset.order_by(*ordering)
        queryset = queryset.filter(self.get_filter_by_search())

        total_records = queryset.count()
        data = self.get_values(queryset)
        if self.include_options_column:
            data = self.add_options_column(data)
        return {
            "data": data,
            "recordsTotal": total_records,
            "recordsFiltered": total_records,
        }

    def render_to_response(self, context, **response_kwargs):
        return JsonResponse(context)
