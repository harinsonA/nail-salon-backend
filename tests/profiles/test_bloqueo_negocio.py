from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from django_tenants.utils import schema_context

from apps.profiles.models import Perfil
from apps.seguridad.access import LockState, lock_status, register_failure
from apps.seguridad.models import AccesoUsuario
from tests.base import (
    NegocioTestCase,
    borrar_negocio_de_prueba,
    crear_negocio_de_prueba,
)

User = get_user_model()
Rol = Perfil.Rol

CLAVE = "Clave-Segura-123"
INCORRECTA = "otra-clave"


class BloqueoEnElLoginDelNegocioTests(NegocioTestCase):
    esquema = "bloqueo"
    dominio = "bloqueo.localhost"

    def crear(self, rol, nombre):
        usuario = User.objects.create_user(
            username=nombre, email=f"{nombre}@correo.cl", password=CLAVE
        )
        Perfil.objects.filter(user=usuario).update(rol=rol, debe_cambiar_clave=False)
        return usuario

    def entrar(self, correo, clave=CLAVE):
        return Client(HTTP_HOST=self.dominio).post(
            reverse("login"), {"username": correo, "password": clave}
        )

    def fallar(self, correo, veces):
        respuesta = None
        for _ in range(veces):
            respuesta = self.entrar(correo, INCORRECTA)
        return respuesta

    def test_los_primeros_fallos_dan_el_mensaje_de_siempre(self):
        self.crear(Rol.COLABORADOR, "laura")
        respuesta = self.fallar("laura@correo.cl", 3)
        self.assertContains(respuesta, "Correo o contraseña incorrectos.")
        self.assertNotContains(respuesta, "Te queda 1 intento")

    def test_el_cuarto_fallo_avisa_que_queda_un_intento(self):
        self.crear(Rol.COLABORADOR, "laura")
        respuesta = self.fallar("laura@correo.cl", 4)
        self.assertContains(
            respuesta,
            "Te queda 1 intento antes de que la cuenta se bloquee por un rato.",
        )

    def test_una_colaboradora_bloqueada_sabe_a_quien_pedir_ayuda(self):
        laura = self.crear(Rol.COLABORADOR, "laura")
        respuesta = self.fallar("LAURA@correo.cl", 5)
        hora = timezone.localtime(lock_status(laura).until).strftime("%H:%M")
        self.assertContains(
            respuesta,
            f"Esta cuenta quedó bloqueada por intentos fallidos. Podrás volver a intentarlo a las {hora}.",
        )
        self.assertContains(
            respuesta, "pide al propietario o a un encargado que te desbloquee"
        )

    def test_una_encargada_bloqueada_pide_ayuda_al_propietario(self):
        self.crear(Rol.ENCARGADO, "ana")
        respuesta = self.fallar("ana@correo.cl", 5)
        self.assertContains(
            respuesta, "pide al propietario del negocio que te desbloquee"
        )

    def test_la_propietaria_bloqueada_pide_ayuda_al_soporte(self):
        self.crear(Rol.PROPIETARIO, "maria")
        respuesta = self.fallar("maria@correo.cl", 5)
        self.assertContains(respuesta, "pide ayuda al soporte de Hi Agenda")

    def test_bloqueada_no_entra_ni_con_la_clave_correcta(self):
        laura = self.crear(Rol.COLABORADOR, "laura")
        self.fallar("laura@correo.cl", 5)
        respuesta = self.entrar("laura@correo.cl")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Esta cuenta quedó bloqueada")
        self.assertEqual(lock_status(laura).failures, 5)

    def test_entrar_bien_reinicia_el_conteo(self):
        laura = self.crear(Rol.COLABORADOR, "laura")
        self.fallar("laura@correo.cl", 3)
        self.assertRedirects(
            self.entrar("laura@correo.cl"),
            reverse("calendar"),
            fetch_redirect_response=False,
        )
        self.assertEqual(lock_status(laura).failures, 0)

    def test_un_correo_que_no_existe_no_crea_filas(self):
        respuesta = self.fallar("nadie@correo.cl", 6)
        self.assertContains(respuesta, "Correo o contraseña incorrectos.")
        self.assertFalse(AccesoUsuario.objects.exists())


class BloqueoAisladoPorNegocioTests(NegocioTestCase):
    esquema = "bloqueo_a"
    dominio = "bloqueo-a.localhost"

    @classmethod
    def setUpClass(cls):
        cls.otro = crear_negocio_de_prueba("bloqueo_b")
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        borrar_negocio_de_prueba(cls.otro)

    def test_un_bloqueo_en_un_negocio_no_toca_el_mismo_correo_en_otro(self):
        laura = User.objects.create_user(
            username="laura", email="laura@correo.cl", password=CLAVE
        )
        for _ in range(5):
            register_failure(laura)
        with schema_context("bloqueo_b"):
            otra_laura = User.objects.create_user(
                username="laura", email="laura@correo.cl", password=CLAVE
            )
            self.assertEqual(lock_status(otra_laura).state, LockState.FREE)
        connection.set_tenant(self.negocio)
        self.assertEqual(lock_status(laura).state, LockState.TEMPORARY)
