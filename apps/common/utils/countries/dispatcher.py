from result import Result

from apps.common.utils.countries.ar.validator import ArgentinaValidator
from apps.common.utils.countries.base import CountryValidator
from apps.common.utils.countries.cl.validator import ChileValidator
from apps.common.utils.countries.co.validator import ColombiaValidator
from apps.common.utils.countries.constants import Country
from apps.common.utils.countries.do.validator import DominicanRepublicValidator
from apps.common.utils.countries.ec.validator import EcuadorValidator
from apps.common.utils.countries.mx.validator import MexicoValidator
from apps.common.utils.countries.pe.validator import PeruValidator
from apps.common.utils.countries.uy.validator import UruguayValidator
from apps.common.utils.countries.ve.validator import VenezuelaValidator

"""========================================================================="""
# region ........ Constants

DEFAULT_COUNTRY = Country.CHILE


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Classes


class CountryDispatcher:
    validators: dict[str, CountryValidator] = {
        validator.country: validator
        for validator in (
            ArgentinaValidator(),
            ChileValidator(),
            ColombiaValidator(),
            EcuadorValidator(),
            MexicoValidator(),
            PeruValidator(),
            DominicanRepublicValidator(),
            UruguayValidator(),
            VenezuelaValidator(),
        )
    }

    @classmethod
    def get_validator(cls, country: str | None) -> CountryValidator:
        return cls.validators.get(country, cls.validators[DEFAULT_COUNTRY])

    @classmethod
    def country_for_phone_prefix(cls, prefix: str) -> str:
        for country, validator in cls.validators.items():
            if validator.phone.prefix == prefix:
                return country
        return DEFAULT_COUNTRY

    @classmethod
    def identifier_types(cls, country: str | None) -> list[tuple[str, str]]:
        return cls.get_validator(country).identifier_types()

    @classmethod
    def validate_phone(cls, country: str | None, number: str) -> Result[str, str]:
        return cls.get_validator(country).validate_phone(number)

    @classmethod
    def validate_identifier(
        cls, country: str | None, identifier_type: str, number: str
    ) -> Result[str, str]:
        return cls.get_validator(country).validate_identifier(identifier_type, number)


# endregion
"""========================================================================="""
