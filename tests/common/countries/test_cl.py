from django.test import SimpleTestCase

from apps.common.utils.countries.cl.constants import IdentifierType
from apps.common.utils.countries.cl.validator import ChileValidator

VALIDATOR = ChileValidator()


class ChilePhoneTests(SimpleTestCase):
    def test_accepts_mobile_numbers_with_separators(self):
        for number in ("912345678", "9 1234 5678", "9-1234-5678"):
            with self.subTest(number=number):
                self.assertEqual(VALIDATOR.validate_phone(number).value, "+56912345678")

    def test_rejects_wrong_operator_length_or_characters(self):
        cases = {
            "812345678": "prefijo",
            "91234567": "8 dígitos",
            "9123a5678": "solo debe contener",
        }
        for number, message in cases.items():
            with self.subTest(number=number):
                self.assertIn(message, VALIDATOR.validate_phone(number).value)


class ChileIdentifierTests(SimpleTestCase):
    def test_accepts_ruts_in_any_common_format(self):
        for number in ("12.345.678-5", "12345678-5", "123456785", " 12345678-5 "):
            with self.subTest(number=number):
                self.assertEqual(
                    VALIDATOR.validate_identifier(IdentifierType.RUT, number).value,
                    "12345678-5",
                )

    def test_accepts_k_as_check_digit_in_any_case(self):
        for number in ("10.000.013-K", "10000013-k"):
            with self.subTest(number=number):
                self.assertEqual(
                    VALIDATOR.validate_identifier(IdentifierType.RUT, number).value,
                    "10000013-K",
                )

    def test_rejects_a_wrong_check_digit(self):
        self.assertIn(
            "dígito verificador",
            VALIDATOR.validate_identifier(IdentifierType.RUT, "12.345.678-9").value,
        )

    def test_rejects_malformed_ruts(self):
        for number in ("123456-0", "123.456.789-1", "12345678-X", "12a45678-5", ""):
            with self.subTest(number=number):
                self.assertIn(
                    "entre 7 y 8 dígitos",
                    VALIDATOR.validate_identifier(IdentifierType.RUT, number).value,
                )

    def test_validates_passports(self):
        self.assertEqual(
            VALIDATOR.validate_identifier(
                IdentifierType.PASSPORT, " f1234 5678 "
            ).value,
            "F12345678",
        )
        self.assertIn(
            "entre 6 y 12",
            VALIDATOR.validate_identifier(IdentifierType.PASSPORT, "F-123").value,
        )

    def test_rejects_types_from_other_countries(self):
        self.assertIn(
            "no corresponde",
            VALIDATOR.validate_identifier("cedula", "V-12345678").value,
        )
