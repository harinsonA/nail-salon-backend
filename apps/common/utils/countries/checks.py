from itertools import cycle

from result import Err, Ok, Result

"""========================================================================="""
# region ........ Constants

PASSPORT_INVALID_MESSAGE = (
    "El pasaporte debe tener entre %(min)s y %(max)s letras o dígitos."
)
IDENTIFIER_SEPARATORS = ". -"


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Functions


def keep_digits(value: str, allowed: str = "") -> Result[str, str]:
    digits = ""
    for character in value.strip():
        if character.isdigit():
            digits += character
        elif character not in allowed:
            return Err(character)
    return Ok(digits)


def digits_in_range(value: str, min_length: int, max_length: int) -> Result[str, str]:
    result = keep_digits(value, allowed=IDENTIFIER_SEPARATORS)
    if result.is_err() or not min_length <= len(result.value) <= max_length:
        return Err(value)
    return result


def modulo_11_check_digit(body: str) -> str:
    total = sum(
        int(digit) * factor for digit, factor in zip(reversed(body), cycle(range(2, 8)))
    )
    remainder = 11 - total % 11
    return {11: "0", 10: "K"}.get(remainder, str(remainder))


def luhn_check_digit(body: str) -> str:
    total = 0
    for position, digit in enumerate(reversed(body)):
        value = int(digit) * (2 if position % 2 == 0 else 1)
        total += value - 9 if value > 9 else value
    return str((10 - total % 10) % 10)


def validate_passport(
    number: str, min_length: int, max_length: int
) -> Result[str, str]:
    value = "".join(number.split())
    if not (
        value.isascii() and value.isalnum() and min_length <= len(value) <= max_length
    ):
        return Err(PASSPORT_INVALID_MESSAGE % {"min": min_length, "max": max_length})
    return Ok(value)


# endregion
"""========================================================================="""
