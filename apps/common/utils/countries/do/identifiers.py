from result import Err, Ok, Result

from apps.common.utils.countries.base import IdentifierValidator
from apps.common.utils.countries.checks import (
    digits_in_range,
    luhn_check_digit,
    validate_passport,
)
from apps.common.utils.countries.do.constants import (
    CEDULA_LENGTH,
    PASSPORT_MAX_LENGTH,
    PASSPORT_MIN_LENGTH,
    IdentifierType,
)

"""========================================================================="""
# region ........ Constants

CEDULA_FORMAT_MESSAGE = "La cédula debe tener %(length)s dígitos (001-1234567-8)."
CEDULA_CHECK_DIGIT_MESSAGE = "El dígito verificador de la cédula no es correcto."


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Classes


class DominicanRepublicIdentifierValidator(IdentifierValidator):
    types = IdentifierType

    def validate_number(self, identifier_type: str, number: str) -> Result[str, str]:
        if identifier_type == IdentifierType.CEDULA:
            return self.validate_cedula(number)
        return validate_passport(number, PASSPORT_MIN_LENGTH, PASSPORT_MAX_LENGTH)

    @staticmethod
    def validate_cedula(number: str) -> Result[str, str]:
        result = digits_in_range(number, CEDULA_LENGTH, CEDULA_LENGTH)
        if result.is_err():
            return Err(CEDULA_FORMAT_MESSAGE % {"length": CEDULA_LENGTH})
        digits = result.value
        if luhn_check_digit(digits[:-1]) != digits[-1]:
            return Err(CEDULA_CHECK_DIGIT_MESSAGE)
        return Ok(f"{digits[:3]}-{digits[3:10]}-{digits[10]}")


# endregion
"""========================================================================="""
