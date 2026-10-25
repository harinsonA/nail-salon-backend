from django.db.models import TextChoices

"""========================================================================="""
# region ........ Constants

COUNTRY_KEY = "MEXICO"
COUNTRY_CODE = "MX"
COUNTRY_NAME = "México"

PHONE_PREFIX = "+52"
PHONE_LENGTH = 10
PHONE_OPERATOR_PREFIXES = ()

CURP_PATTERN = r"[A-Z][AEIOUX][A-Z]{2}\d{6}[HMX][A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z\d]\d"
CURP_ALPHABET = "0123456789ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"
PASSPORT_MIN_LENGTH = 6
PASSPORT_MAX_LENGTH = 12


class IdentifierType(TextChoices):
    CURP = "curp", "CURP"
    PASSPORT = "pasaporte", "Pasaporte"


# endregion
"""========================================================================="""
