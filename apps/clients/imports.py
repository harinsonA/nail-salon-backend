from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from result import Ok, Err

from apps.clients.models.cliente import Cliente
from apps.common.imports.validators import BaseImportValidator
from apps.common.utils.utils import CommonCleaner
from apps.common.utils.phones import CountryPhonePrefix


class ClientImportValidator(BaseImportValidator):
    campos = {
        "nombre": "Nombre",
        "apellido": "Apellido",
        "telefono": "Teléfono",
        "email": "Email",
        "estado": "Estado",
        "notas": "Notas",
    }

    def clean_nombre(self, nombre, **kwargs):
        if not nombre:
            return Err("El campo 'nombre' es obligatorio.")
        return CommonCleaner.clean_alphabetic_field("nombre", nombre)

    def clean_apellido(self, apellido, **kwargs):
        if not apellido:
            return Err("El campo 'apellido' es obligatorio.")
        return CommonCleaner.clean_alphabetic_field("apellido", apellido)

    def clean_telefono(self, telefono, **kwargs):
        print(f"Validando teléfono: {telefono}")
        if not telefono:
            return Ok("")  # teléfono opcional: vacío es válido
        allowed_prefixes = [prefix.value for prefix in CountryPhonePrefix]
        for prefix in allowed_prefixes:
            if telefono.startswith(prefix):
                _phone = telefono[len(prefix) :]
                return CommonCleaner.clean_phone_field(prefix, _phone)
        str_prefixes = ", ".join(allowed_prefixes)
        return Err(
            f"El teléfono debe comenzar con uno de los siguientes prefijos: {str_prefixes}."
        )

    def clean_estado(self, estado, **kwargs):
        allowed_states = [choice.value for choice in Cliente.EstadoChoices]
        str_allowed_states = ", ".join(allowed_states)
        if not estado:
            return Err(f"El campo 'estado' es obligatorio: {str_allowed_states}.")
        estado_lower = estado.lower()
        if estado_lower not in allowed_states:
            return Err(
                f"El campo 'estado' debe ser uno de los siguientes: {str_allowed_states}."
            )
        return Ok(estado_lower)

    def clean_email(self, email, **kwargs):
        if not email:
            return Ok("")
        try:
            validate_email(email)
        except ValidationError:
            return Err(f"Email inválido: {email}")
        return Ok(email)

    def clean_notas(self, notas, **kwargs):
        if not notas:
            return Ok("")
        return CommonCleaner.clean_250_characters_field("notas", notas)
