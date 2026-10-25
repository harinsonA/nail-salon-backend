from django.db.models import TextChoices

from apps.common.utils.countries.ar import constants as argentina
from apps.common.utils.countries.cl import constants as chile
from apps.common.utils.countries.co import constants as colombia
from apps.common.utils.countries.do import constants as dominican_republic
from apps.common.utils.countries.ec import constants as ecuador
from apps.common.utils.countries.mx import constants as mexico
from apps.common.utils.countries.pe import constants as peru
from apps.common.utils.countries.uy import constants as uruguay
from apps.common.utils.countries.ve import constants as venezuela

"""========================================================================="""
# region ........ Helpers


def phone_prefix_label(country) -> str:
    return f"{country.COUNTRY_CODE} ({country.PHONE_PREFIX})"


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Constants

COUNTRIES = (
    argentina,
    chile,
    colombia,
    ecuador,
    mexico,
    peru,
    dominican_republic,
    uruguay,
    venezuela,
)


class Country(TextChoices):
    ARGENTINA = argentina.COUNTRY_CODE, argentina.COUNTRY_NAME
    CHILE = chile.COUNTRY_CODE, chile.COUNTRY_NAME
    COLOMBIA = colombia.COUNTRY_CODE, colombia.COUNTRY_NAME
    ECUADOR = ecuador.COUNTRY_CODE, ecuador.COUNTRY_NAME
    MEXICO = mexico.COUNTRY_CODE, mexico.COUNTRY_NAME
    PERU = peru.COUNTRY_CODE, peru.COUNTRY_NAME
    REPUBLICA_DOMINICANA = (
        dominican_republic.COUNTRY_CODE,
        dominican_republic.COUNTRY_NAME,
    )
    URUGUAY = uruguay.COUNTRY_CODE, uruguay.COUNTRY_NAME
    VENEZUELA = venezuela.COUNTRY_CODE, venezuela.COUNTRY_NAME


class CountryPhonePrefix(TextChoices):
    ARGENTINA = argentina.PHONE_PREFIX, phone_prefix_label(argentina)
    CHILE = chile.PHONE_PREFIX, phone_prefix_label(chile)
    COLOMBIA = colombia.PHONE_PREFIX, phone_prefix_label(colombia)
    ECUADOR = ecuador.PHONE_PREFIX, phone_prefix_label(ecuador)
    MEXICO = mexico.PHONE_PREFIX, phone_prefix_label(mexico)
    PERU = peru.PHONE_PREFIX, phone_prefix_label(peru)
    REPUBLICA_DOMINICANA = (
        dominican_republic.PHONE_PREFIX,
        phone_prefix_label(dominican_republic),
    )
    URUGUAY = uruguay.PHONE_PREFIX, phone_prefix_label(uruguay)
    VENEZUELA = venezuela.PHONE_PREFIX, phone_prefix_label(venezuela)


# endregion
"""========================================================================="""
