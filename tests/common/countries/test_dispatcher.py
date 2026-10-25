from django.test import SimpleTestCase

from apps.common.utils.countries.base import (
    CountryValidator,
    IdentifierValidator,
    PhoneValidator,
)
from apps.common.utils.countries.constants import (
    COUNTRY_OPERATOR_PREFIX,
    Country,
    CountryPhoneLength,
    CountryPhonePrefix,
)
from apps.common.utils.countries.dispatcher import CountryDispatcher


class CountryDispatcherTests(SimpleTestCase):
    def test_every_supported_country_has_its_validator(self):
        self.assertEqual(set(CountryDispatcher.validators), set(Country.values))

    def test_every_validator_follows_the_contract(self):
        for country, validator in CountryDispatcher.validators.items():
            with self.subTest(country=country):
                self.assertIsInstance(validator, CountryValidator)
                self.assertEqual(validator.country, country)
                self.assertIsInstance(validator.phone, PhoneValidator)
                self.assertIsInstance(validator.identifier, IdentifierValidator)
                self.assertIn("pasaporte", validator.identifier.types.values)

    def test_phone_rules_match_the_current_phone_constants(self):
        lengths = dict(CountryPhoneLength.choices)
        for member in Country:
            with self.subTest(country=member.value):
                phone = CountryDispatcher.get_validator(member.value).phone
                prefix = CountryPhonePrefix[member.name]
                self.assertEqual(phone.prefix, prefix)
                self.assertEqual(phone.length, int(lengths[prefix]))
                self.assertEqual(
                    set(phone.operator_prefixes), set(COUNTRY_OPERATOR_PREFIX[prefix])
                )

    def test_sends_each_identifier_to_its_country(self):
        self.assertEqual(
            CountryDispatcher.validate_identifier("CL", "rut", "12.345.678-5").value,
            "12345678-5",
        )
        self.assertEqual(
            CountryDispatcher.validate_identifier("VE", "cedula", "v-12.345.678").value,
            "V-12345678",
        )
        self.assertIn(
            "no corresponde",
            CountryDispatcher.validate_identifier("CL", "cedula", "V-12345678").value,
        )

    def test_sends_each_phone_to_its_country(self):
        self.assertEqual(
            CountryDispatcher.validate_phone("CL", "9 1234 5678").value, "+56912345678"
        )
        self.assertIn(
            "prefijo", CountryDispatcher.validate_phone("VE", "912345678").value
        )

    def test_lists_the_identifier_types_of_each_country(self):
        self.assertEqual(
            CountryDispatcher.identifier_types("MX"),
            [("curp", "CURP"), ("pasaporte", "Pasaporte")],
        )

    def test_finds_the_country_of_a_phone_prefix(self):
        self.assertEqual(CountryDispatcher.country_for_phone_prefix("+56"), "CL")
        self.assertEqual(CountryDispatcher.country_for_phone_prefix("+1-809"), "DO")

    def test_uses_chile_when_the_country_is_missing_or_unsupported(self):
        chile = CountryDispatcher.validators["CL"]
        for country in (None, "", "ES"):
            with self.subTest(country=country):
                self.assertIs(CountryDispatcher.get_validator(country), chile)
                self.assertEqual(
                    CountryDispatcher.identifier_types(country),
                    [("rut", "RUT"), ("pasaporte", "Pasaporte")],
                )
                self.assertEqual(
                    CountryDispatcher.validate_identifier(
                        country, "rut", "12.345.678-5"
                    ).value,
                    "12345678-5",
                )
                self.assertEqual(
                    CountryDispatcher.validate_phone(country, "912345678").value,
                    "+56912345678",
                )
        self.assertEqual(CountryDispatcher.country_for_phone_prefix("+34"), "CL")
