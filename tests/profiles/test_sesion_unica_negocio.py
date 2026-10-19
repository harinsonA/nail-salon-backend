from django.contrib.auth import get_user_model
from django.test import Client, override_settings
from django.urls import reverse

from apps.profiles.models import Perfil
from apps.seguridad.sessions import CLOSED_ELSEWHERE_MESSAGE
from tests.base import NegocioTestCase

User = get_user_model()

CLAVE = "Clave-Segura-123"
NUEVA = "Otra-Clave-Segura-456"


class SesionUnicaEnElNegocioTests(NegocioTestCase):
    esquema = "sesion_negocio"
    dominio = "sesion-negocio.localhost"

    def setUp(self):
        super().setUp()
        self.laura = User.objects.create_user(username="laura", email="laura@correo.cl", password=CLAVE)
        Perfil.objects.filter(user=self.laura).update(debe_cambiar_clave=False)

    def entrar(self):
        navegador = Client(HTTP_HOST=self.dominio)
        respuesta = navegador.post(reverse("login"), {"username": "laura@correo.cl", "password": CLAVE})
        self.assertRedirects(respuesta, reverse("calendar"), fetch_redirect_response=False)
        return navegador

    def test_entrar_en_otro_dispositivo_cierra_la_sesion_anterior(self):
        computador = self.entrar()
        telefono = self.entrar()
        respuesta = computador.get(reverse("calendar"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta["Location"].startswith(reverse("login")))
        self.assertNotIn("_auth_user_id", computador.session)
        self.assertEqual(telefono.get(reverse("calendar")).status_code, 200)

    def test_el_login_del_negocio_dice_por_que_se_cerro_y_solo_una_vez(self):
        computador = self.entrar()
        self.entrar()
        computador.get(reverse("calendar"))
        self.assertContains(computador.get(reverse("login")), CLOSED_ELSEWHERE_MESSAGE)
        self.assertNotContains(computador.get(reverse("login")), CLOSED_ELSEWHERE_MESSAGE)

    def test_el_aviso_gana_al_de_sesion_expirada(self):
        computador = self.entrar()
        self.entrar()
        computador.get(reverse("calendar"))
        respuesta = computador.get(reverse("login"), {"expired": 1})
        self.assertContains(respuesta, CLOSED_ELSEWHERE_MESSAGE)
        self.assertNotContains(respuesta, "Tu sesión expiró")

    def test_el_ping_de_sesion_recibe_el_motivo(self):
        computador = self.entrar()
        self.entrar()
        respuesta = computador.post(reverse("session_ping"), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(respuesta.status_code, 401)
        self.assertEqual(respuesta.json()["message"], CLOSED_ELSEWHERE_MESSAGE)

    def test_cambiar_la_clave_temporal_no_cierra_la_sesion(self):
        Perfil.objects.filter(user=self.laura).update(debe_cambiar_clave=True)
        navegador = self.entrar()
        respuesta = navegador.post(reverse("cambiar_clave"), {"new_password1": NUEVA, "new_password2": NUEVA})
        self.assertRedirects(respuesta, reverse("calendar"), fetch_redirect_response=False)
        self.assertEqual(navegador.get(reverse("calendar")).status_code, 200)

    @override_settings(SECURITY_SINGLE_SESSION=False)
    def test_el_interruptor_apagado_permite_varias_sesiones(self):
        computador = self.entrar()
        self.entrar()
        self.assertEqual(computador.get(reverse("calendar")).status_code, 200)
