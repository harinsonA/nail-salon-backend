from django.test import SimpleTestCase

from apps.common.utils.countries.co.constants import IdentifierType
from apps.common.utils.countries.co.validator import ColombiaValidator

VALIDATOR = ColombiaValidator()


class ColombiaPhoneTests(SimpleTestCase):
    def test_accepts_mobile_numbers(self):
        self.assertEqual(
            VALIDATOR.validate_phone("300 123 4567").value, "+573001234567"
        )

    def test_rejects_wrong_operator_and_lists_only_some_prefixes(self):
        message = VALIDATOR.validate_phone("3991234567").value
        self.assertIn("prefijo", message)
        self.assertTrue(message.endswith("...)."))


class ColombiaIdentifierTests(SimpleTestCase):
    def test_accepts_cedulas_of_six_to_ten_digits(self):
        for number, expected in (
            ("1.020.304.050", "1020304050"),
            ("123456", "123456"),
            ("79 123 456", "79123456"),
        ):
            with self.subTest(number=number):
                self.assertEqual(
                    VALIDATOR.validate_identifier(IdentifierType.CEDULA, number).value,
                    expected,
                )

    def test_rejects_malformed_cedulas(self):
        for number in ("12345", "12345678901", "1020A04050", ""):
            with self.subTest(number=number):
                self.assertIn(
                    "entre 6 y 10 dígitos",
                    VALIDATOR.validate_identifier(IdentifierType.CEDULA, number).value,
                )

    def test_validates_passports(self):
        self.assertIn(
            "entre 6 y 12",
            VALIDATOR.validate_identifier(IdentifierType.PASSPORT, "AB12").value,
        )
