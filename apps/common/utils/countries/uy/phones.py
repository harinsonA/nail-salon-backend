from apps.common.utils.countries.base import PhoneValidator
from apps.common.utils.countries.uy.constants import (
    PHONE_LENGTH,
    PHONE_OPERATOR_PREFIXES,
    PHONE_PREFIX,
)

"""========================================================================="""
# region ........ Classes


class UruguayPhoneValidator(PhoneValidator):
    prefix = PHONE_PREFIX
    length = PHONE_LENGTH
    operator_prefixes = PHONE_OPERATOR_PREFIXES


# endregion
"""========================================================================="""
