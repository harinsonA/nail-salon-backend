import datetime
from decimal import Decimal, InvalidOperation

from result import Ok, Err

from apps.common.imports.validators import BaseImportValidator
from apps.common.utils.utils import CommonCleaner
from apps.services.models.servicio import Servicio
from apps.services.models.categoria import Categoria


class ServiceImportValidator(BaseImportValidator):
    campos = {
        "nombre": "Nombre",
        "categoria": "ID Categoría",
        "descripcion": "Descripción",
        "precio": "Precio",
        "duracion_estimada": "Duración (minutos)",
        "estado": "Estado",
    }

    # Duración por defecto cuando la columna viene vacía (igual que el modelo).
    DEFAULT_DURATION = datetime.timedelta(minutes=30)

    def clean_nombre(self, nombre, **kwargs):
        if not nombre:
            return Err("El campo 'nombre' es obligatorio.")
        # Misma regla que ServicesForm.clean_name: solo alfabético y espacios.
        return CommonCleaner.clean_alphabetic_field("nombre del servicio", nombre)

    def clean_categoria(self, categoria, estado="", **kwargs):
        # Campo opcional: vacío -> sin categoría ("Sin definir").
        if not categoria:
            return Ok(None)

        try:
            categoria_id = int(categoria)
        except (TypeError, ValueError):
            return Err(
                f"El 'ID Categoría' debe ser un número entero: {categoria}."
            )

        instancia = Categoria.objects.filter(pk=categoria_id).first()
        if not instancia:
            return Err(f"No existe una categoría con ID {categoria_id}.")

        # Misma regla que el modal: no se puede crear un servicio activo con una
        # categoría inactiva.
        quiere_activar = estado.strip().lower() == Servicio.EstadoChoices.ACTIVO
        if quiere_activar and instancia.estado == Categoria.EstadoChoices.INACTIVO:
            return Err(
                f"No puedes crear un servicio activo con la categoría "
                f"'{instancia.nombre}' (ID {categoria_id}) porque está inactiva."
            )
        return Ok(instancia)

    def clean_descripcion(self, descripcion, **kwargs):
        if not descripcion:
            return Ok("")
        return CommonCleaner.clean_250_characters_field("descripción", descripcion)

    def clean_precio(self, precio, **kwargs):
        if not precio:
            return Err("El campo 'precio' es obligatorio.")
        try:
            valor = Decimal(precio.replace(" ", ""))
        except (InvalidOperation, AttributeError):
            return Err(f"El precio debe ser un número válido: {precio}.")
        if valor <= 0:
            return Err("El precio debe ser mayor a cero.")
        return Ok(valor)

    def clean_duracion_estimada(self, duracion_estimada, **kwargs):
        # Opcional: si viene vacía se usa la duración por defecto.
        if not duracion_estimada:
            return Ok(self.DEFAULT_DURATION)
        try:
            minutos = int(duracion_estimada)
        except (TypeError, ValueError):
            return Err(
                f"La duración debe ser un número entero de minutos: "
                f"{duracion_estimada}."
            )
        if minutos <= 0:
            return Err("La duración debe ser mayor a cero.")
        return Ok(datetime.timedelta(minutes=minutos))

    def clean_estado(self, estado, **kwargs):
        allowed_states = [choice.value for choice in Servicio.EstadoChoices]
        str_allowed_states = ", ".join(allowed_states)
        if not estado:
            return Err(f"El campo 'estado' es obligatorio: {str_allowed_states}.")
        estado_lower = estado.lower()
        if estado_lower not in allowed_states:
            return Err(
                f"El campo 'estado' debe ser uno de los siguientes: "
                f"{str_allowed_states}."
            )
        return Ok(estado_lower)


class CategoryImportValidator(BaseImportValidator):
    campos = {
        "nombre": "Nombre",
        "descripcion": "Descripción",
        "estado": "Estado",
    }

    def clean_nombre(self, nombre, **kwargs):
        if not nombre:
            return Err("El campo 'nombre' es obligatorio.")
        # Misma regla que CategoriesForm.clean_name: solo alfabético y espacios.
        return CommonCleaner.clean_alphabetic_field(
            "nombre de la categoria", nombre
        )

    def clean_descripcion(self, descripcion, **kwargs):
        if not descripcion:
            return Ok("")
        return CommonCleaner.clean_250_characters_field("descripción", descripcion)

    def clean_estado(self, estado, **kwargs):
        allowed_states = [choice.value for choice in Categoria.EstadoChoices]
        str_allowed_states = ", ".join(allowed_states)
        if not estado:
            return Err(f"El campo 'estado' es obligatorio: {str_allowed_states}.")
        estado_lower = estado.lower()
        if estado_lower not in allowed_states:
            return Err(
                f"El campo 'estado' debe ser uno de los siguientes: "
                f"{str_allowed_states}."
            )
        return Ok(estado_lower)
