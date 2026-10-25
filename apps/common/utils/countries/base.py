from abc import ABC, abstractmethod

from django.db.models import TextChoices
from result import Err, Ok, Result

from apps.common.utils.countries.checks import keep_digits

"""========================================================================="""
# region ........ Constants

PREFIX_INVALID_MESSAGE = "El prefijo del teléfono es inválido. (%(prefixes)s)."
PHONE_LENGTH_INVALID_MESSAGE = "El número de teléfono debe tener %(length)s dígitos."
PHONE_CHARACTERS_MESSAGE = (
    "El número de teléfono solo debe contener dígitos, espacios o guiones."
)
IDENTIFIER_TYPE_INVALID_MESSAGE = "El tipo de identificador no corresponde a este país."
MAX_PREFIXES_IN_MESSAGE = 5


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Classes


class PhoneValidator:
    prefix: str
    length: int
    operator_prefixes: tuple[str, ...] = ()

    def validate(self, number: str) -> Result[str, str]:
        result = keep_digits(number, allowed=" -")
        if result.is_err():
            return Err(PHONE_CHARACTERS_MESSAGE)
        digits = result.value
        result = self.validate_operator(digits)
        if result.is_err():
            return result
        if len(digits) - len(result.value) != self.length:
            return Err(PHONE_LENGTH_INVALID_MESSAGE % {"length": self.length})
        return Ok(f"{self.prefix}{digits}")

    def validate_operator(self, digits: str) -> Result[str, str]:
        if not self.operator_prefixes:
            return Ok("")
        for operator_prefix in self.operator_prefixes:
            if digits.startswith(operator_prefix):
                return Ok(operator_prefix)
        prefixes = ", ".join(self.operator_prefixes[:MAX_PREFIXES_IN_MESSAGE])
        if len(self.operator_prefixes) > MAX_PREFIXES_IN_MESSAGE:
            prefixes = f"{prefixes}..."
        return Err(PREFIX_INVALID_MESSAGE % {"prefixes": prefixes})


class IdentifierValidator(ABC):
    types: type[TextChoices]

    def validate(self, identifier_type: str, number: str) -> Result[str, str]:
        if identifier_type not in self.types.values:
            return Err(IDENTIFIER_TYPE_INVALID_MESSAGE)
        return self.validate_number(identifier_type, number.strip().upper())

    @abstractmethod
    def validate_number(
        self, identifier_type: str, number: str
    ) -> Result[str, str]: ...


class CountryValidator:
    country: str
    phone: PhoneValidator
    identifier: IdentifierValidator

    def identifier_types(self) -> list[tuple[str, str]]:
        return self.identifier.types.choices

    def validate_phone(self, number: str) -> Result[str, str]:
        return self.phone.validate(number)

    def validate_identifier(
        self, identifier_type: str, number: str
    ) -> Result[str, str]:
        return self.identifier.validate(identifier_type, number)


# endregion
"""========================================================================="""
