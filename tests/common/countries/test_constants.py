from django.test import SimpleTestCase

from apps.common.utils.countries.constants import (
    COUNTRIES,
    Country,
    CountryPhonePrefix,
    NationalIdentifierType,
)
from apps.common.utils.countries.dispatcher import CountryDispatcher


class CountryListsTests(SimpleTestCase):
    def test_every_list_has_one_member_per_country_in_the_same_order(self):
        keys = [country.COUNTRY_KEY for country in COUNTRIES]
        for choices in (Country, CountryPhonePrefix):
            with self.subTest(choices=choices.__name__):
                self.assertEqual(choices.names, keys)

    def test_each_member_takes_the_data_of_its_country(self):
        for country in COUNTRIES:
            with self.subTest(country=country.COUNTRY_CODE):
                self.assertEqual(Country[country.COUNTRY_KEY], country.COUNTRY_CODE)
                self.assertEqual(
                    Country[country.COUNTRY_KEY].label, country.COUNTRY_NAME
                )
                self.assertEqual(
                    CountryPhonePrefix[country.COUNTRY_KEY], country.PHONE_PREFIX
                )

    def test_every_identifier_type_of_every_country_is_in_the_shared_list(self):
        for country in Country.values:
            for code, _ in CountryDispatcher.identifier_types(country):
                with self.subTest(country=country, code=code):
                    self.assertIn(code, NationalIdentifierType.values)
