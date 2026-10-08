from datetime import date

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, SimpleTestCase, TestCase
from django.urls import URLPattern, URLResolver, get_resolver, reverse
from django_tenants.utils import get_public_schema_name

from apps.profiles.models import Perfil
from apps.profiles.permisos import PARA_TODO_EL_EQUIPO, SOLO_ADMINISTRACION
from apps.tenancy.models import Dominio, Negocio
from apps.tenancy.testing import NegocioTestCase

User = get_user_model()

VALORES_DE_PRUEBA = {"int": 1, "str": date.today().isoformat()}


def rutas_con_nombre(patrones=None):
    for patron in patrones if patrones is not None else get_resolver().url_patterns:
        if isinstance(patron, URLResolver):
            yield from rutas_con_nombre(patron.url_patterns)
        elif isinstance(patron, URLPattern) and patron.name:
            yield patron


def url_de_prueba(patron):
    convertidores = getattr(patron.pattern, "converters", {})
    argumentos = {
        nombre: VALORES_DE_PRUEBA["int" if type(conv).__name__ == "IntConverter" else "str"]
        for nombre, conv in convertidores.items()
    }
    return reverse(patron.name, kwargs=argumentos)


class ClasificacionDeRutasTests(SimpleTestCase):
    def test_cada_ruta_de_la_agenda_tiene_un_permiso_asignado(self):
        nombres = {patron.name for patron in rutas_con_nombre()}
        self.assertEqual(nombres - SOLO_ADMINISTRACION - PARA_TODO_EL_EQUIPO, set(), "rutas sin clasificar")
        self.assertEqual((SOLO_ADMINISTRACION | PARA_TODO_EL_EQUIPO) - nombres, set(), "rutas que ya no existen")
        self.assertEqual(SOLO_ADMINISTRACION & PARA_TODO_EL_EQUIPO, set())


class PermisosPorRolTests(NegocioTestCase):
    esquema = "permisos"
    dominio = "permisos.localhost"

    def navegador_de(self, rol, raise_request_exception=True):
        usuario = User.objects.create_user(username=rol, email=f"{rol}@correo.cl")
        Perfil.objects.filter(user=usuario).update(rol=rol, debe_cambiar_clave=False)
        navegador = Client(HTTP_HOST=self.dominio, raise_request_exception=raise_request_exception)
        navegador.force_login(usuario)
        return navegador

    def rutas_de(self, nombres):
        return [patron for patron in rutas_con_nombre() if patron.name in nombres]

    def test_el_colaborador_no_entra_a_la_administracion(self):
        navegador = self.navegador_de(Perfil.Rol.COLABORADOR)
        for patron in self.rutas_de(SOLO_ADMINISTRACION):
            with self.subTest(ruta=patron.name):
                self.assertEqual(navegador.get(url_de_prueba(patron)).status_code, 403)

    def test_el_colaborador_recibe_json_en_ajax(self):
        navegador = self.navegador_de(Perfil.Rol.COLABORADOR)
        respuesta = navegador.get(reverse("incomes_list"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(respuesta.status_code, 403)
        self.assertIn("propietario", respuesta.json()["message"])

    def test_encargado_y_propietario_entran_a_la_administracion(self):
        for rol in (Perfil.Rol.ENCARGADO, Perfil.Rol.PROPIETARIO):
            navegador = self.navegador_de(rol, raise_request_exception=False)
            for patron in self.rutas_de(SOLO_ADMINISTRACION):
                with self.subTest(rol=rol, ruta=patron.name):
                    self.assertNotEqual(navegador.get(url_de_prueba(patron)).status_code, 403)

    def test_el_colaborador_trabaja_la_agenda_y_los_clientes(self):
        navegador = self.navegador_de(Perfil.Rol.COLABORADOR)
        for nombre in ("calendar", "clients", "tasks", "client_import", "client_export", "client_example_export"):
            with self.subTest(ruta=nombre):
                self.assertEqual(navegador.get(reverse(nombre)).status_code, 200)

    def test_el_menu_muestra_solo_lo_permitido(self):
        colaborador = self.navegador_de(Perfil.Rol.COLABORADOR).get(reverse("clients"))
        encargado = self.navegador_de(Perfil.Rol.ENCARGADO).get(reverse("clients"))
        for ruta in ("dashboard", "services", "incomes"):
            with self.subTest(ruta=ruta):
                self.assertNotContains(colaborador, f'href="{reverse(ruta)}"')
                self.assertContains(encargado, f'href="{reverse(ruta)}"')
        for respuesta in (colaborador, encargado):
            self.assertContains(respuesta, f'href="{reverse("client_import")}"')
            self.assertContains(respuesta, reverse("client_export"))

    def test_dentro_de_un_negocio_nadie_es_superusuario(self):
        usuario = User.objects.create_superuser(username="jefe", email="jefe@correo.cl", password="x")
        usuario.refresh_from_db()
        self.assertFalse(usuario.is_superuser)
        self.assertFalse(usuario.is_staff)


class PanelDeLaPlataformaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain="admin.localhost", tenant=publico, is_primary=True)

    def test_tu_panel_sigue_con_superusuario_y_sin_perfiles(self):
        connection.set_schema_to_public()
        admin = User.objects.create_superuser(username="admin", email="admin@correo.cl", password="x")
        admin.refresh_from_db()
        self.assertTrue(admin.is_superuser)
        navegador = Client(HTTP_HOST="admin.localhost")
        navegador.force_login(admin)
        self.assertEqual(navegador.get("/admin/").status_code, 200)
