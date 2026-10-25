from result import Err, Ok, Result

from apps.common.utils.countries.base import IdentifierValidator
from apps.common.utils.countries.checks import keep_digits, validate_passport
from apps.common.utils.countries.ve.constants import (
    CEDULA_MAX_LENGTH,
    CEDULA_MIN_LENGTH,
    CEDULA_NATIONALITIES,
    PASSPORT_MAX_LENGTH,
    PASSPORT_MIN_LENGTH,
    IdentifierType,
)

"""========================================================================="""
# region ........ Constants

CEDULA_FORMAT_MESSAGE = (
    "La cédula debe empezar con %(nationalities)s seguida de %(min)s a %(max)s "
    "dígitos (V-12.345.678)."
)


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Classes


class VenezuelaIdentifierValidator(IdentifierValidator):
    types = IdentifierType

    def validate_number(self, identifier_type: str, number: str) -> Result[str, str]:
        if identifier_type == IdentifierType.CEDULA:
            return self.validate_cedula(number)
        return validate_passport(number, PASSPORT_MIN_LENGTH, PASSPORT_MAX_LENGTH)

    @staticmethod
    def validate_cedula(number: str) -> Result[str, str]:
        format_error = Err(
            CEDULA_FORMAT_MESSAGE
            % {
                "nationalities": " o ".join(CEDULA_NATIONALITIES),
                "min": CEDULA_MIN_LENGTH,
                "max": CEDULA_MAX_LENGTH,
            }
        )
        nationality, digits = number[:1], number[1:]
        result = keep_digits(digits, allowed=". -")
        if nationality not in CEDULA_NATIONALITIES or result.is_err():
            return format_error
        digits = result.value.lstrip("0")
        if not CEDULA_MIN_LENGTH <= len(digits) <= CEDULA_MAX_LENGTH:
            return format_error
        return Ok(f"{nationality}-{digits}")


# endregion
"""========================================================================="""
