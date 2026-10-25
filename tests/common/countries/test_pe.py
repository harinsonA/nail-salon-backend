from django.test import SimpleTestCase

from apps.common.utils.countries.pe.constants import IdentifierType
from apps.common.utils.countries.pe.validator import PeruValidator

VALIDATOR = PeruValidator()


class PeruPhoneTests(SimpleTestCase):
    def test_accepts_mobile_numbers(self):
        self.assertEqual(VALIDATOR.validate_phone("912 345 678").value, "+51912345678")

    def test_rejects_wrong_operator(self):
        self.assertIn("prefijo", VALIDATOR.validate_phone("112345678").value)


class PeruIdentifierTests(SimpleTestCase):
    def test_accepts_eight_digit_dnis_keeping_leading_zeros(self):
        for number in ("12345678", "01234567", "1234 5678"):
            with self.subTest(number=number):
                self.assertEqual(
                    VALIDATOR.validate_identifier(IdentifierType.DNI, number).value,
                    number.replace(" ", ""),
                )

    def test_rejects_other_lengths(self):
        for number in ("1234567", "123456789", ""):
            with self.subTest(number=number):
                self.assertIn(
                    "8 dígitos",
                    VALIDATOR.validate_identifier(IdentifierType.DNI, number).value,
                )
