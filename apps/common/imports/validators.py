import csv
import io

from result import Err, Ok, Result

from apps.common.utils.text import truncate_text
from apps.tareas.models import TareaEnProceso


class BaseImportValidator:
    """Lee el CSV, valida/sanea cada fila ejecutando los ``clean_<campo>`` de la
    subclase, y devuelve:

      - ``Ok(list[dict])``  -> filas limpias (cada dict keyed por campo del modelo)
      - ``Err(list[dict])`` -> lista PLANA; una fila puede aparecer varias veces:
                               ``[{"fila", "mensaje_error", "valor"}, ...]``
    """

    # {campo_del_modelo: "Encabezado"} -- el ORDEN define el orden de columnas.
    campos: dict = {}

    def __init__(self, cleaned_data: dict):
        if not self.campos:
            raise NotImplementedError(
                f"{type(self).__name__} debe definir 'campos' "
                "(mapa {campo_modelo: 'Encabezado'})."
            )
        self.cleaned_data = cleaned_data
        self.archivo = cleaned_data["archivo"]
        self.first_data_row = 1  # pasa a 2 si hay fila de encabezados
        self.fields = self.get_fields()  # ["nombre", "apellido", ...]
        self.headers = self.get_headers()  # ["Nombre", "Apellido", ...]
        # Totalizadores (los llena validate(); los consume la vista de errores)
        self.filas_ok = 0  # filas correctas
        self.filas_error = 0  # filas distintas con al menos un error

    # ---- Derivados del mapa 'campos' ----
    @classmethod
    def get_fields(cls) -> list:
        return list(cls.campos.keys())

    @classmethod
    def get_headers(cls) -> list:
        return list(cls.campos.values())

    # ---- Orquestación ----
    def validate(self) -> Result[list, list]:
        lectura = self.read_csv(self.archivo)
        if lectura.is_err():
            # fallo GLOBAL del archivo -> una sola entrada en la tabla de errores
            self.filas_ok = 0
            self.filas_error = 1
            return Err(
                [
                    {
                        "fila": "—",
                        "mensaje_error": lectura.value,
                        "valor": truncate_text(getattr(self.archivo, "name", "")),
                    }
                ]
            )
        filas = self.skip_header_row(lectura.value)  # ignora encabezados si vienen

        ancho = len(self.fields)
        limpias, errores = [], []

        for numero, fila in enumerate(filas, start=self.first_data_row):
            # 1) ancho: la fila debe traer exactamente las columnas esperadas
            if len(fila) != ancho:
                errores.append(
                    {
                        "fila": numero,
                        "mensaje_error": (
                            f"La fila tiene {len(fila)} columnas; se esperaban {ancho}."
                        ),
                        "valor": truncate_text(", ".join(str(c) for c in fila)),
                    }
                )
                continue

            # 2) mapeo posicional -> dict keyed por campo del modelo
            mapeo = self.map_row(fila)
            if mapeo.is_err():
                errores.append(
                    {
                        "fila": numero,
                        "mensaje_error": mapeo.value,
                        "valor": truncate_text(", ".join(str(c) for c in fila)),
                    }
                )
                continue
            datos = mapeo.value

            # 3) ejecutar los clean_<campo>; una fila puede dar VARIOS errores
            resultado = self.clean_row(datos)
            if resultado.is_err():
                for error in resultado.value:  # error = {mensaje_error, valor}
                    errores.append({"fila": numero, **error})
                continue
            limpias.append(resultado.value)

        # Totalizadores: filas correctas vs. filas distintas con error
        self.filas_ok = len(limpias)
        self.filas_error = len({e["fila"] for e in errores})

        if errores:
            return Err(errores)
        return Ok(limpias)

    def map_row(self, fila: list) -> Result:
        """Mapea una fila (lista posicional) a ``{campo_modelo: valor}``.

        Aislado en try/except: si el armado del dict falla, se reporta como
        error de esa fila en vez de tumbar toda la importación.
        """
        try:
            datos = dict(zip(self.fields, (celda.strip() for celda in fila)))
            return Ok(datos)
        except Exception as exc:  # noqa: BLE001
            return Err(f"No se pudo procesar la fila: {exc}")

    # ---- Ejecuta los clean_<campo> descubiertos en la subclase ----
    def clean_row(self, datos: dict) -> Result:
        """Corre cada ``clean_<campo>`` sobre la fila ya mapeada.

        Los campos sin ``clean_`` pasan sin validación.
          - ``Ok(dict)``  -> fila limpia, lista para ``Model(**dict)``
          - ``Err(list)`` -> ``[{"mensaje_error", "valor"}, ...]`` de ESA fila
        """
        cleaners = self.get_cleaners()
        if not cleaners:
            raise NotImplementedError(
                f"{type(self).__name__} debe definir al menos un método "
                "clean_<campo>() (p. ej. clean_nombre)."
            )

        limpio = dict(datos)  # los campos sin cleaner pasan tal cual
        errores = []
        for campo, cleaner in cleaners.items():
            resultado = cleaner(**datos)  # clean_nombre(self, nombre, **kwargs)
            if resultado.is_err():
                errores.append(
                    {
                        "mensaje_error": resultado.value,
                        "valor": truncate_text(datos.get(campo, "")),
                    }
                )
            else:
                limpio[campo] = resultado.value

        if errores:
            return Err(errores)
        return Ok(limpio)

    def get_cleaners(self) -> dict:
        """Auto-descubre los métodos ``clean_<campo>`` de la subclase, en el
        orden de 'campos' (``clean_row`` queda excluido). -> {campo: método}."""
        cleaners = {}
        for campo in self.fields:
            metodo = getattr(self, f"clean_{campo}", None)
            if callable(metodo):
                cleaners[campo] = metodo
        return cleaners

    # ---- Lectura POSICIONAL (no DictReader: los encabezados son opcionales) ----
    def read_csv(self, archivo) -> Result:
        """CSV -> lista de listas (descarta filas vacías). Es un fallo GLOBAL
        (afecta a TODO el archivo), distinto de un error de fila.

        El ÚNICO encoding permitido es UTF-8 (``utf-8-sig`` acepta UTF-8 con o
        sin el BOM que agrega Excel al guardar como 'CSV UTF-8'). Si no es
        UTF-8, se rechaza el archivo con un mensaje claro.
          - ``Ok(list[list])``  filas con datos
          - ``Err(str)``        si no es UTF-8 / está mal formado / no se puede leer
        """
        try:
            archivo.file.seek(0)
            texto = io.TextIOWrapper(archivo.file, encoding="utf-8-sig", newline="")
            delimitador = self.detect_delimiter(texto)
            filas = [
                f
                for f in csv.reader(texto, delimiter=delimitador)
                if any(c.strip() for c in f)
            ]
            texto.detach()  # no cerrar el archivo subyacente
        except UnicodeDecodeError:
            return Err(
                "El archivo debe estar codificado en UTF-8. "
                "Guárdalo como 'CSV UTF-8' y reintenta."
            )
        except csv.Error as exc:
            return Err(f"El CSV está mal formado: {exc}")
        except Exception as exc:  # noqa: BLE001
            return Err(f"No se pudo leer el archivo: {exc}")
        if not filas:
            return Err("El archivo no tiene filas con datos.")
        return Ok(filas)

    @staticmethod
    def detect_delimiter(texto) -> str:
        """Detecta el separador del CSV a partir de la primera línea con datos.

        Excel en configuración regional español/Chile guarda los CSV con ``;``
        (la coma se reserva como separador decimal); el CSV estándar usa ``,``.
        Se prueba con ``csv.Sniffer`` y, si falla, se elige entre ``;`` y ``,``
        por frecuencia. Deja el puntero al inicio para que la lectura real
        recorra todo el archivo.
        """
        muestra = texto.readline()
        texto.seek(0)
        try:
            return csv.Sniffer().sniff(muestra, delimiters=";,").delimiter
        except csv.Error:
            return ";" if muestra.count(";") > muestra.count(",") else ","

    def skip_header_row(self, filas: list) -> list:
        """Si la 1a fila coincide con get_headers(), se descarta (no es dato)."""
        if not filas:
            return filas
        primera = [c.strip().casefold() for c in filas[0]]
        headers = [h.strip().casefold() for h in self.headers]
        if primera == headers:
            self.first_data_row = 2  # los datos arrancan en la fila 2
            return filas[1:]
        return filas


class BaseAsyncImportValidator:
    """Valida y sanea el CSV de una importación asíncrona, fila por fila.

    Contraparte de BaseImportValidator para el flujo asíncrono: en vez de un
    archivo subido recibe la TareaEnProceso y trabaja sobre el texto que la
    vista dejó en datos_entrada["contenido"]. La subclase de cada entidad
    define los campos y los clean_<campo>.

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
