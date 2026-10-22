from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.clients.models import Cliente
from apps.profiles.models import Perfil
from apps.services.models import Categoria, Servicio
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

    def encargada(self):
        user = User.objects.create_user(username="ana", email="ana@correo.cl", password="x")
        Perfil.objects.filter(user=user).update(rol=Perfil.Rol.ENCARGADO, debe_cambiar_clave=False)
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(user)
        return navegador

    def ir_a(self, nombre):
        return f'href="{reverse(nombre)}" class="btn btn-sm btn-primary cal2-welcome__go"'

    def servicio(self):
        Servicio.objects.create(nombre="Manicure", precio=Decimal("10000"), categoria=Categoria.objects.create(nombre="Manos"))

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

    def test_sin_clientes_ni_servicios_da_la_bienvenida_con_los_pasos(self):
        respuesta = self.encargada().get(reverse("calendar"))
        self.assertContains(respuesta, 'id="calendar-welcome"')
        self.assertContains(respuesta, self.ir_a("clients"))
        self.assertContains(respuesta, self.ir_a("services"))
        self.assertContains(respuesta, "Agenda tu primera cita")

    def test_la_colaboradora_no_recibe_el_enlace_a_servicios(self):
        respuesta = self.navegador.get(reverse("calendar"))
        self.assertContains(respuesta, self.ir_a("clients"))
        self.assertNotContains(respuesta, self.ir_a("services"))
        self.assertContains(respuesta, "Pídeselos a quien administra el negocio.")

    def test_marca_como_listo_el_paso_que_ya_esta_hecho(self):
        Cliente.objects.create(nombre="Paula", apellido="Herrera")
        respuesta = self.encargada().get(reverse("calendar"))
        self.assertContains(respuesta, "cal2-welcome__step is-done", count=1)
        self.assertNotContains(respuesta, self.ir_a("clients"))

    def test_con_clientes_y_servicios_no_aparece(self):
        Cliente.objects.create(nombre="Paula", apellido="Herrera")
        self.servicio()
        self.assertNotContains(self.encargada().get(reverse("calendar")), 'id="calendar-welcome"')
