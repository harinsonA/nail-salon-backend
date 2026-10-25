from django.db.models import TextChoices

"""========================================================================="""
# region ........ Constants

COUNTRY_KEY = "ECUADOR"
COUNTRY_CODE = "EC"
COUNTRY_NAME = "Ecuador"

PHONE_PREFIX = "+593"
PHONE_LENGTH = 8
PHONE_OPERATOR_PREFIXES = ("09",)

CEDULA_LENGTH = 10
CEDULA_PROVINCES = {f"{code:02d}" for code in range(1, 25)} | {"30"}
CEDULA_MAX_THIRD_DIGIT = 5
PASSPORT_MIN_LENGTH = 6
PASSPORT_MAX_LENGTH = 12


class IdentifierType(TextChoices):
    CEDULA = "cedula", "Cédula de identidad"
    PASSPORT = "pasaporte", "Pasaporte"


# endregion
"""========================================================================="""
