from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.profiles.models import Perfil
from apps.settings.models import Preference
from apps.settings.preferences import Scope
from tests.base import NegocioTestCase

User = get_user_model()


class CalendarioV2Tests(NegocioTestCase):
    esquema = "calendario"
    dominio = "calendario.localhost"

    def setUp(self):
        super().setUp()
        self.colaboradora = User.objects.create_user(username="camila", email="camila@correo.cl", password="x")
        Perfil.objects.filter(user=self.colaboradora).update(debe_cambiar_clave=False)
        self.navegador = Client(HTTP_HOST=self.dominio)
        self.navegador.force_login(self.colaboradora)

    def activar(self):
        Preference.objects.create(scope=Scope.NEGOCIO, scope_id="", key="calendario_v2", value=True)

    def test_apagada_el_menu_sigue_en_el_calendario_actual(self):
        respuesta = self.navegador.get(reverse("calendar"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "calendar/list.html")

    def test_apagada_la_v2_devuelve_al_calendario_actual(self):
        respuesta = self.navegador.get(reverse("calendar_v2"))
        self.assertRedirects(respuesta, reverse("calendar"), fetch_redirect_response=False)

    def test_activa_el_menu_lleva_a_la_v2(self):
        self.activar()
        respuesta = self.navegador.get(reverse("calendar"))
        self.assertRedirects(respuesta, reverse("calendar_v2"), fetch_redirect_response=False)

    def test_activa_todo_el_equipo_ve_la_v2(self):
        self.activar()
        respuesta = self.navegador.get(reverse("calendar_v2"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "calendar_v2/list.html")

    def test_sin_sesion_pide_entrar(self):
        self.activar()
        respuesta = Client(HTTP_HOST=self.dominio).get(reverse("calendar_v2"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertNotEqual(respuesta["Location"], reverse("calendar_v2"))
