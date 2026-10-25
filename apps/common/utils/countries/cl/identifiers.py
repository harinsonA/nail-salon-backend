from result import Err, Ok, Result

from apps.common.utils.countries.base import IdentifierValidator
from apps.common.utils.countries.checks import (
    keep_digits,
    modulo_11_check_digit,
    validate_passport,
)
from apps.common.utils.countries.cl.constants import (
    PASSPORT_MAX_LENGTH,
    PASSPORT_MIN_LENGTH,
    RUT_BODY_MAX_LENGTH,
    RUT_BODY_MIN_LENGTH,
    IdentifierType,
)

"""========================================================================="""
# region ........ Constants

RUT_FORMAT_MESSAGE = (
    "El RUT debe tener entre %(min)s y %(max)s dígitos más el dígito "
    "verificador (12.345.678-5)."
)
RUT_CHECK_DIGIT_MESSAGE = "El dígito verificador del RUT no es correcto."


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Classes


class ChileIdentifierValidator(IdentifierValidator):
    types = IdentifierType

    def validate_number(self, identifier_type: str, number: str) -> Result[str, str]:
        if identifier_type == IdentifierType.RUT:
            return self.validate_rut(number)
        return validate_passport(number, PASSPORT_MIN_LENGTH, PASSPORT_MAX_LENGTH)

    @staticmethod
    def validate_rut(number: str) -> Result[str, str]:
        format_error = Err(
            RUT_FORMAT_MESSAGE
            % {"min": RUT_BODY_MIN_LENGTH, "max": RUT_BODY_MAX_LENGTH}
        )
        body, check_digit = number[:-1], number[-1:]
        result = keep_digits(body, allowed=". -")
        if result.is_err() or not (check_digit.isdigit() or check_digit == "K"):
            return format_error
        body = result.value.lstrip("0")
        if not RUT_BODY_MIN_LENGTH <= len(body) <= RUT_BODY_MAX_LENGTH:
            return format_error
        if modulo_11_check_digit(body) != check_digit:
            return Err(RUT_CHECK_DIGIT_MESSAGE)
        return Ok(f"{body}-{check_digit}")


# endregion
"""========================================================================="""
