from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.profiles.models import Perfil
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

    def test_todo_el_equipo_entra_al_calendario_sin_activar_nada(self):
        respuesta = self.navegador.get(reverse("calendar"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "calendar_v2/list.html")

    def test_el_calendario_vive_en_su_direccion_de_siempre(self):
        self.assertEqual(reverse("calendar"), "/calendario/")
        self.assertEqual(reverse("calendar_data"), "/calendario/datos/")
        self.assertEqual(reverse("calendar_preferences"), "/calendario/preferencias/")

    def test_sin_sesion_pide_entrar(self):
        respuesta = Client(HTTP_HOST=self.dominio).get(reverse("calendar"))
        self.assertEqual(respuesta.status_code, 302)
        self.assertNotEqual(respuesta["Location"], reverse("calendar"))

