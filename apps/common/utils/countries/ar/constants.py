from django.db.models import TextChoices

"""========================================================================="""
# region ........ Constants

COUNTRY_KEY = "ARGENTINA"
COUNTRY_CODE = "AR"
COUNTRY_NAME = "Argentina"

PHONE_PREFIX = "+54"
PHONE_LENGTH = 10
PHONE_OPERATOR_PREFIXES = ("9",)

DNI_MIN_LENGTH = 7
DNI_MAX_LENGTH = 8
PASSPORT_MIN_LENGTH = 6
PASSPORT_MAX_LENGTH = 12


class IdentifierType(TextChoices):
    DNI = "dni", "DNI"
    PASSPORT = "pasaporte", "Pasaporte"


# endregion
"""========================================================================="""
