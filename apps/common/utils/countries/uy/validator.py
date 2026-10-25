from apps.common.utils.countries.base import CountryValidator
from apps.common.utils.countries.uy.constants import COUNTRY_CODE
from apps.common.utils.countries.uy.identifiers import UruguayIdentifierValidator
from apps.common.utils.countries.uy.phones import UruguayPhoneValidator

"""========================================================================="""
# region ........ Classes


class UruguayValidator(CountryValidator):
    country = COUNTRY_CODE
    phone = UruguayPhoneValidator()
    identifier = UruguayIdentifierValidator()


# endregion
"""========================================================================="""
