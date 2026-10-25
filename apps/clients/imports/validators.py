from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from result import Err, Ok

from apps.clients.models.cliente import Cliente
from apps.common.imports.validators import BaseAsyncImportValidator
from apps.common.utils.countries.constants import (
    Country,
    CountryPhonePrefix,
    NationalIdentifierType,
)
from apps.common.utils.countries.dispatcher import CountryDispatcher
from apps.common.utils.utils import CommonCleaner

COUNTRY_INVALID_MESSAGE = "El país debe ser un código de dos letras: %(codes)s."
REPEATED_IN_FILE_MESSAGE = "Ese %(what)s se repite en otra fila del archivo."
CLIENT_HOLDER = "otro cliente"
NATIONAL_ID_FIELD_BY_KEY = {
    "country": "pais",
    "type": "tipo_identificador_nacional",
    "number": "identificador_nacional",
}


class ClientAsyncImportValidator(BaseAsyncImportValidator):
    def __init__(self, task):
        super().__init__(task)
        self.seen_values = {
            "correo": set(),
            "teléfono": set(),
            "identificador nacional": set(),
        }

    def first_in_file(self, what, value):
        if value in self.seen_values[what]:
            return Err(REPEATED_IN_FILE_MESSAGE % {"what": what})
        self.seen_values[what].add(value)
        return Ok(value)

    fields = {
        "nombre": "Nombre",
        "apellido": "Apellido",
        "telefono": "Teléfono",
        "email": "Email",
        "pais": "País",
        "tipo_identificador_nacional": "Tipo de identificador nacional",
        "identificador_nacional": "Identificador nacional",
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
        if not telefono:
            return Ok("")  # teléfono opcional: vacío es válido
        allowed_prefixes = [prefix.value for prefix in CountryPhonePrefix]
        for prefix in allowed_prefixes:
            if telefono.startswith(prefix):
                _phone = telefono[len(prefix) :]
                result = CommonCleaner.clean_phone_field(prefix, _phone)
                if result.is_err():
                    return result
                available = CommonCleaner.check_phone_available(
                    Cliente.objects.all(), CLIENT_HOLDER, telefono=result.ok_value
                )
                if available.is_err():
                    return available
                return self.first_in_file("teléfono", result.ok_value)
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
        email = email.lower()
        available = CommonCleaner.check_email_available(
            Cliente.objects.all(), CLIENT_HOLDER, email
        )
        if available.is_err():
            return available
        return self.first_in_file("correo", email)

    def clean_notas(self, notas, **kwargs):
        if not notas:
            return Ok("")
        return CommonCleaner.clean_250_characters_field("notas", notas)

    def clean_pais(self, **data):
        return self.national_identifier_field("pais", data)

    def clean_tipo_identificador_nacional(self, **data):
        return self.national_identifier_field("tipo_identificador_nacional", data)

    def clean_identificador_nacional(self, **data):
        result = self.national_identifier_field("identificador_nacional", data)
        if result.is_err() or not result.ok_value:
            return result
        _, values = self.check_national_identifier(
            data.get("pais", ""),
            data.get("tipo_identificador_nacional", ""),
            data.get("identificador_nacional", ""),
        )
        available = CommonCleaner.check_national_identifier_available(
            Cliente.objects.all(),
            CLIENT_HOLDER,
            values["pais"],
            values["tipo_identificador_nacional"],
            values["identificador_nacional"],
        )
        if available.is_err():
            return available
        key = tuple(values.values())
        if self.first_in_file("identificador nacional", key).is_err():
            return Err(REPEATED_IN_FILE_MESSAGE % {"what": "identificador nacional"})
        return result

    def national_identifier_field(self, field, data):
        errors, values = self.check_national_identifier(
            data.get("pais", ""),
            data.get("tipo_identificador_nacional", ""),
            data.get("identificador_nacional", ""),
        )
        if field in errors:
            return Err(errors[field])
        return Ok(values.get(field))

    @staticmethod
    def check_national_identifier(country, identifier_type, number):
        country = country.strip().upper()
        if country and country not in Country.values:
            return {
                "pais": COUNTRY_INVALID_MESSAGE % {"codes": ", ".join(Country.values)}
            }, {}
        identifier_type = identifier_type.strip()
        types = CountryDispatcher.identifier_types(country) if country else []
        generic_names = dict(NationalIdentifierType.choices)
        for value, label in types:
            names = (value, label, generic_names.get(value, value))
            if identifier_type.casefold() in (name.casefold() for name in names):
                identifier_type = value
                break
        result = CommonCleaner.clean_national_identifier(
            country, identifier_type, number.strip()
        )
        if result.is_err():
            return {
                NATIONAL_ID_FIELD_BY_KEY[key]: message
                for key, message in result.err_value.items()
            }, {}
        return {}, {
            "pais": country or None,
            "tipo_identificador_nacional": identifier_type or None,
            "identificador_nacional": result.ok_value,
        }
