from apps.common.utils.countries.base import CountryValidator
from apps.common.utils.countries.mx.constants import COUNTRY_CODE
from apps.common.utils.countries.mx.identifiers import MexicoIdentifierValidator
from apps.common.utils.countries.mx.phones import MexicoPhoneValidator

"""========================================================================="""
# region ........ Classes


class MexicoValidator(CountryValidator):
    country = COUNTRY_CODE
    phone = MexicoPhoneValidator()
    identifier = MexicoIdentifierValidator()


# endregion
"""========================================================================="""
