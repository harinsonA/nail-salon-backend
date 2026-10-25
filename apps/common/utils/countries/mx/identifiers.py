import re

from result import Err, Ok, Result

from apps.common.utils.countries.base import IdentifierValidator
from apps.common.utils.countries.checks import validate_passport
from apps.common.utils.countries.mx.constants import (
    CURP_ALPHABET,
    CURP_PATTERN,
    PASSPORT_MAX_LENGTH,
    PASSPORT_MIN_LENGTH,
    IdentifierType,
)

"""========================================================================="""
# region ........ Constants

CURP_FORMAT_MESSAGE = (
    "La CURP debe tener 18 caracteres con el formato oficial (BOXW310820HNERXN09)."
)
CURP_CHECK_DIGIT_MESSAGE = "El dígito verificador de la CURP no es correcto."


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Classes


class MexicoIdentifierValidator(IdentifierValidator):
    types = IdentifierType

    def validate_number(self, identifier_type: str, number: str) -> Result[str, str]:
        if identifier_type == IdentifierType.CURP:
            return self.validate_curp(number)
        return validate_passport(number, PASSPORT_MIN_LENGTH, PASSPORT_MAX_LENGTH)

    @staticmethod
    def validate_curp(number: str) -> Result[str, str]:
        curp = "".join(number.split())
        if not re.fullmatch(CURP_PATTERN, curp):
            return Err(CURP_FORMAT_MESSAGE)
        total = sum(
            CURP_ALPHABET.index(character) * (18 - position)
            for position, character in enumerate(curp[:-1])
        )
        if str((10 - total % 10) % 10) != curp[-1]:
            return Err(CURP_CHECK_DIGIT_MESSAGE)
        return Ok(curp)


# endregion
"""========================================================================="""
