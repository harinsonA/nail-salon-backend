from result import Err, Result

from apps.common.utils.countries.ar.constants import (
    DNI_MAX_LENGTH,
    DNI_MIN_LENGTH,
    PASSPORT_MAX_LENGTH,
    PASSPORT_MIN_LENGTH,
    IdentifierType,
)
from apps.common.utils.countries.base import IdentifierValidator
from apps.common.utils.countries.checks import digits_in_range, validate_passport

"""========================================================================="""
# region ........ Constants

DNI_FORMAT_MESSAGE = "El DNI debe tener entre %(min)s y %(max)s dígitos (12.345.678)."


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Classes


class ArgentinaIdentifierValidator(IdentifierValidator):
    types = IdentifierType

    def validate_number(self, identifier_type: str, number: str) -> Result[str, str]:
        if identifier_type == IdentifierType.DNI:
            return self.validate_dni(number)
        return validate_passport(number, PASSPORT_MIN_LENGTH, PASSPORT_MAX_LENGTH)

    @staticmethod
    def validate_dni(number: str) -> Result[str, str]:
        result = digits_in_range(number, DNI_MIN_LENGTH, DNI_MAX_LENGTH)
        if result.is_err():
            return Err(
                DNI_FORMAT_MESSAGE % {"min": DNI_MIN_LENGTH, "max": DNI_MAX_LENGTH}
            )
        return result


# endregion
"""========================================================================="""
