import re
from decimal import Decimal, InvalidOperation

from django.contrib.auth.password_validation import (
    CommonPasswordValidator,
    UserAttributeSimilarityValidator,
    validate_password,
)
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.forms import BaseFormSet
from result import Err, Ok, Result

from apps.common.utils.businesses import BusinessCleaner
from apps.common.utils.countries.base import IDENTIFIER_TYPE_INVALID_MESSAGE
from apps.common.utils.countries.dispatcher import CountryDispatcher
from apps.common.utils.passwords import PasswordPolicyValidator

USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 30
USERNAME_PATTERN = re.compile(r"^[a-z][a-z0-9._-]*$")
NATIONAL_ID_COUNTRY_MISSING = "Elige el país del identificador nacional."
NATIONAL_ID_TYPE_MISSING = "Elige el tipo de identificador nacional."
NATIONAL_ID_NUMBER_MISSING = "Escribe el identificador nacional del tipo elegido."
NATIONAL_ID_TAKEN = "Ese identificador nacional ya lo tiene %(holder)s."
EMAIL_TAKEN = "Ese correo ya lo usa %(holder)s."
PHONE_TAKEN = "Ese teléfono ya lo usa %(holder)s."

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


def get_form_errors_to_response(form):
    main_field = getattr(form, "non_field_errors_target", None) or next(iter(form.fields))
    return [
        {
            "id_element": f"id_{form.add_prefix(main_field if field == NON_FIELD_ERRORS else field)}",
            "error": error[0],
        }
        for field, error in form.errors.items()
        if error
    ]


def get_formset_errors_to_response(formset):
    errors = [
        error
        for form in formset.forms
        if not form.cleaned_data.get("DELETE")
        for error in get_form_errors_to_response(form)
    ]
    if formset.non_form_errors():
        errors.append(
            {"id_element": f"id_{formset.prefix}-errors", "error": formset.non_form_errors()[0]}
        )
    return errors


def get_related_errors_to_response(related_form):
    if isinstance(related_form, BaseFormSet):
        return get_formset_errors_to_response(related_form)
    return get_form_errors_to_response(related_form)


def is_ascii_digit(character):
    return character.isascii() and character.isdigit()


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Classes


class CommonCleaner(PasswordPolicyValidator, BusinessCleaner):
    @staticmethod
    def clean_username_field(field_value: str) -> Result[str, str]:
        value = field_value.strip()
        if any(character.isupper() for character in value):
            return Err("El usuario debe ir en minúsculas.")
        if not USERNAME_MIN_LENGTH <= len(value) <= USERNAME_MAX_LENGTH:
            return Err(
                f"El usuario debe tener entre {USERNAME_MIN_LENGTH} y {USERNAME_MAX_LENGTH} caracteres."
            )
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
                password_validators=[
                    UserAttributeSimilarityValidator(),
                    CommonPasswordValidator(),
                ],
            )
        except ValidationError as error:
            return Err(error.messages[0])
        return Ok(field_value)

    @staticmethod
    def clean_alphabetic_field(
        field_name: str, field_value: str, allow_dots: bool = False
    ) -> Result[str, str]:
        """
        Cleans a string field to contain
        only alphabetic characters and spaces.
        """
        value = ""
        for character in field_value:
            if not (
                character.isalpha()
                or character.isspace()
                or (allow_dots and character == ".")
            ):
                allowed = (
                    "caracteres alfabéticos, espacios y puntos"
                    if allow_dots
                    else "caracteres alfabéticos y espacios"
                )
                return Err(f"El campo '{field_name}' debe solo contener {allowed}.")
            value += character
        return Ok(value.strip())

    @staticmethod
    def clean_alphanumeric_field(
        field_name: str, field_value: str, allow_dots: bool = False
    ) -> Result[str, str]:
        for character in field_value:
            if not (
                character.isalpha()
                or is_ascii_digit(character)
                or character.isspace()
                or (allow_dots and character == ".")
            ):
                allowed = (
                    "letras, números, espacios y puntos"
                    if allow_dots
                    else "letras, números y espacios"
                )
                return Err(f"El campo '{field_name}' debe solo contener {allowed}.")
        return Ok(field_value.strip())

    @staticmethod
    def clean_numeric_field(field_name: str, field_value: str) -> Result[str, str]:
        if not all(is_ascii_digit(character) for character in field_value):
            return Err(f"El campo '{field_name}' debe solo contener números.")
        return Ok(field_value)

    @staticmethod
    def check_unique(queryset, message: str, **lookup) -> Result[None, str]:
        """
        Err(message) when another record of the queryset already has these values.
        """
        if queryset.filter(**lookup).exists():
            return Err(message)
        return Ok(None)

    @classmethod
    def check_national_identifier_available(
        cls, queryset, holder: str, country: str, identifier_type: str, number: str
    ) -> Result[None, str]:
        return cls.check_unique(
            queryset,
            NATIONAL_ID_TAKEN % {"holder": holder},
            pais=country,
            tipo_identificador_nacional=identifier_type,
            identificador_nacional=number,
        )

    @classmethod
    def check_email_available(
        cls, queryset, holder: str, email: str, field: str = "email"
    ) -> Result[None, str]:
        return cls.check_unique(
            queryset, EMAIL_TAKEN % {"holder": holder}, **{f"{field}__iexact": email}
        )

    @classmethod
    def check_phone_available(
        cls, queryset, holder: str, **lookup
    ) -> Result[None, str]:
        return cls.check_unique(queryset, PHONE_TAKEN % {"holder": holder}, **lookup)

    @staticmethod
    def clean_national_identifier(
        country: str, identifier_type: str, number: str
    ) -> Result[str | None, dict]:
        """
        Optional national identifier: type and number go together and need a country.
        Errors come keyed by "country", "type" or "number".
        """
        if not (identifier_type or number):
            return Ok(None)
        errors = {}
        if not country:
            errors["country"] = NATIONAL_ID_COUNTRY_MISSING
        if not identifier_type:
            errors["type"] = NATIONAL_ID_TYPE_MISSING
        if not number:
            errors["number"] = NATIONAL_ID_NUMBER_MISSING
        if errors:
            return Err(errors)
        result = CountryDispatcher.validate_identifier(country, identifier_type, number)
        if result.is_err():
            invalid_type = result.err_value == IDENTIFIER_TYPE_INVALID_MESSAGE
            key = "type" if invalid_type else "number"
            return Err({key: result.err_value})
        return result

    @staticmethod
    def clean_phone_field(prefix_value: str, phone_number: str) -> Result[str, str]:
        """
        Cleans a phone number field with the rules of the prefix's country.
        """
        return CountryDispatcher.validate_phone_with_prefix(prefix_value, phone_number)

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

    @staticmethod
    def clean_amount_field(field_name: str, field_value) -> Result[Decimal, str]:
        if field_value is None or field_value == "":
            return Ok(Decimal("0"))
        try:
            value = Decimal(str(field_value).replace(" ", ""))
        except InvalidOperation:
            return Err(f"El campo '{field_name}' debe ser un número válido: {field_value}.")
        if not value.is_finite():
            return Err(f"El campo '{field_name}' debe ser un número válido: {field_value}.")
        if value < 0:
            return Err(f"El campo '{field_name}' no puede ser negativo.")
        return Ok(value)


# endregion
"""========================================================================="""
