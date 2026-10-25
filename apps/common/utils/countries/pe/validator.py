from apps.common.utils.countries.base import CountryValidator
from apps.common.utils.countries.pe.constants import COUNTRY_CODE
from apps.common.utils.countries.pe.identifiers import PeruIdentifierValidator
from apps.common.utils.countries.pe.phones import PeruPhoneValidator

"""========================================================================="""
# region ........ Classes


class PeruValidator(CountryValidator):
    country = COUNTRY_CODE
    phone = PeruPhoneValidator()
    identifier = PeruIdentifierValidator()


# endregion
"""========================================================================="""
