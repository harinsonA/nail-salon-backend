from apps.common.utils.countries.base import CountryValidator
from apps.common.utils.countries.do.constants import COUNTRY_CODE
from apps.common.utils.countries.do.identifiers import (
    DominicanRepublicIdentifierValidator,
)
from apps.common.utils.countries.do.phones import DominicanRepublicPhoneValidator

"""========================================================================="""
# region ........ Classes


class DominicanRepublicValidator(CountryValidator):
    country = COUNTRY_CODE
    phone = DominicanRepublicPhoneValidator()
    identifier = DominicanRepublicIdentifierValidator()


# endregion
"""========================================================================="""
