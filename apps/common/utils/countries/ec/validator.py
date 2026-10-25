from apps.common.utils.countries.base import CountryValidator
from apps.common.utils.countries.ec.constants import COUNTRY_CODE
from apps.common.utils.countries.ec.identifiers import EcuadorIdentifierValidator
from apps.common.utils.countries.ec.phones import EcuadorPhoneValidator

"""========================================================================="""
# region ........ Classes


class EcuadorValidator(CountryValidator):
    country = COUNTRY_CODE
    phone = EcuadorPhoneValidator()
    identifier = EcuadorIdentifierValidator()


# endregion
"""========================================================================="""
