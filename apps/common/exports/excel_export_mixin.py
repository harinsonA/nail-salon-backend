from __future__ import annotations

from datetime import datetime

from django.http import HttpResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment

from apps.common.exports.columns import ExcelColumn
from apps.common.exports.styles import (
    CONTENT_TYPE_XLSX,
    FREEZE_HEADER,
    write_header_row,
)


class ExcelExportMixin:
    """
    Da capacidad de exportar a Excel a una vista basada en BaseListViewAjax.

    Una subclase de export típica solo define excel_columns (y opcionalmente
    excel_filename / excel_sheet_title), reutilizando filtros, annotate y los
    valores de display que la list view ya calcula.

    Debe ir a la IZQUIERDA de la list view en el MRO para que sus hooks ganen:
        class XExportView(ExcelExportMixin, XListView): ...

    Los estilos del encabezado viven en apps.common.exports.styles (compartidos
    con las plantillas de ejemplo de importación).
    """

    excel_columns: list[ExcelColumn] = []
    excel_filename = "export"  # sin extensión
    excel_sheet_title = "Datos"
    force_export = False  # True en vistas dedicadas (URL propia)
    export_param = "export"  # trigger por querystring: ?export=excel
    export_value = "excel"
    freeze_header = FREEZE_HEADER

    # --- Decisión (los hooks que BaseListViewAjax respeta) ---
    def is_export(self) -> bool:
        if not self.excel_columns:
            return False
        if self.force_export:
            return True
        return self.request.GET.get(self.export_param) == self.export_value

    def should_paginate(self) -> bool:
        return False if self.is_export() else super().should_paginate()

    def render_to_response(self, context, **response_kwargs):
        if self.is_export():
            return self.build_excel_response(context["data"])
        return super().render_to_response(context, **response_kwargs)

    # --- Construcción del archivo ---
    def get_excel_filename(self) -> str:
        stamp = datetime.now().strftime("%Y%m%d_%H%M")
        return f"{self.excel_filename}_{stamp}.xlsx"

    def build_excel_response(self, rows: list[dict]) -> HttpResponse:
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = self.excel_sheet_title

        # Encabezado con estilos de marca compartidos
        write_header_row(
            sheet,
            [column.header for column in self.excel_columns],
            [column.width for column in self.excel_columns],
        )

        for row_index, row in enumerate(rows, start=2):
            for col_index, column in enumerate(self.excel_columns, start=1):
                cell = sheet.cell(
                    row=row_index, column=col_index, value=column.get_value(row)
                )
                cell.alignment = Alignment(horizontal=column.align, vertical="center")
                if column.number_format:
                    cell.number_format = column.number_format

        if self.freeze_header:
            sheet.freeze_panes = "A2"

        response = HttpResponse(content_type=CONTENT_TYPE_XLSX)
        response["Content-Disposition"] = (
            f'attachment; filename="{self.get_excel_filename()}"'
        )
        workbook.save(response)
        return response
