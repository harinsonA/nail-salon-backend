from result import Err, Ok, Result

from apps.common.utils.countries.base import IdentifierValidator
from apps.common.utils.countries.checks import (
    digits_in_range,
    luhn_check_digit,
    validate_passport,
)
from apps.common.utils.countries.ec.constants import (
    CEDULA_LENGTH,
    CEDULA_MAX_THIRD_DIGIT,
    CEDULA_PROVINCES,
    PASSPORT_MAX_LENGTH,
    PASSPORT_MIN_LENGTH,
    IdentifierType,
)

"""========================================================================="""
# region ........ Constants

CEDULA_FORMAT_MESSAGE = "La cédula debe tener %(length)s dígitos (1710034065)."
CEDULA_PROVINCE_MESSAGE = (
    "Los dos primeros dígitos de la cédula no corresponden a una provincia."
)
CEDULA_THIRD_DIGIT_MESSAGE = (
    "El tercer dígito de la cédula debe estar entre 0 y %(max)s."
)
CEDULA_CHECK_DIGIT_MESSAGE = "El dígito verificador de la cédula no es correcto."


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Classes


class EcuadorIdentifierValidator(IdentifierValidator):
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
        if digits[:2] not in CEDULA_PROVINCES:
            return Err(CEDULA_PROVINCE_MESSAGE)
        if int(digits[2]) > CEDULA_MAX_THIRD_DIGIT:
            return Err(CEDULA_THIRD_DIGIT_MESSAGE % {"max": CEDULA_MAX_THIRD_DIGIT})
        if luhn_check_digit(digits[:-1]) != digits[-1]:
            return Err(CEDULA_CHECK_DIGIT_MESSAGE)
        return Ok(digits)


# endregion
"""========================================================================="""
