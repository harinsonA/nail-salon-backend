from apps.common.utils.countries.base import CountryValidator
from apps.common.utils.countries.cl.constants import COUNTRY_CODE
from apps.common.utils.countries.cl.identifiers import ChileIdentifierValidator
from apps.common.utils.countries.cl.phones import ChilePhoneValidator

"""========================================================================="""
# region ........ Classes


class ChileValidator(CountryValidator):
    country = COUNTRY_CODE
    phone = ChilePhoneValidator()
    identifier = ChileIdentifierValidator()


# endregion
"""========================================================================="""
