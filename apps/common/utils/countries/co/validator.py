from apps.common.utils.countries.base import CountryValidator
from apps.common.utils.countries.co.constants import COUNTRY_CODE
from apps.common.utils.countries.co.identifiers import ColombiaIdentifierValidator
from apps.common.utils.countries.co.phones import ColombiaPhoneValidator

"""========================================================================="""
# region ........ Classes


class ColombiaValidator(CountryValidator):
    country = COUNTRY_CODE
    phone = ColombiaPhoneValidator()
    identifier = ColombiaIdentifierValidator()


# endregion
"""========================================================================="""
