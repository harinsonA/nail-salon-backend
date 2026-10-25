from urllib.parse import quote, urlencode

from result import Err, Ok, Result

from apps.common.utils.countries.constants import (
    COUNTRY_OPERATOR_PREFIX,
    CountryPhoneLength,
    CountryPhonePrefix,
)

"""========================================================================="""
# region ........ Constants

PREFIX_INVALID_MESSAGE = "El prefijo del teléfono es inválido. (%(prefixes)s)."
PHONE_LENGTH_INVALID_MESSAGE = "El número de teléfono debe tener %(length)s dígitos."

WHATSAPP_APP_URL = "https://wa.me"
WHATSAPP_WEB_URL = "https://web.whatsapp.com/send"


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Classes


class PhoneCleaner:
    def __init__(self, prefix_value: str):
        self.prefix_value = prefix_value
        self.allowed_characters = [" ", "-"]
        self.operator_prefixes = self.__get_operator_prefixes(prefix_value)
        self.phone_length = self.__get_phone_length(prefix_value)

    @staticmethod
    def __get_operator_prefixes(prefix_value: str) -> set:
        return COUNTRY_OPERATOR_PREFIX.get(prefix_value, {})

    @staticmethod
    def __get_phone_length(prefix_value: str) -> int:
        phone_lengths = dict(CountryPhoneLength.choices)
        return int(phone_lengths.get(prefix_value, "0"))

    def __common_clean(self, phone_number: str) -> Result[str, str]:
        value = ""
        for character in phone_number:
            if not (character.isdigit() or character in self.allowed_characters):
                return Err(
                    "El número de teléfono solo debe contener "
                    "dígitos, espacios o guiones."
                )
            if character in self.allowed_characters:
                continue
            value += character
        return Ok(value)

    def __is_operator_valid(self, phone_number: str) -> Result[str, str]:
        if not self.operator_prefixes:
            return Ok("")
        for prefix in self.operator_prefixes:
            if phone_number.startswith(prefix):
                return Ok(prefix)
        prefixes = (
            ", ".join(self.operator_prefixes)
            if self.prefix_value != CountryPhonePrefix.COLOMBIA
            else f"{', '.join(list(self.operator_prefixes)[:5])}..."
        )
        return Err(PREFIX_INVALID_MESSAGE % {"prefixes": prefixes})

    def __is_valid(self, phone_number: str) -> Result[str, str]:
        result = self.__is_operator_valid(phone_number)
        if result.is_err():
            return result
        _phone_number = phone_number[len(result.value) :]
        if len(_phone_number) != self.phone_length:
            return Err(PHONE_LENGTH_INVALID_MESSAGE % {"length": self.phone_length})
        return Ok(phone_number)

    def is_valid(self, phone_number: str) -> Result[str, str]:
        result = self.__common_clean(phone_number)
        if result.is_err():
            return result
        cleaned_number = result.value
        result = self.__is_valid(cleaned_number)
        if result.is_err():
            return result
        return Ok(f"{self.prefix_value}{cleaned_number}")


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Functions


def get_whatsapp_url(phone_number: str, message: str = "", app: bool = False) -> str:
    digits = "".join(character for character in phone_number if character.isdigit())
    params = {"text": message} if message else {}
    if app:
        url = f"{WHATSAPP_APP_URL}/{digits}"
    else:
        url = WHATSAPP_WEB_URL
        params = {"phone": digits, **params}
    if not params:
        return url
    return f"{url}?{urlencode(params, quote_via=quote)}"


# endregion
"""========================================================================="""
