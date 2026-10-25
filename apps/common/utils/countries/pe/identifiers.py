from result import Err, Result

from apps.common.utils.countries.base import IdentifierValidator
from apps.common.utils.countries.checks import digits_in_range, validate_passport
from apps.common.utils.countries.pe.constants import (
    DNI_LENGTH,
    PASSPORT_MAX_LENGTH,
    PASSPORT_MIN_LENGTH,
    IdentifierType,
)

"""========================================================================="""
# region ........ Constants

DNI_FORMAT_MESSAGE = "El DNI debe tener %(length)s dígitos (12345678)."


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Classes


class PeruIdentifierValidator(IdentifierValidator):
    types = IdentifierType

    def validate_number(self, identifier_type: str, number: str) -> Result[str, str]:
        if identifier_type == IdentifierType.DNI:
            return self.validate_dni(number)
        return validate_passport(number, PASSPORT_MIN_LENGTH, PASSPORT_MAX_LENGTH)

    @staticmethod
    def validate_dni(number: str) -> Result[str, str]:
        result = digits_in_range(number, DNI_LENGTH, DNI_LENGTH)
        if result.is_err():
            return Err(DNI_FORMAT_MESSAGE % {"length": DNI_LENGTH})
        return result


# endregion
"""========================================================================="""
