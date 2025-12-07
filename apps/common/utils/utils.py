from result import Result, Ok, Err
from apps.common.utils.phones import PhoneCleaner

"""========================================================================="""
# region ........ functions


def get_errors_to_response(errors):
    errors = dict(errors)
    if not errors:
        return []
    return [
        {
            "id_element": f"id_{field}",
            "error": error[0],
        }
        for field, error in errors.items()
        if error
    ]


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Classes


class CommonCleaner:
    @staticmethod
    def clean_alphabetic_field(field_name: str, field_value: str) -> Result[str, str]:
        """
        Cleans a string field to contain
        only alphabetic characters and spaces.
        """
        value = ""
        for character in field_value:
            if not (character.isalpha() or character.isspace()):
                return Err(
                    f"El campo '{field_name}' debe solo contener "
                    "caracteres alfabéticos y espacios."
                )
            value += character
        return Ok(value.strip())

    @staticmethod
    def clean_phone_field(prefix_value: str, phone_number: str) -> Result[str, str]:
        """
        Cleans a phone number field using PhoneCleaner.
        """
        phone_cleaner = PhoneCleaner(prefix_value)
        return phone_cleaner.is_valid(phone_number)

    @staticmethod
    def clean_250_characters_field(
        field_name: str, field_value: str
    ) -> Result[str, str]:
        """
        Cleans a string field to ensure it does not exceed 250 characters.
        """
        if len(field_value) > 250:
            return Err(f"El campo '{field_name}' no debe exceder 250 caracteres.")
        return Ok(field_value.strip())


# endregion
"""========================================================================="""
