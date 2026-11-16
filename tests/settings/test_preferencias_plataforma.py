from io import StringIO

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, override_settings
from django_tenants.utils import schema_context

from apps.settings.models import Preference
from apps.settings.preferences import (
    APP_LATEST_VERSION,
    APP_MAINTENANCE,
    APP_MAINTENANCE_MESSAGE,
    APP_MINIMUM_VERSION,
    APP_MODULE,
    PREFERENCES,
    RESERVATION_AMOUNT,
    Category,
    Scope,
    get_preferences,
)
from tests.base import NegocioTestCase

User = get_user_model()

PLATAFORMA = (APP_MINIMUM_VERSION, APP_LATEST_VERSION, APP_MAINTENANCE, APP_MAINTENANCE_MESSAGE)


class PreferenciasPlataformaTests(NegocioTestCase):
    esquema = "preferencias_plataforma"

    def test_estan_en_el_registro_con_alcance_plataforma_y_categoria_de_la_app(self):
        for definicion in PLATAFORMA:
            with self.subTest(definicion=definicion.key):
                self.assertIn(definicion.key, PREFERENCES)
                self.assertEqual(definicion.scope, Scope.PLATAFORMA)
                self.assertEqual(definicion.category, Category.APP_MOVIL)

    def test_sin_configurar_valen_vacio_y_apagado(self):
        for esquema in ("public", self.esquema):
            with self.subTest(esquema=esquema), schema_context(esquema):
                self.assertEqual(APP_MINIMUM_VERSION.get(), "")
                self.assertEqual(APP_LATEST_VERSION.get(), "")
                self.assertIs(APP_MAINTENANCE.get(), False)
                self.assertEqual(APP_MAINTENANCE_MESSAGE.get(), "")

    def test_lo_guardado_en_public_se_lee_igual_desde_el_negocio(self):
        with schema_context("public"):
            APP_MINIMUM_VERSION.set("1.4.0")
            APP_MAINTENANCE.set(True)
        self.assertEqual(connection.schema_name, self.esquema)
        self.assertEqual(APP_MINIMUM_VERSION.get(), "1.4.0")
        self.assertIs(APP_MAINTENANCE.is_enabled(), True)

    def test_lo_guardado_desde_el_negocio_queda_en_public(self):
        APP_LATEST_VERSION.set("2.0.1")
        self.assertEqual(connection.schema_name, self.esquema)
        self.assertFalse(Preference.objects.filter(key=APP_LATEST_VERSION.key).exists())
        with schema_context("public"):
            fila = Preference.objects.get(key=APP_LATEST_VERSION.key)
            self.assertEqual(fila.scope, Scope.PLATAFORMA)
            self.assertEqual(fila.scope_id, "")
            self.assertEqual(APP_LATEST_VERSION.get(), "2.0.1")

    def test_escribir_dos_veces_actualiza_la_misma_fila_y_deja_historial_sin_usuario(self):
        APP_MAINTENANCE_MESSAGE.set("Volvemos pronto")
        APP_MAINTENANCE_MESSAGE.set("Volvemos a las 10:00")
        with schema_context("public"):
            fila = Preference.objects.get(key=APP_MAINTENANCE_MESSAGE.key)
            self.assertEqual(fila.value, "Volvemos a las 10:00")
            self.assertEqual(fila.history.count(), 2)
            self.assertFalse(fila.history.exclude(history_user=None).exists())

    def test_se_leen_junto_a_las_del_negocio(self):
        APP_MINIMUM_VERSION.set("1.0.0")
        RESERVATION_AMOUNT.set(5000)
        valores = get_preferences([APP_MINIMUM_VERSION, RESERVATION_AMOUNT, APP_MAINTENANCE])
        self.assertEqual(
            valores,
            {"app_version_minima": "1.0.0", "valor_reserva": 5000, "app_mantenimiento": False},
        )

    def test_las_versiones_exigen_la_forma_numerica(self):
        for valor in ("1.4", "v1.4.0", "1.4.0-beta", "uno"):
            with self.subTest(valor=valor), self.assertRaises(ValidationError):
                APP_MINIMUM_VERSION.set(valor)
        self.assertEqual(APP_MINIMUM_VERSION.set(" 10.20.30 "), "10.20.30")
        self.assertEqual(APP_LATEST_VERSION.set(""), "")


class AppModuleTests(NegocioTestCase):
    esquema = "app_module"

    def test_es_del_negocio_y_esta_apagada_por_defecto(self):
        self.assertEqual(APP_MODULE.scope, Scope.NEGOCIO)
        self.assertEqual(APP_MODULE.category, Category.FUNCIONES_NUEVAS)
        self.assertIs(APP_MODULE.is_enabled(), False)

    def test_se_enciende_solo_en_su_negocio(self):
        APP_MODULE.set(True)
        self.assertIs(APP_MODULE.is_enabled(), True)
        self.assertTrue(Preference.objects.filter(key="app_module", scope=Scope.NEGOCIO).exists())
        with schema_context("public"):
            self.assertIs(APP_MODULE.is_enabled(), False)
            self.assertFalse(Preference.objects.filter(key="app_module").exists())

    @override_settings(DEBUG=True)
    def test_el_comando_la_enciende_y_la_apaga(self):
        salida = StringIO()
        call_command("encender_app_movil", "app-module", stdout=salida)
        self.assertIn("encendida", salida.getvalue())
        connection.set_tenant(self.negocio)
        self.assertIs(APP_MODULE.is_enabled(), True)

        call_command("encender_app_movil", "app_module", "--apagar", stdout=StringIO())
        connection.set_tenant(self.negocio)
        self.assertIs(APP_MODULE.is_enabled(), False)

    @override_settings(DEBUG=True)
    def test_el_comando_avisa_si_el_negocio_no_existe(self):
        with self.assertRaises(CommandError):
            call_command("encender_app_movil", "no-existe", stdout=StringIO())


class EncenderAppMovilSoloEnDesarrolloTests(SimpleTestCase):
    def test_exige_debug(self):
        with self.assertRaises(CommandError):
            call_command("encender_app_movil", "demo", stdout=StringIO())
