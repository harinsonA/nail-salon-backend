from django.test import SimpleTestCase

from apps.common.utils.countries.ec.constants import IdentifierType
from apps.common.utils.countries.ec.validator import EcuadorValidator

VALIDATOR = EcuadorValidator()


def validate_cedula(number):
    return VALIDATOR.validate_identifier(IdentifierType.CEDULA, number)


class EcuadorPhoneTests(SimpleTestCase):
    def test_accepts_mobile_numbers(self):
        self.assertEqual(
            VALIDATOR.validate_phone("09 1234 5678").value, "+5930912345678"
        )

    def test_rejects_wrong_operator(self):
        self.assertIn("prefijo", VALIDATOR.validate_phone("0212345678").value)


class EcuadorIdentifierTests(SimpleTestCase):
    def test_accepts_valid_cedulas(self):
        for number in ("1710034065", "171003406-5"):
            with self.subTest(number=number):
                self.assertEqual(validate_cedula(number).value, "1710034065")

    def test_rejects_wrong_length(self):
        for number in ("171003406", "17100340651", ""):
            with self.subTest(number=number):
                self.assertIn("10 dígitos", validate_cedula(number).value)

    def test_rejects_unknown_provinces(self):
        for number in ("0010034065", "2510034065"):
            with self.subTest(number=number):
                self.assertIn("provincia", validate_cedula(number).value)

    def test_rejects_a_third_digit_above_five(self):
        self.assertIn("tercer dígito", validate_cedula("1760034065").value)

    def test_rejects_a_wrong_check_digit(self):
        self.assertIn("verificador", validate_cedula("1710034064").value)
