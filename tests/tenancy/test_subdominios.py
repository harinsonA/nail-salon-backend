from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from apps.tenancy.subdominios import esquema_desde_subdominio, validar_esquema, validar_subdominio


class SubdominiosTests(SimpleTestCase):
    def test_el_esquema_cambia_guiones_por_guiones_bajos(self):
        self.assertEqual(esquema_desde_subdominio("mi-barberia"), "mi_barberia")
        self.assertEqual(esquema_desde_subdominio("salon2"), "salon2")

    def test_acepta_subdominios_validos(self):
        for subdominio in ("maria", "el-corte", "barberia-2", "abc"):
            with self.subTest(subdominio=subdominio):
                validar_subdominio(subdominio)

    def test_rechaza_caracteres_fuera_de_la_lista_blanca(self):
        for subdominio in ("María", "mi_barberia", "-corte", "corte-", "mi--barberia", "2salon", "el corte", "uñas"):
            with self.subTest(subdominio=subdominio), self.assertRaises(ValidationError):
                validar_subdominio(subdominio)

    def test_rechaza_largos_fuera_de_rango(self):
        for subdominio in ("ab", "a" * 41):
            with self.subTest(subdominio=subdominio), self.assertRaises(ValidationError):
                validar_subdominio(subdominio)

    def test_rechaza_subdominios_reservados(self):
        for subdominio in ("admin", "www", "api", "public", "pg-datos"):
            with self.subTest(subdominio=subdominio), self.assertRaises(ValidationError):
                validar_subdominio(subdominio)

    def test_valida_el_nombre_del_esquema(self):
        validar_esquema("mi_barberia")
        for esquema in ("mi-barberia", "pg_datos", "admin", "Mayus"):
            with self.subTest(esquema=esquema), self.assertRaises(ValidationError):
                validar_esquema(esquema)
