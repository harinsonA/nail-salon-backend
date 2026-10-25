from result import Err, Ok, Result

from apps.common.utils.countries.base import IdentifierValidator
from apps.common.utils.countries.checks import digits_in_range, validate_passport
from apps.common.utils.countries.uy.constants import (
    CEDULA_BODY_MAX_LENGTH,
    CEDULA_BODY_MIN_LENGTH,
    CEDULA_CHECK_WEIGHTS,
    PASSPORT_MAX_LENGTH,
    PASSPORT_MIN_LENGTH,
    IdentifierType,
)

"""========================================================================="""
# region ........ Constants

CEDULA_FORMAT_MESSAGE = (
    "La cédula debe tener entre %(min)s y %(max)s dígitos más el dígito "
    "verificador (1.234.567-2)."
)
CEDULA_CHECK_DIGIT_MESSAGE = "El dígito verificador de la cédula no es correcto."


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Classes


class UruguayIdentifierValidator(IdentifierValidator):
    types = IdentifierType

    def validate_number(self, identifier_type: str, number: str) -> Result[str, str]:
        if identifier_type == IdentifierType.CEDULA:
            return self.validate_cedula(number)
        return validate_passport(number, PASSPORT_MIN_LENGTH, PASSPORT_MAX_LENGTH)

    @staticmethod
    def validate_cedula(number: str) -> Result[str, str]:
        result = digits_in_range(
            number, CEDULA_BODY_MIN_LENGTH + 1, CEDULA_BODY_MAX_LENGTH + 1
        )
        if result.is_err():
            return Err(
                CEDULA_FORMAT_MESSAGE
                % {"min": CEDULA_BODY_MIN_LENGTH, "max": CEDULA_BODY_MAX_LENGTH}
            )
        body, check_digit = result.value[:-1], result.value[-1]
        padded_body = body.zfill(len(CEDULA_CHECK_WEIGHTS))
        total = sum(
            int(digit) * weight
            for digit, weight in zip(padded_body, CEDULA_CHECK_WEIGHTS, strict=True)
        )
        if str((10 - total % 10) % 10) != check_digit:
            return Err(CEDULA_CHECK_DIGIT_MESSAGE)
        return Ok(f"{body}-{check_digit}")


# endregion
"""========================================================================="""
