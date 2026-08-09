import csv
import io

from result import Err, Ok, Result

from apps.common.utils.text import truncate_text
from apps.tareas.models import TareaEnProceso


class BaseAsyncImportValidator:
    """Valida y sanea el CSV de una importación asíncrona, fila por fila.

    Recibe la TareaEnProceso y trabaja sobre el texto que la vista dejó en
    datos_entrada["contenido"]. La subclase de cada entidad define los
    campos y los clean_<campo>.

    Attributes:
        fields (dict): Mapa {campo_del_modelo: "Encabezado"}. El ORDEN define
            el orden de las columnas del CSV.
        errors (list[dict]): Errores acumulados, con la forma
            {"row", "message", "value"}. Los fallos globales usan row="--".
        cleaned_data (list[dict]): Filas limpias, listas para Model(**fila).
        first_data_row (int): Número de la primera fila de datos en el
            archivo original (2 si traía encabezado, 1 si no).
        rows_ok (int): Filas que pasaron completas. Lo llena validate().
        rows_error (int): Filas DISTINTAS con al menos un error (una fila con
            varios errores cuenta una vez). Lo llena validate().
    """

    fields: dict = {}

    def __init__(self, task: TareaEnProceso):
        """Prepara el validator a partir de la tarea.

        No valida todavía: la extracción del contenido queda guardada como
        Result y es validate() quien decide.

        Args:
            task (TareaEnProceso): Tarea con el contenido en datos_entrada.

        Raises:
            NotImplementedError: Si la subclase no define 'fields' o no
                define ningún clean_<campo>.
        """
        if not self.fields:
            raise NotImplementedError(
                f"{type(self).__name__} debe definir 'fields' "
                "(mapa {campo_modelo: 'Encabezado'})."
            )
        self.errors: list = []
        self.cleaned_data: list = []
        self.first_data_row: int = 1
        self.rows_ok: int = 0
        self.rows_error: int = 0

        self.headers: list = self.get_headers()
        self.expected_columns: int = len(self.headers)
        self.input_data: Result = self.__get_input_data(task)
        self.cleaners: dict = self.__get_cleaners()

    @classmethod
    def get_headers(cls) -> list:
        """Encabezados esperados del CSV, en el orden de 'fields'.

        Es classmethod porque la vista de importación lo usa sin instanciar,
        para el bloque informativo del formulario.

        Returns:
            list[str]: Los encabezados declarados en 'fields'.
        """
        return list(cls.fields.values())

    def validate(self) -> Result:
        """Lee y valida el contenido completo, en una sola pasada.

        Es todo-o-nada: si alguna fila falla, descarta las limpias y devuelve
        solo los errores. Deja poblados rows_ok y rows_error como resumen.

        Returns:
            Result: Ok(list[dict]) con todas las filas limpias si no hubo
                ningún error, o Err(list[dict]) con la lista PLANA de errores
                {"row", "message", "value"} — una misma fila puede aparecer
                varias veces.
        """
        if self.input_data.is_err():
            self.errors.append(
                {"row": "--", "message": self.input_data.value, "value": ""}
            )
            self.rows_error = 1
            return Err(self.errors)

        rows_result: Result = self.__get_rows()
        if rows_result.is_err():
            self.errors.append(
                {"row": "--", "message": rows_result.value, "value": ""}
            )
            self.rows_error = 1
            return Err(self.errors)

        for row_number, row in enumerate(rows_result.value, start=self.first_data_row):
            result: Result = self.__validate_row(row)
            if result.is_err():
                for error in result.value:
                    self.errors.append({"row": row_number, **error})
                continue
            self.cleaned_data.append(result.value)

        self.rows_ok = len(self.cleaned_data)
        self.rows_error = len({error["row"] for error in self.errors})

        if self.errors:
            return Err(self.errors)
        return Ok(self.cleaned_data)

    def __get_input_data(self, task: TareaEnProceso) -> Result:
        input_data: str = task.datos_entrada.get("contenido", "")
        if not input_data.strip():
            return Err(
                "La tarea no tiene datos de entrada: no hay contenido que procesar."
            )
        return Ok(input_data)

    def __get_cleaners(self) -> dict:
        cleaners: dict = {}
        for field in self.fields:
            clean_method = getattr(self, f"clean_{field}", None)
            if callable(clean_method):
                cleaners[field] = clean_method
        if not cleaners:
            raise NotImplementedError(
                f"{type(self).__name__} debe definir al menos un método "
                "clean_<campo>() (p. ej. clean_nombre)."
            )
        return cleaners

    def __get_rows(self) -> Result:
        try:
            stream = io.StringIO(self.input_data.value)
            delimiter: str = self.__detect_delimiter(stream)
            rows: list = [
                row
                for row in csv.reader(stream, delimiter=delimiter)
                if any(column.strip() for column in row)
            ]
        except csv.Error as exc:
            return Err(f"El CSV está mal formado: {exc}")
        except Exception as exc:  # noqa: BLE001
            return Err(f"No se pudo leer el contenido: {exc}")
        if not rows:
            return Err("El archivo no tiene filas con datos.")
        return Ok(self.__skip_header_row(rows))

    @staticmethod
    def __detect_delimiter(stream: io.StringIO) -> str:
        sample: str = stream.readline()
        stream.seek(0)
        try:
            return csv.Sniffer().sniff(sample, delimiters=";,").delimiter
        except csv.Error:
            return ";" if sample.count(";") > sample.count(",") else ","

    def __skip_header_row(self, rows: list) -> list:
        if not rows:
            return rows
        first_row: list = [column.strip().casefold() for column in rows[0]]
        headers: list = [header.strip().casefold() for header in self.headers]
        if first_row == headers:
            self.first_data_row = 2
            return rows[1:]
        return rows

    def __validate_row(self, row: list) -> Result:
        row_length: int = len(row)
        if row_length != self.expected_columns:
            return Err(
                [
                    {
                        "message": (
                            f"La fila tiene {row_length} columnas; "
                            f"se esperaban {self.expected_columns}."
                        ),
                        "value": truncate_text(
                            ", ".join(str(column) for column in row)
                        ),
                    }
                ]
            )

        result = self.__map_row(row)
        if result.is_err():
            return Err(
                [
                    {
                        "message": result.value,
                        "value": truncate_text(
                            ", ".join(str(column) for column in row)
                        ),
                    }
                ]
            )
        return self.__clean_row(result.value)

    def __map_row(self, row: list) -> Result:
        try:
            data: dict = dict(zip(self.fields, (column.strip() for column in row)))
            return Ok(data)
        except Exception as exc:  # noqa: BLE001
            return Err(f"No se pudo procesar la fila: {exc}")

    def __clean_row(self, data: dict) -> Result:
        cleaned_data: dict = dict(data)
        errors: list = []
        for field, cleaner in self.cleaners.items():
            result: Result = cleaner(**data)
            if result.is_err():
                errors.append(
                    {
                        "message": result.value,
                        "value": truncate_text(data.get(field, "")),
                    }
                )
            else:
                cleaned_data[field] = result.value

        if errors:
            return Err(errors)
        return Ok(cleaned_data)
