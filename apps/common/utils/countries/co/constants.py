from django.db.models import TextChoices

"""========================================================================="""
# region ........ Constants

COUNTRY_KEY = "COLOMBIA"
COUNTRY_CODE = "CO"
COUNTRY_NAME = "Colombia"

PHONE_PREFIX = "+57"
PHONE_LENGTH = 7
PHONE_OPERATOR_PREFIXES = (
    "300",
    "301",
    "302",
    "303",
    "304",
    "305",
    "310",
    "311",
    "312",
    "313",
    "314",
    "315",
    "316",
    "317",
    "318",
    "319",
    "320",
    "321",
    "322",
    "323",
    "324",
    "350",
    "351",
)

CEDULA_MIN_LENGTH = 6
CEDULA_MAX_LENGTH = 10
PASSPORT_MIN_LENGTH = 6
PASSPORT_MAX_LENGTH = 12


class IdentifierType(TextChoices):
    CEDULA = "cedula", "Cédula de ciudadanía"
    PASSPORT = "pasaporte", "Pasaporte"


# endregion
"""========================================================================="""
