from django.db.models import TextChoices

"""========================================================================="""
# region ........ Constants

COUNTRY_KEY = "PERU"
COUNTRY_CODE = "PE"
COUNTRY_NAME = "Perú"

PHONE_PREFIX = "+51"
PHONE_LENGTH = 8
PHONE_OPERATOR_PREFIXES = ("9",)

DNI_LENGTH = 8
PASSPORT_MIN_LENGTH = 6
PASSPORT_MAX_LENGTH = 12


class IdentifierType(TextChoices):
    DNI = "dni", "DNI"
    PASSPORT = "pasaporte", "Pasaporte"


# endregion
"""========================================================================="""
