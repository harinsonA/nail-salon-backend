from datetime import timedelta

from django.contrib.auth import authenticate, get_user_model
from django.db import connection
from django.test import Client, TestCase
from django.utils import timezone
from django_tenants.utils import get_public_schema_name

from apps.seguridad.access import LockState, lock_status
from apps.seguridad.models import AccesoUsuario
from apps.tenancy.models import Dominio, Negocio

User = get_user_model()

PANEL = "admin.localhost"
RUTA = "/admin/login/"
CLAVE = "clave-larga"
INCORRECTA = "clave-mala"


class BloqueoEnElLoginDelPanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=publico, is_primary=True)
        cls.admin = User.objects.create_superuser(username="admin", email="admin@correo.cl", password=CLAVE)

    def setUp(self):
        connection.set_schema_to_public()
        self.panel = Client(HTTP_HOST=PANEL)

    def entrar(self, clave=CLAVE, usuario="admin"):
        return self.panel.post(RUTA, {"username": usuario, "password": clave, "next": "/admin/"})

    def fallar(self, veces):
        respuesta = None
        for _ in range(veces):
            respuesta = self.entrar(INCORRECTA)
        return respuesta

    def acceso(self):
        return AccesoUsuario.objects.get(user=self.admin)

    def test_los_primeros_fallos_dan_el_mensaje_de_siempre(self):
        respuesta = self.fallar(3)
        self.assertContains(respuesta, "Usuario o contraseña incorrectos.")
        self.assertNotContains(respuesta, "Te queda 1 intento")
        self.assertEqual(self.acceso().intentos_fallidos, 3)

    def test_el_cuarto_fallo_avisa_que_queda_un_intento(self):
        respuesta = self.fallar(4)
        self.assertContains(respuesta, "Te queda 1 intento antes de que la cuenta se bloquee por un rato.")

    def test_el_quinto_fallo_bloquea_y_dice_hasta_que_hora(self):
        respuesta = self.fallar(5)
        hora = timezone.localtime(self.acceso().bloqueado_hasta).strftime("%H:%M")
        self.assertContains(respuesta, f"Esta cuenta quedó bloqueada por intentos fallidos. Podrás volver a intentarlo a las {hora}.")
        self.assertContains(respuesta, "pide a otro administrador del panel que la desbloquee")

    def test_bloqueado_no_entra_ni_con_la_clave_correcta(self):
        self.fallar(5)
        respuesta = self.entrar()
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Esta cuenta quedó bloqueada")
        self.assertNotIn("_auth_user_id", self.panel.session)
        self.assertEqual(self.acceso().intentos_fallidos, 5)

    def test_al_vencer_el_bloqueo_entra_y_el_conteo_vuelve_a_cero(self):
        self.fallar(5)
        AccesoUsuario.objects.filter(user=self.admin).update(bloqueado_hasta=timezone.now() - timedelta(seconds=1))
        self.assertRedirects(self.entrar(), "/admin/", fetch_redirect_response=False)
        acceso = self.acceso()
        self.assertEqual(acceso.intentos_fallidos, 0)
        self.assertIsNone(acceso.bloqueado_hasta)

    def test_despues_del_temporal_avisa_antes_del_definitivo(self):
        self.fallar(5)
        AccesoUsuario.objects.filter(user=self.admin).update(bloqueado_hasta=timezone.now() - timedelta(seconds=1))
        respuesta = self.fallar(4)
        self.assertContains(respuesta, "Te queda 1 intento antes de que la cuenta se bloquee hasta que alguien la desbloquee.")
        respuesta = self.fallar(1)
        self.assertContains(
            respuesta,
            "Esta cuenta está bloqueada por intentos fallidos. Para volver a entrar, pide a otro administrador del panel que la desbloquee.",
        )
        self.assertEqual(lock_status(self.admin).state, LockState.PERMANENT)

    def test_entrar_bien_reinicia_el_conteo(self):
        self.fallar(3)
        self.assertRedirects(self.entrar(), "/admin/", fetch_redirect_response=False)
        self.assertEqual(self.acceso().intentos_fallidos, 0)

    def test_un_usuario_que_no_existe_no_crea_filas(self):
        respuesta = self.entrar(INCORRECTA, usuario="nadie")
        self.assertContains(respuesta, "Usuario o contraseña incorrectos.")
        self.assertFalse(AccesoUsuario.objects.exists())

    def test_la_clave_correcta_sin_acceso_al_panel_no_cuenta_como_fallo(self):
        sin_panel = User.objects.create_user(username="sin_panel", password=CLAVE)
        respuesta = self.entrar(usuario="sin_panel")
        self.assertContains(respuesta, "Usuario o contraseña incorrectos.")
        self.assertFalse(AccesoUsuario.objects.filter(user=sin_panel).exists())

    def test_authenticate_sin_peticion_tambien_cuenta(self):
        for _ in range(5):
            self.assertIsNone(authenticate(None, username="admin", password=INCORRECTA))
        self.assertIsNone(authenticate(None, username="admin", password=CLAVE))
        self.assertEqual(lock_status(self.admin).state, LockState.TEMPORARY)
