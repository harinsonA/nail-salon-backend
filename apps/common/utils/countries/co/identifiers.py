from result import Err, Result

from apps.common.utils.countries.base import IdentifierValidator
from apps.common.utils.countries.checks import digits_in_range, validate_passport
from apps.common.utils.countries.co.constants import (
    CEDULA_MAX_LENGTH,
    CEDULA_MIN_LENGTH,
    PASSPORT_MAX_LENGTH,
    PASSPORT_MIN_LENGTH,
    IdentifierType,
)

"""========================================================================="""
# region ........ Constants

CEDULA_FORMAT_MESSAGE = (
    "La cédula de ciudadanía debe tener entre %(min)s y %(max)s dígitos "
    "(1.234.567.890)."
)


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Classes


class ColombiaIdentifierValidator(IdentifierValidator):
    types = IdentifierType

    def validate_number(self, identifier_type: str, number: str) -> Result[str, str]:
        if identifier_type == IdentifierType.CEDULA:
            return self.validate_cedula(number)
        return validate_passport(number, PASSPORT_MIN_LENGTH, PASSPORT_MAX_LENGTH)

    @staticmethod
    def validate_cedula(number: str) -> Result[str, str]:
        result = digits_in_range(number, CEDULA_MIN_LENGTH, CEDULA_MAX_LENGTH)
        if result.is_err():
            return Err(
                CEDULA_FORMAT_MESSAGE
                % {"min": CEDULA_MIN_LENGTH, "max": CEDULA_MAX_LENGTH}
            )
        return result


# endregion
"""========================================================================="""
