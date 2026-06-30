import csv
import io

from result import Result, Ok, Err

from apps.common.utils.text import truncate_text


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
