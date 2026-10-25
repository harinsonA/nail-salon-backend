from apps.common.utils.countries.ar.identifiers import ArgentinaIdentifierValidator
from apps.common.utils.countries.ar.phones import ArgentinaPhoneValidator
from apps.common.utils.countries.base import CountryValidator
from apps.common.utils.countries.ar.constants import COUNTRY_CODE

"""========================================================================="""
# region ........ Classes


class ArgentinaValidator(CountryValidator):
    country = COUNTRY_CODE
    phone = ArgentinaPhoneValidator()
    identifier = ArgentinaIdentifierValidator()


# endregion
"""========================================================================="""
