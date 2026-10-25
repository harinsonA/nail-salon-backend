from django.test import SimpleTestCase

from apps.common.utils.countries.uy.constants import IdentifierType
from apps.common.utils.countries.uy.validator import UruguayValidator

VALIDATOR = UruguayValidator()


def validate_cedula(number):
    return VALIDATOR.validate_identifier(IdentifierType.CEDULA, number)


class UruguayPhoneTests(SimpleTestCase):
    def test_accepts_mobile_numbers(self):
        self.assertEqual(VALIDATOR.validate_phone("09 123 4567").value, "+598091234567")

    def test_rejects_wrong_operator(self):
        self.assertIn("prefijo", VALIDATOR.validate_phone("021234567").value)


class UruguayIdentifierTests(SimpleTestCase):
    def test_accepts_valid_cedulas_in_any_common_format(self):
        for number in ("1.234.567-2", "1234567-2", "12345672"):
            with self.subTest(number=number):
                self.assertEqual(validate_cedula(number).value, "1234567-2")

    def test_accepts_old_cedulas_with_six_digits(self):
        self.assertEqual(validate_cedula("123.456-1").value, "123456-1")

    def test_rejects_wrong_length(self):
        for number in ("12345-6", "12.345.678-9", ""):
            with self.subTest(number=number):
                self.assertIn("entre 6 y 7 dígitos", validate_cedula(number).value)

    def test_rejects_a_wrong_check_digit(self):
        self.assertIn("verificador", validate_cedula("1.234.567-3").value)
