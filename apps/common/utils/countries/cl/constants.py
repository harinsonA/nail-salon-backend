from django.db.models import TextChoices

"""========================================================================="""
# region ........ Constants

COUNTRY_KEY = "CHILE"
COUNTRY_CODE = "CL"
COUNTRY_NAME = "Chile"

PHONE_PREFIX = "+56"
PHONE_LENGTH = 8
PHONE_OPERATOR_PREFIXES = ("9",)

RUT_BODY_MIN_LENGTH = 7
RUT_BODY_MAX_LENGTH = 8
PASSPORT_MIN_LENGTH = 6
PASSPORT_MAX_LENGTH = 12


class IdentifierType(TextChoices):
    RUT = "rut", "RUT"
    PASSPORT = "pasaporte", "Pasaporte"


# endregion
"""========================================================================="""
