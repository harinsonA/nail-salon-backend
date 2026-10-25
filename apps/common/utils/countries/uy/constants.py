from django.db.models import TextChoices

"""========================================================================="""
# region ........ Constants

COUNTRY_KEY = "URUGUAY"
COUNTRY_CODE = "UY"
COUNTRY_NAME = "Uruguay"

PHONE_PREFIX = "+598"
PHONE_LENGTH = 7
PHONE_OPERATOR_PREFIXES = ("09",)

CEDULA_BODY_MIN_LENGTH = 6
CEDULA_BODY_MAX_LENGTH = 7
CEDULA_CHECK_WEIGHTS = (2, 9, 8, 7, 6, 3, 4)
PASSPORT_MIN_LENGTH = 6
PASSPORT_MAX_LENGTH = 12


class IdentifierType(TextChoices):
    CEDULA = "cedula", "Cédula de identidad"
    PASSPORT = "pasaporte", "Pasaporte"


# endregion
"""========================================================================="""
