import re
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context

from apps.profiles.models import Perfil
from apps.seguridad.access import LockState, lock_status, register_failure
from apps.seguridad.models import AccesoUsuario
from apps.tenancy.models import Dominio, Negocio
from apps.tenancy.propietario import owner_lock_status, unlock_owner
from tests.base import NegocioTestCase

User = get_user_model()


def url_panel(nombre, *args):
    return reverse(f"admin:{nombre}", args=args, urlconf=settings.PUBLIC_SCHEMA_URLCONF)


class RescateDelPropietarioTests(NegocioTestCase):
    esquema = "rescate"

    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain="admin.localhost", tenant=publico, is_primary=True)
        cls.admin = User.objects.create_superuser(username="admin", password="x")
        cls.staff = User.objects.create_user(username="staff", password="x", is_staff=True)

    def setUp(self):
        super().setUp()
        with schema_context(self.esquema):
            self.propietario = User.objects.create_user(username="maria", email="maria@correo.cl", password="vieja")
            Perfil.objects.filter(user=self.propietario).update(rol=Perfil.Rol.PROPIETARIO, debe_cambiar_clave=False)
        connection.set_schema_to_public()
        self.panel = Client(HTTP_HOST="admin.localhost")
        self.panel.force_login(self.admin)

    def bloquear_propietario(self, definitivo=False):
        with schema_context(self.esquema):
            for _ in range(5):
                register_failure(self.propietario)
            if definitivo:
                AccesoUsuario.objects.filter(user=self.propietario).update(
                    bloqueado_hasta=timezone.now() - timedelta(seconds=1)
                )
                for _ in range(5):
                    register_failure(self.propietario)

    def negocio_fresco(self):
        return Negocio.objects.get(pk=self.negocio.pk)

    def estado_en_el_negocio(self):
        with schema_context(self.esquema):
            return lock_status(self.propietario)

    def test_el_panel_lee_el_estado_del_propietario(self):
        self.assertEqual(owner_lock_status(self.negocio_fresco()).state, LockState.FREE)
        self.bloquear_propietario(definitivo=True)
        self.assertEqual(owner_lock_status(self.negocio_fresco()).state, LockState.PERMANENT)

    def test_desbloquear_al_propietario_deja_rastro_en_los_dos_esquemas(self):
        self.bloquear_propietario(definitivo=True)
        self.assertEqual(unlock_owner(self.negocio_fresco(), self.admin), ("maria@correo.cl", True))
        self.assertFalse(self.estado_en_el_negocio().is_locked)
        with schema_context(self.esquema):
            acceso = AccesoUsuario.objects.get(user=self.propietario).history.first()
            self.assertEqual(acceso.history_change_reason, "Desbloqueado desde el panel")
            self.assertIsNone(acceso.history_user_id)
            self.assertTrue(User.objects.get(pk=self.propietario.pk).check_password("vieja"))
        ultimo = Negocio.objects.get(pk=self.negocio.pk).history.first()
        self.assertEqual(ultimo.history_change_reason, "Propietario desbloqueado")
        self.assertEqual(ultimo.history_user, self.admin)

    def test_desbloquear_a_quien_no_esta_bloqueado_no_toca_el_historial(self):
        antes = Negocio.objects.get(pk=self.negocio.pk).history.count()
        self.assertEqual(unlock_owner(self.negocio_fresco(), self.admin), ("maria@correo.cl", False))
        self.assertEqual(Negocio.objects.get(pk=self.negocio.pk).history.count(), antes)

    def test_sin_propietario_no_hay_nada_que_desbloquear(self):
        with schema_context(self.esquema):
            Perfil.objects.filter(user=self.propietario).update(rol=Perfil.Rol.ENCARGADO)
        self.assertIsNone(owner_lock_status(self.negocio_fresco()))
        self.assertIsNone(unlock_owner(self.negocio_fresco(), self.admin))

    def test_restablecer_la_clave_tambien_desbloquea(self):
        self.bloquear_propietario(definitivo=True)
        respuesta = self.panel.post(
            url_panel("tenancy_negocio_clave_propietario", self.negocio.pk), {"identidad_confirmada": "on"}
        )
        clave = re.search(r"<code[^>]*>([a-z2-9-]{14})</code>", respuesta.content.decode()).group(1)
        self.assertFalse(self.estado_en_el_negocio().is_locked)
        with schema_context(self.esquema):
            acceso = AccesoUsuario.objects.get(user=self.propietario)
            self.assertEqual(acceso.history.first().history_change_reason, "Desbloqueado al restablecer la clave desde el panel")
            self.assertTrue(User.objects.get(pk=self.propietario.pk).check_password(clave))

    def test_la_pantalla_muestra_el_bloqueo_y_desbloquea(self):
        self.bloquear_propietario(definitivo=True)
        url = url_panel("tenancy_negocio_desbloquear_propietario", self.negocio.pk)
        pantalla = self.panel.get(url)
        self.assertContains(pantalla, "Bloqueado hasta que alguien lo desbloquee")
        self.assertContains(pantalla, "Desbloquear al propietario")
        respuesta = self.panel.post(url, follow=True)
        self.assertRedirects(respuesta, url_panel("tenancy_negocio_change", self.negocio.pk))
        self.assertContains(respuesta, "El propietario (maria@correo.cl) quedó desbloqueado")
        self.assertFalse(self.estado_en_el_negocio().is_locked)

    def test_la_pantalla_avisa_si_no_esta_bloqueado(self):
        url = url_panel("tenancy_negocio_desbloquear_propietario", self.negocio.pk)
        self.assertContains(self.panel.get(url), "no está bloqueado")
        respuesta = self.panel.post(url, follow=True)
        self.assertContains(respuesta, "El propietario no estaba bloqueado: no hubo cambios.")

    def test_solo_un_superusuario_puede_desbloquear(self):
        self.bloquear_propietario()
        otro = Client(HTTP_HOST="admin.localhost")
        otro.force_login(self.staff)
        respuesta = otro.post(url_panel("tenancy_negocio_desbloquear_propietario", self.negocio.pk))
        self.assertEqual(respuesta.status_code, 403)
        self.assertTrue(self.estado_en_el_negocio().is_locked)

    def test_no_se_desbloquea_un_alta_sin_terminar(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=Negocio.Estado.PREPARANDO)
        respuesta = self.panel.post(url_panel("tenancy_negocio_desbloquear_propietario", self.negocio.pk))
        self.assertRedirects(
            respuesta, url_panel("tenancy_negocio_change", self.negocio.pk), fetch_redirect_response=False
        )

    def test_la_ficha_muestra_el_acceso_del_propietario_y_la_accion(self):
        ficha = self.panel.get(url_panel("tenancy_negocio_change", self.negocio.pk))
        self.assertContains(ficha, "Acceso del propietario")
        self.assertContains(ficha, "Sin bloqueo")
        self.assertContains(ficha, url_panel("tenancy_negocio_desbloquear_propietario", self.negocio.pk))
        self.bloquear_propietario()
        hora = timezone.localtime(self.estado_en_el_negocio().until).strftime("%H:%M")
        ficha = self.panel.get(url_panel("tenancy_negocio_change", self.negocio.pk))
        self.assertContains(ficha, f"Bloqueado hasta las {hora}")

    def test_la_ficha_de_un_alta_sin_terminar_no_consulta_el_esquema(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=Negocio.Estado.PREPARANDO)
        ficha = self.panel.get(url_panel("tenancy_negocio_change", self.negocio.pk))
        self.assertContains(ficha, "Acceso del propietario")
        self.assertNotContains(ficha, url_panel("tenancy_negocio_desbloquear_propietario", self.negocio.pk))
