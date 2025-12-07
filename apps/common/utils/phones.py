from django.db.models import TextChoices
from result import Result, Ok, Err

"""========================================================================="""
# region ........ Constants

PREFIX_INVALID_MESSAGE = "El prefijo del teléfono es inválido. (%(prefixes)s)."
PHONE_LENGTH_INVALID_MESSAGE = "El número de teléfono debe tener %(length)s dígitos."

ARGENTINA = "+54"
CHILE = "+56"
COLOMBIA = "+57"
ECUADOR = "+593"
MEXICO = "+52"
PERU = "+51"
REPUBLICA_DOMINICANA = "+1-809"
URUGUAY = "+598"
VENEZUELA = "+58"

COUNTRY_OPERATOR_PREFIX = {
    ARGENTINA: {"9"},
    CHILE: {"9"},
    COLOMBIA: {
        "300",
        "301",
        "302",
        "303",
        "304",
        "305",
        "310",
        "311",
        "312",
        "313",
        "314",
        "315",
        "316",
        "317",
        "318",
        "319",
        "320",
        "321",
        "322",
        "323",
        "324",
        "350",
        "351",
    },
    ECUADOR: {"09"},
    MEXICO: {},
    PERU: {"9"},
    REPUBLICA_DOMINICANA: {"809", "829", "849"},
    URUGUAY: {"09"},
    VENEZUELA: {"424", "414", "412", "416", "426"},
}


class CountryPhonePrefix(TextChoices):
    ARGENTINA = ARGENTINA, "AR (+54)"
    CHILE = CHILE, "CL (+56)"
    COLOMBIA = COLOMBIA, "CO (+57)"
    ECUADOR = ECUADOR, "EC (+593)"
    MEXICO = MEXICO, "MX (+52)"
    PERU = PERU, "PE (+51)"
    REPUBLICA_DOMINICANA = REPUBLICA_DOMINICANA, "DO (+1-809)"
    URUGUAY = URUGUAY, "UY (+598)"
    VENEZUELA = VENEZUELA, "VE (+58)"


class CountryPhoneLength(TextChoices):
    ARGENTINA = ARGENTINA, "10"
    CHILE = CHILE, "8"
    COLOMBIA = COLOMBIA, "7"
    ECUADOR = ECUADOR, "8"
    MEXICO = MEXICO, "10"
    PERU = PERU, "8"
    REPUBLICA_DOMINICANA = REPUBLICA_DOMINICANA, "7"
    URUGUAY = URUGUAY, "7"
    VENEZUELA = VENEZUELA, "7"


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
            if self.prefix_value != COLOMBIA
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
