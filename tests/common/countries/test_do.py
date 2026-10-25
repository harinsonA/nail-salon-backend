from django.test import SimpleTestCase

from apps.common.utils.countries.do.constants import IdentifierType
from apps.common.utils.countries.do.validator import DominicanRepublicValidator

VALIDATOR = DominicanRepublicValidator()


def validate_cedula(number):
    return VALIDATOR.validate_identifier(IdentifierType.CEDULA, number)


class DominicanRepublicPhoneTests(SimpleTestCase):
    def test_accepts_every_area_code(self):
        for area_code in ("809", "829", "849"):
            with self.subTest(area_code=area_code):
                self.assertEqual(
                    VALIDATOR.validate_phone(f"{area_code}-123-4567").value,
                    f"+1-809{area_code}1234567",
                )

    def test_rejects_unknown_area_codes(self):
        self.assertIn("prefijo", VALIDATOR.validate_phone("8191234567").value)


class DominicanRepublicIdentifierTests(SimpleTestCase):
    def test_accepts_valid_cedulas_and_formats_them(self):
        for number in ("001-0000001-7", "00100000017", "402-0000000-4"):
            with self.subTest(number=number):
                result = validate_cedula(number).value
                self.assertRegex(result, r"^\d{3}-\d{7}-\d$")
                self.assertEqual(result.replace("-", ""), number.replace("-", ""))

    def test_rejects_wrong_length(self):
        for number in ("001-000001-7", "0010000001700", ""):
            with self.subTest(number=number):
                self.assertIn("11 dígitos", validate_cedula(number).value)

    def test_rejects_a_wrong_check_digit(self):
        self.assertIn("verificador", validate_cedula("001-0000001-8").value)
