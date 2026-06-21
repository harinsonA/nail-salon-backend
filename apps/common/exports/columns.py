from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class ExcelColumn:
    """Describe una columna del Excel exportado."""

    header: str  # texto del encabezado
    field: str  # clave en el dict de datos (campo de field_list o derivado en get_values)
    width: int = 20  # ancho de la columna
    align: str = "left"  # "left" | "center" | "right"
    number_format: Optional[str] = None  # formato nativo de Excel, ej. "$ #,##0"
    formatter: Optional[Callable[[Any], Any]] = None  # transforma el valor antes de escribir

    def get_value(self, row: dict) -> Any:
        value = row.get(self.field, "")
        return self.formatter(value) if self.formatter else value
