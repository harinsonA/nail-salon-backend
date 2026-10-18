from django import forms
from django.test import SimpleTestCase

from apps.common.form_fields import SchemaField, SubdomainField
from apps.common.utils.utils import CommonCleaner


class SubdomainRuleTests(SimpleTestCase):
    def test_accepts_valid_subdomains(self):
        for subdominio in ("maria", "el-corte", "barberia-del-centro", "abc"):
            with self.subTest(subdominio=subdominio):
                self.assertEqual(CommonCleaner.clean_subdomain_field(subdominio).value, subdominio)

    def test_rejects_characters_outside_the_whitelist(self):
        for subdominio in ("María", "mi_barberia", "-corte", "corte-", "mi--barberia", "2salon", "salon2", "barberia-2", "el corte", "uñas"):
            with self.subTest(subdominio=subdominio):
                self.assertIn("solo admite", CommonCleaner.clean_subdomain_field(subdominio).value)

    def test_rejects_lengths_out_of_range(self):
        for subdominio in ("ab", "a" * 41):
            with self.subTest(subdominio=subdominio):
                self.assertIn("entre 3 y 40", CommonCleaner.clean_subdomain_field(subdominio).value)

    def test_rejects_reserved_subdomains(self):
        for subdominio in ("admin", "www", "api", "public", "pg-datos"):
            with self.subTest(subdominio=subdominio):
                self.assertEqual(CommonCleaner.clean_subdomain_field(subdominio).value, f"«{subdominio}» está reservado.")


class SchemaRuleTests(SimpleTestCase):
    def test_accepts_valid_schemas(self):
        for esquema in ("mi_barberia", "corte_central", "abc"):
            with self.subTest(esquema=esquema):
                self.assertTrue(CommonCleaner.clean_schema_field(esquema).is_ok())

    def test_rejects_invalid_or_reserved_schemas(self):
        casos = {
            "mi-barberia": "solo admite",
            "Mayus": "solo admite",
            "mi__barberia": "solo admite",
            "_corte": "solo admite",
            "salon2": "solo admite",
            "corte_2": "solo admite",
            "ab": "entre 3 y 40",
            "pg_datos": "reservado",
            "admin": "reservado",
            "public": "reservado",
        }
        for esquema, mensaje in casos.items():
            with self.subTest(esquema=esquema):
                resultado = CommonCleaner.clean_schema_field(esquema)
                self.assertTrue(resultado.is_err())
                self.assertIn(mensaje, resultado.value)


class TimeZoneRuleTests(SimpleTestCase):
    def test_accepts_known_time_zones_and_rejects_the_rest(self):
        self.assertTrue(CommonCleaner.clean_time_zone_field("America/Santiago").is_ok())
        self.assertEqual(
            CommonCleaner.clean_time_zone_field("Marte/Olympus").value,
            "«Marte/Olympus» no es una zona horaria válida.",
        )


class BusinessFieldTests(SimpleTestCase):
    def test_fields_lowercase_and_validate_with_the_cleaner(self):
        class SampleForm(forms.Form):
            subdominio = SubdomainField(label="Subdominio")
            esquema = SchemaField(label="Esquema")

        valid = SampleForm(data={"subdominio": " El-Corte ", "esquema": "El_Corte"})
        self.assertTrue(valid.is_valid(), valid.errors)
        self.assertEqual(valid.cleaned_data, {"subdominio": "el-corte", "esquema": "el_corte"})
        invalid = SampleForm(data={"subdominio": "admin", "esquema": "el-corte"})
        self.assertFalse(invalid.is_valid())
        self.assertEqual(invalid.errors["subdominio"], ["«admin» está reservado."])
        self.assertIn("guion bajo", invalid.errors["esquema"][0])
