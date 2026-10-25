from django.test import SimpleTestCase

from apps.common.utils.countries.ve.constants import IdentifierType
from apps.common.utils.countries.ve.validator import VenezuelaValidator

VALIDATOR = VenezuelaValidator()


class VenezuelaPhoneTests(SimpleTestCase):
    def test_accepts_every_mobile_operator(self):
        for operator in ("412", "414", "416", "424", "426"):
            with self.subTest(operator=operator):
                self.assertEqual(
                    VALIDATOR.validate_phone(f"{operator} 123 4567").value,
                    f"+58{operator}1234567",
                )

    def test_rejects_wrong_operator_or_length(self):
        self.assertIn("prefijo", VALIDATOR.validate_phone("4151234567").value)
        self.assertIn("7 dígitos", VALIDATOR.validate_phone("41412345").value)


class VenezuelaIdentifierTests(SimpleTestCase):
    def test_accepts_cedulas_in_any_common_format(self):
        for number in ("V-12.345.678", "v12345678", "V 12345678", "V-012345678"):
            with self.subTest(number=number):
                self.assertEqual(
                    VALIDATOR.validate_identifier(IdentifierType.CEDULA, number).value,
                    "V-12345678",
                )
        self.assertEqual(
            VALIDATOR.validate_identifier(IdentifierType.CEDULA, "E-81.234.567").value,
            "E-81234567",
        )

    def test_rejects_malformed_cedulas(self):
        for number in (
            "12345678",
            "J-12345678",
            "V-12345",
            "V-123456789",
            "V-12a45678",
            "",
        ):
            with self.subTest(number=number):
                self.assertIn(
                    "V o E",
                    VALIDATOR.validate_identifier(IdentifierType.CEDULA, number).value,
                )

    def test_validates_passports(self):
        self.assertEqual(
            VALIDATOR.validate_identifier(IdentifierType.PASSPORT, "123456789").value,
            "123456789",
        )
        self.assertIn(
            "entre 6 y 12",
            VALIDATOR.validate_identifier(IdentifierType.PASSPORT, "12345").value,
        )

    def test_rejects_types_from_other_countries(self):
        self.assertIn(
            "no corresponde", VALIDATOR.validate_identifier("rut", "12345678-5").value
        )
