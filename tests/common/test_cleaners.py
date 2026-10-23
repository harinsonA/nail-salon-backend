from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.common.utils.passwords import PasswordPolicyValidator
from apps.common.utils.utils import CommonCleaner

User = get_user_model()


class UsernameRuleTests(SimpleTestCase):
    def assert_valid(self, value, expected=None):
        result = CommonCleaner.clean_username_field(value)
        self.assertTrue(result.is_ok(), result.value)
        self.assertEqual(result.value, expected or value)

    def assert_invalid(self, value, message):
        result = CommonCleaner.clean_username_field(value)
        self.assertTrue(result.is_err())
        self.assertIn(message, result.value)

    def test_accepts_lowercase_letters_digits_and_separators(self):
        for value in ("admin_panel", "ana.rojas", "a-b", "soporte2"):
            with self.subTest(value=value):
                self.assert_valid(value)

    def test_trims_surrounding_spaces(self):
        self.assert_valid("  ana  ", "ana")

    def test_rejects_uppercase(self):
        self.assert_invalid("Admin", "minúsculas")

    def test_rejects_wrong_length(self):
        self.assert_invalid("ab", "entre 3 y 30")
        self.assert_invalid("a" * 31, "entre 3 y 30")

    def test_rejects_other_characters_or_a_leading_non_letter(self):
        for value in ("1ana", "_ana", "josé", "ana rojas", "ana@hiagenda"):
            with self.subTest(value=value):
                self.assert_invalid(value, "debe empezar con una letra")


class PasswordRuleTests(SimpleTestCase):
    def check(self, value, user=None):
        return CommonCleaner.clean_password_field(value, user=user)

    def test_accepts_a_password_that_meets_the_policy(self):
        for value in ("Clave#123", "Hi.Agenda2026", "x9Y8z7!w"):
            with self.subTest(value=value):
                self.assertTrue(self.check(value).is_ok())

    def test_length_between_8_and_20(self):
        self.assertIn("entre 8 y 20", self.check("Ab#1234").value)
        self.assertIn("entre 8 y 20", self.check("Abcdefgh#123456789012").value)

    def test_requires_one_uppercase(self):
        self.assertEqual(self.check("clave#123").value, "La contraseña debe incluir al menos 1 mayúscula.")

    def test_requires_three_digits(self):
        self.assertEqual(self.check("Clave#12x").value, "La contraseña debe incluir al menos 3 números.")

    def test_requires_one_special_character(self):
        self.assertEqual(self.check("Clave1234").value, "La contraseña debe incluir al menos 1 carácter especial.")

    def test_lists_every_missing_requirement(self):
        self.assertEqual(
            self.check("clavesegura").value,
            "La contraseña debe incluir al menos 1 mayúscula, 3 números y 1 carácter especial.",
        )

    def test_rejects_a_password_similar_to_the_user(self):
        user = User(username="carolina", email="carolina@hiagenda.test", first_name="Carolina")
        self.assertTrue(self.check("Carolina#123", user=user).is_err())


class PasswordPolicyValidatorTests(SimpleTestCase):
    def test_works_as_a_django_password_validator(self):
        validator = PasswordPolicyValidator()
        validator.validate("Clave#123")
        with self.assertRaises(ValidationError):
            validator.validate("clave")
        self.assertIn("3 números", validator.get_help_text())

    def test_common_cleaner_inherits_the_policy(self):
        self.assertTrue(issubclass(CommonCleaner, PasswordPolicyValidator))
        self.assertEqual(CommonCleaner().get_help_text(), PasswordPolicyValidator().get_help_text())


class AmountRuleTests(SimpleTestCase):
    def test_empty_counts_as_zero(self):
        for monto in (None, ""):
            with self.subTest(monto=monto):
                self.assertEqual(CommonCleaner.clean_amount_field("precio", monto).ok_value, Decimal("0"))

    def test_accepts_zero_and_positive_amounts(self):
        for monto, esperado in ((0, "0"), ("0", "0"), (Decimal("15000.50"), "15000.50"), ("15 000", "15000"), (3000, "3000")):
            with self.subTest(monto=monto):
                self.assertEqual(CommonCleaner.clean_amount_field("precio", monto).ok_value, Decimal(esperado))

    def test_rejects_negative_amounts(self):
        for monto in (-1, "-500", Decimal("-0.01")):
            with self.subTest(monto=monto):
                self.assertEqual(
                    CommonCleaner.clean_amount_field("precio", monto).err_value,
                    "El campo 'precio' no puede ser negativo.",
                )

    def test_rejects_values_that_are_not_numbers(self):
        for monto in ("abc", "NaN", "Infinity"):
            with self.subTest(monto=monto):
                self.assertIn("debe ser un número válido", CommonCleaner.clean_amount_field("precio", monto).err_value)
