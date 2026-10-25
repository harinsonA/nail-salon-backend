from apps.common.utils.countries.base import PhoneValidator
from apps.common.utils.countries.ve.constants import (
    PHONE_LENGTH,
    PHONE_OPERATOR_PREFIXES,
    PHONE_PREFIX,
)

"""========================================================================="""
# region ........ Classes


class VenezuelaPhoneValidator(PhoneValidator):
    prefix = PHONE_PREFIX
    length = PHONE_LENGTH
    operator_prefixes = PHONE_OPERATOR_PREFIXES


# endregion
"""========================================================================="""
