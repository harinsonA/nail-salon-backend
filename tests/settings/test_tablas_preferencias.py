from django.db import connection
from django.test import TestCase

from tests.base import NegocioTestCase

TABLAS = {"preference", "settings_historicalpreference", "configuracion_negocio"}


def tablas_del_esquema():
    with connection.cursor() as cursor:
        return set(connection.introspection.table_names(cursor))


class TablasPreferenciasEnPublicTests(TestCase):
    def test_existen_en_public(self):
        self.assertEqual(connection.schema_name, "public")
        self.assertTrue(TABLAS <= tablas_del_esquema())


class TablasPreferenciasEnNegocioTests(NegocioTestCase):
    esquema = "tablas_preferencias"

    def test_existen_en_el_negocio(self):
        self.assertTrue(TABLAS <= tablas_del_esquema())
