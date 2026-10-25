from apps.common.utils.countries.base import CountryValidator
from apps.common.utils.countries.ve.constants import COUNTRY_CODE
from apps.common.utils.countries.ve.identifiers import VenezuelaIdentifierValidator
from apps.common.utils.countries.ve.phones import VenezuelaPhoneValidator

"""========================================================================="""
# region ........ Classes


class VenezuelaValidator(CountryValidator):
    country = COUNTRY_CODE
    phone = VenezuelaPhoneValidator()
    identifier = VenezuelaIdentifierValidator()


# endregion
"""========================================================================="""
