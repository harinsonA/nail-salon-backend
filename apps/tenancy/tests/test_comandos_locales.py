from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import SimpleTestCase, TestCase, override_settings
from django_tenants.utils import schema_context

from apps.clients.models import Cliente
from apps.profiles.models import Perfil
from apps.settings.models import Preference
from apps.settings.preferences.constants import Scope
from apps.tenancy.testing import borrar_negocio_de_prueba, crear_negocio_de_prueba

User = get_user_model()


class SoloEnDesarrolloTests(SimpleTestCase):
    def test_los_comandos_locales_exigen_debug(self):
        for comando in ("apartar_tablas_de_negocio", "preparar_negocios_locales", "copiar_datos_demo"):
            with self.subTest(comando=comando), self.assertRaises(CommandError):
                call_command(comando, stdout=StringIO())


@override_settings(DEBUG=True)
class CopiarDatosDemoTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.origen = crear_negocio_de_prueba("origen")
        cls.destino = crear_negocio_de_prueba("destino")
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        borrar_negocio_de_prueba(cls.origen)
        borrar_negocio_de_prueba(cls.destino)

    def setUp(self):
        with schema_context("origen"):
            User.objects.create_superuser(username="harinson", email="h@correo.cl", password="x")
            User.objects.create_user(username="ana", email="a@correo.cl", password="x")
            self.laura = Cliente.objects.create(nombre="Laura")
            Preference.objects.create(scope="salon", key="recordatorios", value=True)
        with schema_context("destino"):
            Cliente.objects.create(nombre="Se borra al copiar")

    def copiar(self):
        call_command("copiar_datos_demo", desde="origen", hacia="destino", stdout=StringIO())
        connection.set_schema_to_public()

    def test_copia_los_datos_con_sus_ids(self):
        self.copiar()
        with schema_context("destino"):
            self.assertEqual(list(Cliente.all_objects.values_list("id", "nombre")), [(self.laura.id, "Laura")])
            self.assertEqual(Cliente.history.count(), 1)
            self.assertGreater(Cliente.objects.create(nombre="Nueva").id, self.laura.id)

    def test_se_puede_repetir(self):
        self.copiar()
        self.copiar()
        with schema_context("destino"):
            self.assertEqual(Cliente.all_objects.count(), 1)
            self.assertEqual(User.objects.count(), 2)

    def test_el_superusuario_queda_como_propietario(self):
        self.copiar()
        with schema_context("destino"):
            self.assertEqual(
                dict(Perfil.objects.values_list("user__username", "rol")),
                {"harinson": Perfil.Rol.PROPIETARIO, "ana": Perfil.Rol.COLABORADOR},
            )
            self.assertFalse(Perfil.objects.filter(debe_cambiar_clave=True).exists())

    def test_el_alcance_salon_pasa_a_negocio(self):
        self.copiar()
        with schema_context("destino"):
            self.assertEqual(Preference.objects.get(key="recordatorios").scope, Scope.NEGOCIO)

    def test_el_origen_no_cambia(self):
        self.copiar()
        with schema_context("origen"):
            self.assertEqual(Cliente.all_objects.count(), 1)
            self.assertFalse(Perfil.objects.exists())

    def test_rechaza_destinos_que_no_son_negocios(self):
        for hacia in ("public", "no_existe"):
            with self.subTest(hacia=hacia), self.assertRaises(CommandError):
                call_command("copiar_datos_demo", desde="origen", hacia=hacia, stdout=StringIO())
