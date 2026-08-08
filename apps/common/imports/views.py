from django.contrib import messages
from django.db import transaction
from django.http import HttpResponse
from django.views.generic import FormView, View
from openpyxl import Workbook

from apps.common.exports.styles import (
    CONTENT_TYPE_XLSX,
    FREEZE_HEADER,
    write_header_row,
)
from apps.common.views.base_views import ProtectedView

from .forms import BaseImportForm


class BaseImportView(ProtectedView, FormView):
    """Vista base de importación (página normal, no modal).

    En ``form_valid`` instancia el ``validator_class``, mira el ``Result`` y
    bifurca: si hay errores renderiza la tabla de errores; si está OK persiste
    por lotes y redirige a ``success_url``.
    """

    template_name = "common/imports/import_form.html"
    error_template_name = "common/imports/import_errors.html"
    form_class = BaseImportForm

    title = "Importación"
    validator_class = None
    model = None
    view_url = None
    example_export_url = None
    back_url = None
    success_url = None
    batch_size = 50

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["import_title"] = self.title
        context["view_url"] = self.view_url
        context["example_export_url"] = self.example_export_url
        context["back_url"] = self.back_url or self.success_url
        if self.validator_class:
            context["import_fields"] = self.validator_class.get_headers()
        return context

    def form_valid(self, form):
        validator = self.validator_class(form.cleaned_data)
        resultado = validator.validate()
        if resultado.is_err():
            return self.render_errors(form, resultado.value, validator)
        creados = self.save(resultado.value)
        messages.success(self.request, f"{creados} registros importados correctamente.")
        return super().form_valid(form)

    @transaction.atomic
    def save(self, data: list) -> int:
        """Crea los registros por lotes. Todo-o-nada (transaction.atomic): si un
        INSERT falla, no queda nada a medias.

        ``bulk_create(batch_size=...)`` ya parte los INSERT en grupos del tamaño
        indicado: 500 filas con batch_size=50 -> 10 sentencias de 50 filas.
        """
        objetos = [self.model(**item) for item in data]
        creados = self.model.objects.bulk_create(objetos, batch_size=self.batch_size)
        return len(creados)

    def render_errors(self, form, errores, validator):
        """Renderiza import_errors.html con la tabla de filas con error."""
        context = self.get_context_data(form=form)
        context["errores"] = errores
        context["total_errores"] = len(errores)
        context["filas_error"] = validator.filas_error
        context["filas_ok"] = validator.filas_ok
        return self.render_to_response(context)

    def render_to_response(self, context, **kwargs):
        if context.get("errores"):
            self.template_name = self.error_template_name
        return super().render_to_response(context, **kwargs)


class BaseExampleExportView(ProtectedView, View):
    """Exporta una plantilla de ejemplo en .xlsx: encabezados + filas de ejemplo.

    Se entrega como Excel (no CSV) para que el usuario edite cómodamente, fila a
    fila, sin pelear con "Datos > Texto en columnas". El encabezado usa los
    estilos compartidos de apps.common.exports.styles (mismos que el export de
    datos), así ambos se mantienen alineados.

    NO confundir con el export de datos reales (ExcelExportMixin): esto exporta
    una plantilla vacía para *guiar la importación*.
    """

    validator_class = None
    example_rows: list = []
    filename = "plantilla"
    sheet_title = "Plantilla"
    column_width = 24

    def get(self, request, *args, **kwargs):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = self.sheet_title

        headers = self.validator_class.get_headers()
        write_header_row(sheet, headers, [self.column_width] * len(headers))

        for row_index, fila in enumerate(self.example_rows, start=2):
            for col_index, value in enumerate(fila, start=1):
                sheet.cell(row=row_index, column=col_index, value=value)

        if FREEZE_HEADER:
            sheet.freeze_panes = "A2"

        response = HttpResponse(content_type=CONTENT_TYPE_XLSX)
        response["Content-Disposition"] = f'attachment; filename="{self.filename}.xlsx"'
        workbook.save(response)
        return response
