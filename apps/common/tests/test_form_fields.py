from django import forms
from django.test import SimpleTestCase

from apps.common.form_fields import (
    AlphabeticField,
    AlphanumericField,
    NoteField,
    NumericField,
)
from apps.common.utils.text import join_name_parts, split_name
from apps.common.utils.utils import CommonCleaner


class SampleForm(forms.Form):
    name = AlphabeticField(label="Nombre", max_length=50, required=False)
    street = AlphabeticField(label="Calle", required=False, allow_dots=True)
    complement = AlphanumericField(label="Depto", required=False, allow_dots=True)
    reference = AlphanumericField(label="Referencia", required=False)
    number = NumericField(label="Número", required=False)
    note = NoteField(label="Nota", required=False)


class FormFieldTests(SimpleTestCase):
    def clean(self, **data):
        form = SampleForm(data=data)
        form.is_valid()
        return form

    def assert_accepts(self, field, value, expected):
        form = self.clean(**{field: value})
        self.assertNotIn(field, form.errors)
        self.assertEqual(form.cleaned_data[field], expected)

    def assert_rejects(self, field, value, message):
        self.assertIn(message, self.clean(**{field: value}).errors[field][0])

    def test_alphabetic_field_collapses_spaces_and_accepts_accents(self):
        self.assert_accepts("name", "  José   Ñandú ", "José Ñandú")

    def test_alphabetic_field_rejects_digits_and_symbols(self):
        for value in ("Ana2", "Ana.", "Ana-María", "Ana_María", "Ana@"):
            with self.subTest(value=value):
                self.assert_rejects(
                    "name",
                    value,
                    "El campo 'nombre' debe solo contener caracteres alfabéticos y espacios.",
                )

    def test_alphabetic_field_can_allow_dots(self):
        self.assert_accepts("street", "Av. Providencia", "Av. Providencia")
        self.assert_rejects(
            "street", "Calle 5", "caracteres alfabéticos, espacios y puntos"
        )

    def test_alphanumeric_field(self):
        self.assert_accepts(
            "reference", "Portón verde al lado del 47", "Portón verde al lado del 47"
        )
        self.assert_rejects("reference", "Frente al 50%", "letras, números y espacios")
        self.assert_rejects(
            "reference", "Frente a la pza.", "letras, números y espacios"
        )
        self.assert_accepts("complement", "Depto. 502", "Depto. 502")
        self.assert_rejects(
            "complement", "Local #3", "letras, números, espacios y puntos"
        )

    def test_numeric_field_only_takes_ascii_digits(self):
        self.assert_accepts("number", "1234", "1234")
        for value in ("12A", "12 34", "12-34", "+56", "²"):
            with self.subTest(value=value):
                self.assert_rejects(
                    "number", value, "El campo 'número' debe solo contener números."
                )

    def test_note_field_keeps_line_breaks_and_limits_length(self):
        self.assert_accepts("note", " Línea uno\nLínea dos ", "Línea uno\nLínea dos")
        self.assertIn("250", self.clean(note="x" * 251).errors["note"][0])

    def test_empty_values_are_allowed_when_optional(self):
        form = self.clean()
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data["name"], "")

    def test_required_still_applies(self):
        field = AlphabeticField(label="Primer nombre")
        with self.assertRaises(forms.ValidationError):
            field.clean("   ")


class CleanerOptionsTests(SimpleTestCase):
    def test_dots_are_off_by_default(self):
        self.assertTrue(
            CommonCleaner.clean_alphabetic_field("calle", "Av. Uno").is_err()
        )
        self.assertTrue(
            CommonCleaner.clean_alphanumeric_field("depto", "Depto. 5").is_err()
        )
        self.assertTrue(
            CommonCleaner.clean_alphabetic_field(
                "calle", "Av. Uno", allow_dots=True
            ).is_ok()
        )
        self.assertTrue(
            CommonCleaner.clean_alphanumeric_field(
                "depto", "Depto. 5", allow_dots=True
            ).is_ok()
        )


class NameHelpersTests(SimpleTestCase):
    def test_join_and_split_names(self):
        self.assertEqual(join_name_parts("Ana", "", "María"), "Ana María")
        self.assertEqual(split_name("Ana María José"), ("Ana", "María José"))
        self.assertEqual(split_name(None), ("", ""))
