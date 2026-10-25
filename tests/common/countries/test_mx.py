from django.test import SimpleTestCase

from apps.common.utils.countries.mx.constants import IdentifierType
from apps.common.utils.countries.mx.validator import MexicoValidator

VALIDATOR = MexicoValidator()


def validate_curp(number):
    return VALIDATOR.validate_identifier(IdentifierType.CURP, number)


class MexicoPhoneTests(SimpleTestCase):
    def test_accepts_ten_digit_numbers_without_operator_prefix(self):
        self.assertEqual(
            VALIDATOR.validate_phone("55 1234 5678").value, "+525512345678"
        )

    def test_rejects_wrong_length(self):
        self.assertIn("10 dígitos", VALIDATOR.validate_phone("551234567").value)


class MexicoIdentifierTests(SimpleTestCase):
    def test_accepts_valid_curps_in_any_case(self):
        for number in ("BOXW310820HNERXN09", " boxw310820hnerxn09 "):
            with self.subTest(number=number):
                self.assertEqual(validate_curp(number).value, "BOXW310820HNERXN09")

    def test_rejects_curps_out_of_the_official_format(self):
        for number in (
            "BOXW310820HNERXN0",
            "B0XW310820HNERXN09",
            "BOXW310820ZNERXN09",
            "",
        ):
            with self.subTest(number=number):
                self.assertIn("formato oficial", validate_curp(number).value)

    def test_rejects_a_wrong_check_digit(self):
        self.assertIn("verificador", validate_curp("BOXW310820HNERXN08").value)
