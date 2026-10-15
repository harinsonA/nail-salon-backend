import re

from django.contrib.auth.password_validation import (
    CommonPasswordValidator,
    UserAttributeSimilarityValidator,
    validate_password,
)
from django.core.exceptions import ValidationError
from result import Result, Ok, Err
from apps.common.utils.passwords import PasswordPolicyValidator
from apps.common.utils.phones import PhoneCleaner

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30
USERNAME_PATTERN = re.compile(r"^[a-z][a-z0-9._-]*$")

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


class CommonCleaner(PasswordPolicyValidator):
    @staticmethod
    def clean_username_field(field_value: str) -> Result[str, str]:
        value = field_value.strip()
        if any(character.isupper() for character in value):
            return Err("El usuario debe ir en minúsculas.")
        if not USERNAME_MIN_LENGTH <= len(value) <= USERNAME_MAX_LENGTH:
            return Err(f"El usuario debe tener entre {USERNAME_MIN_LENGTH} y {USERNAME_MAX_LENGTH} caracteres.")
        if not USERNAME_PATTERN.match(value):
            return Err(
                "El usuario debe empezar con una letra y solo admite letras minúsculas sin tilde, "
                "números, punto, guion y guion bajo."
            )
        return Ok(value)

    @classmethod
    def clean_password_field(cls, field_value: str, user=None) -> Result[str, str]:
        message = cls().password_policy_error(field_value)
        if message:
            return Err(message)
        try:
            validate_password(
                field_value,
                user=user,
                password_validators=[UserAttributeSimilarityValidator(), CommonPasswordValidator()],
            )
        except ValidationError as error:
            return Err(error.messages[0])
        return Ok(field_value)

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
