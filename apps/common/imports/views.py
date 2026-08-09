from django.http import HttpResponse
from django.views.generic import View
from openpyxl import Workbook

from apps.common.exports.styles import (
    CONTENT_TYPE_XLSX,
    FREEZE_HEADER,
    write_header_row,
)
from apps.common.views.base_views import ProtectedView


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
