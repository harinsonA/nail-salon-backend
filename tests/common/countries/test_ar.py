from django.test import SimpleTestCase

from apps.common.utils.countries.ar.constants import IdentifierType
from apps.common.utils.countries.ar.validator import ArgentinaValidator

VALIDATOR = ArgentinaValidator()


class ArgentinaPhoneTests(SimpleTestCase):
    def test_accepts_mobile_numbers(self):
        self.assertEqual(
            VALIDATOR.validate_phone("9 11 1234 5678").value, "+5491112345678"
        )

    def test_rejects_wrong_operator_or_length(self):
        self.assertIn("prefijo", VALIDATOR.validate_phone("1112345678").value)
        self.assertIn("10 dígitos", VALIDATOR.validate_phone("911123456").value)


class ArgentinaIdentifierTests(SimpleTestCase):
    def test_accepts_dnis_with_or_without_dots(self):
        for number in ("12.345.678", "12345678", "1.234.567"):
            with self.subTest(number=number):
                self.assertEqual(
                    VALIDATOR.validate_identifier(IdentifierType.DNI, number).value,
                    number.replace(".", ""),
                )

    def test_rejects_malformed_dnis(self):
        for number in ("123456", "123456789", "12.345.67A", ""):
            with self.subTest(number=number):
                self.assertIn(
                    "entre 7 y 8 dígitos",
                    VALIDATOR.validate_identifier(IdentifierType.DNI, number).value,
                )

    def test_validates_passports(self):
        self.assertEqual(
            VALIDATOR.validate_identifier(IdentifierType.PASSPORT, "aaa123456").value,
            "AAA123456",
        )

    def test_rejects_types_from_other_countries(self):
        self.assertIn(
            "no corresponde", VALIDATOR.validate_identifier("rut", "12345678-5").value
        )
