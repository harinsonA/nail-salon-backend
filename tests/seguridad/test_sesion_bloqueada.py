from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django_tenants.utils import get_public_schema_name

from apps.profiles.models import Perfil
from apps.seguridad.access import register_failure, unlock
from apps.seguridad.models import AccesoUsuario
from apps.seguridad.sessions import LOCKED_MESSAGE
from apps.tenancy.models import Dominio, Negocio
from tests.base import NegocioTestCase

User = get_user_model()

CLAVE = "Clave-Segura-123"


def bloquear(usuario, definitivo=True):
    for _ in range(5):
        register_failure(usuario)
    if definitivo:
        AccesoUsuario.objects.filter(user=usuario).update(bloqueado_hasta=timezone.now() - timedelta(seconds=1))
        for _ in range(5):
            register_failure(usuario)


class SesionBloqueadaEnElNegocioTests(NegocioTestCase):
    esquema = "sesion_bloqueada"
    dominio = "sesion-bloqueada.localhost"

    def setUp(self):
        super().setUp()
        self.mario = User.objects.create_user(username="mario", email="mario@correo.cl", password=CLAVE)
        Perfil.objects.filter(user=self.mario).update(rol=Perfil.Rol.PROPIETARIO, debe_cambiar_clave=False)

    def entrar(self):
        navegador = Client(HTTP_HOST=self.dominio)
        respuesta = navegador.post(reverse("login"), {"username": "mario@correo.cl", "password": CLAVE})
        self.assertRedirects(respuesta, reverse("calendar"), fetch_redirect_response=False)
        return navegador

    def test_bloquear_la_cuenta_cierra_la_sesion_abierta(self):
        navegador = self.entrar()
        self.assertEqual(navegador.get(reverse("calendar")).status_code, 200)
        bloquear(self.mario)
        respuesta = navegador.get(reverse("calendar"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta["Location"].startswith(reverse("login")))
        self.assertNotIn("_auth_user_id", navegador.session)

    def test_el_login_dice_que_la_cuenta_esta_bloqueada_y_solo_una_vez(self):
        navegador = self.entrar()
        bloquear(self.mario)
        navegador.get(reverse("calendar"))
        self.assertContains(navegador.get(reverse("login")), LOCKED_MESSAGE)
        self.assertNotContains(navegador.get(reverse("login")), LOCKED_MESSAGE)

    def test_un_bloqueo_temporal_dice_hasta_que_hora(self):
        navegador = self.entrar()
        bloquear(self.mario, definitivo=False)
        hasta = timezone.localtime(AccesoUsuario.objects.get(user=self.mario).bloqueado_hasta).strftime("%H:%M")
        navegador.get(reverse("calendar"))
        self.assertContains(navegador.get(reverse("login")), f"bloqueada por intentos fallidos hasta las {hasta}")

    def test_una_peticion_ajax_recibe_el_motivo(self):
        navegador = self.entrar()
        bloquear(self.mario)
        respuesta = navegador.post(reverse("session_ping"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["message"], LOCKED_MESSAGE)

    def test_tras_desbloquear_puede_volver_a_entrar(self):
        navegador = self.entrar()
        bloquear(self.mario)
        navegador.get(reverse("calendar"))
        unlock(self.mario, "Prueba")
        self.assertEqual(self.entrar().get(reverse("calendar")).status_code, 200)

    @override_settings(SECURITY_SINGLE_SESSION=False)
    def test_el_bloqueo_se_revisa_aunque_la_sesion_unica_este_apagada(self):
        navegador = self.entrar()
        bloquear(self.mario)
        self.assertEqual(navegador.get(reverse("calendar")).status_code, 302)


class SesionBloqueadaEnElPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain="admin.localhost", tenant=publico, is_primary=True)
        cls.admin = User.objects.create_superuser(username="admin", email="admin@hiagenda.cl", password=CLAVE)

    def setUp(self):
        connection.set_schema_to_public()

    def entrar(self):
        navegador = Client(HTTP_HOST="admin.localhost")
        respuesta = navegador.post("/admin/login/", {"username": "admin", "password": CLAVE, "next": "/admin/"})
        self.assertRedirects(respuesta, "/admin/", fetch_redirect_response=False)
        return navegador

    def test_bloquear_la_cuenta_cierra_la_sesion_del_panel(self):
        navegador = self.entrar()
        bloquear(self.admin)
        respuesta = navegador.get("/admin/")
        self.assertRedirects(respuesta, "/admin/login/?next=/admin/", fetch_redirect_response=False)
        self.assertContains(navegador.get("/admin/login/"), LOCKED_MESSAGE)

    def test_una_peticion_ajax_del_panel_recibe_el_motivo(self):
        navegador = self.entrar()
        bloquear(self.admin)
        respuesta = navegador.get(
            "/admin/auth/user/list/", {"draw": 1, "start": 0, "length": 10}, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["message"], LOCKED_MESSAGE)
