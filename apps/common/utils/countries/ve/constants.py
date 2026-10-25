from django.db.models import TextChoices

"""========================================================================="""
# region ........ Constants

COUNTRY_KEY = "VENEZUELA"
COUNTRY_CODE = "VE"
COUNTRY_NAME = "Venezuela"

PHONE_PREFIX = "+58"
PHONE_LENGTH = 7
PHONE_OPERATOR_PREFIXES = ("412", "414", "416", "424", "426")

CEDULA_NATIONALITIES = ("V", "E")
CEDULA_MIN_LENGTH = 6
CEDULA_MAX_LENGTH = 8
PASSPORT_MIN_LENGTH = 6
PASSPORT_MAX_LENGTH = 12


class IdentifierType(TextChoices):
    CEDULA = "cedula", "Cédula de identidad"
    PASSPORT = "pasaporte", "Pasaporte"


# endregion
"""========================================================================="""
