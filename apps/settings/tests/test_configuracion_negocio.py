from django.db import connection

from apps.settings.models import ConfiguracionNegocio, Preference
from apps.settings.preferences.constants import Scope
from apps.tenancy.testing import NegocioTestCase


class ConfiguracionNegocioTests(NegocioTestCase):
    def columnas(self, tabla):
        with connection.cursor() as cursor:
            return {
                columna.name
                for columna in connection.introspection.get_table_description(cursor, tabla)
            }

    def test_la_tabla_se_renombro_sin_direccion(self):
        columnas = self.columnas("configuracion_negocio")
        self.assertIn("nombre_visible", columnas)
        self.assertNotIn("nombre_salon", columnas)
        self.assertNotIn("direccion", columnas)
        with connection.cursor() as cursor:
            self.assertNotIn("configuracion_salon", connection.introspection.table_names(cursor))

    def test_guarda_lo_que_el_negocio_muestra(self):
        configuracion = ConfiguracionNegocio.objects.create(nombre_visible="Barbería El Corte")
        self.assertEqual(str(configuracion), "Barbería El Corte")

    def test_el_alcance_de_todo_el_negocio_se_llama_negocio(self):
        self.assertEqual(Scope.NEGOCIO, "negocio")
        Preference.objects.create(scope=Scope.NEGOCIO, key="recordatorios", value=True)
        self.assertEqual(Preference.objects.get(key="recordatorios").get_scope_display(), "Negocio")
