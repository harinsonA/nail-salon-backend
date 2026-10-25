from django.db.models import TextChoices

"""========================================================================="""
# region ........ Constants

COUNTRY_KEY = "REPUBLICA_DOMINICANA"
COUNTRY_CODE = "DO"
COUNTRY_NAME = "República Dominicana"

PHONE_PREFIX = "+1-809"
PHONE_LENGTH = 7
PHONE_OPERATOR_PREFIXES = ("809", "829", "849")

CEDULA_LENGTH = 11
PASSPORT_MIN_LENGTH = 6
PASSPORT_MAX_LENGTH = 12


class IdentifierType(TextChoices):
    CEDULA = "cedula", "Cédula de identidad y electoral"
    PASSPORT = "pasaporte", "Pasaporte"


# endregion
"""========================================================================="""
