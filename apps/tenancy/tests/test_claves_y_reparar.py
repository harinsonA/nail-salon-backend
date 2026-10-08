import re
from io import StringIO
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import Client
from django.urls import reverse
from django_tenants.utils import get_public_schema_name, schema_context

from apps.profiles.models import Perfil
from apps.tenancy.models import Dominio, Negocio, Persona, PersonaCorreo
from apps.tenancy.tasks import preparar_negocio
from apps.tenancy.testing import NegocioTestCase

User = get_user_model()


def url_panel(nombre, *args):
    return reverse(f"admin:{nombre}", args=args, urlconf=settings.PUBLIC_SCHEMA_URLCONF)


class ClavesYRepararTests(NegocioTestCase):
    esquema = "claves"

    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain="admin.localhost", tenant=publico, is_primary=True)
        cls.admin = User.objects.create_superuser(username="admin", password="x")

    def setUp(self):
        super().setUp()
        with schema_context(self.esquema):
            self.propietario = User.objects.create_user(username="maria", email="maria@correo.cl", password="vieja")
            Perfil.objects.filter(user=self.propietario).update(rol=Perfil.Rol.PROPIETARIO, debe_cambiar_clave=False)
        connection.set_schema_to_public()
        self.panel = Client(HTTP_HOST="admin.localhost")
        self.panel.force_login(self.admin)

    def test_restablecer_la_clave_del_propietario_exige_confirmar_identidad(self):
        url = url_panel("tenancy_negocio_clave_propietario", self.negocio.pk)
        sin_confirmar = self.panel.post(url, {})
        self.assertIn("identidad_confirmada", sin_confirmar.context["form"].errors)
        respuesta = self.panel.post(url, {"identidad_confirmada": "on"})
        self.assertIn("no-store", respuesta["Cache-Control"])
        clave = re.search(r"<code[^>]*>([a-z2-9-]{14})</code>", respuesta.content.decode()).group(1)
        with schema_context(self.esquema):
            self.propietario.refresh_from_db()
            self.assertTrue(self.propietario.check_password(clave))
            self.assertFalse(self.propietario.check_password("vieja"))
            self.assertTrue(self.propietario.perfil.debe_cambiar_clave)
            self.assertIsNone(self.propietario.perfil.history.first().history_user_id)
        ultimo = Negocio.objects.get(pk=self.negocio.pk).history.first()
        self.assertEqual(ultimo.history_change_reason, "Clave del propietario restablecida")
        self.assertEqual(ultimo.history_user, self.admin)

    def test_la_ficha_ofrece_restablecer_o_reparar_segun_el_estado(self):
        ficha = self.panel.get(url_panel("tenancy_negocio_change", self.negocio.pk))
        self.assertContains(ficha, url_panel("tenancy_negocio_clave_propietario", self.negocio.pk))
        self.assertNotContains(ficha, url_panel("tenancy_negocio_reparar", self.negocio.pk))
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=Negocio.Estado.PREPARANDO)
        ficha = self.panel.get(url_panel("tenancy_negocio_change", self.negocio.pk))
        self.assertContains(ficha, url_panel("tenancy_negocio_reparar", self.negocio.pk))
        self.assertNotContains(ficha, url_panel("tenancy_negocio_clave_propietario", self.negocio.pk))

    def test_no_se_restablece_la_clave_de_un_alta_sin_terminar(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=Negocio.Estado.PREPARANDO)
        respuesta = self.panel.post(
            url_panel("tenancy_negocio_clave_propietario", self.negocio.pk), {"identidad_confirmada": "on"}
        )
        self.assertRedirects(
            respuesta, url_panel("tenancy_negocio_change", self.negocio.pk), fetch_redirect_response=False
        )

    def test_reparar_desde_el_panel_vuelve_a_encolar_con_el_correo_de_acceso(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=Negocio.Estado.PREPARANDO)
        PersonaCorreo.objects.create(persona=self.negocio.titular, correo="personal@correo.cl", es_principal=True)
        PersonaCorreo.objects.create(persona=self.negocio.titular, correo="maria@correo.cl", etiqueta="acceso")
        with mock.patch.object(preparar_negocio, "delay") as encolar:
            self.panel.post(url_panel("tenancy_negocio_reparar", self.negocio.pk))
        encolar.assert_called_once_with(self.negocio.pk, "maria@correo.cl", None)

    def test_reparar_por_comando_deja_el_negocio_activo(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=Negocio.Estado.PREPARANDO)
        PersonaCorreo.objects.create(persona=self.negocio.titular, correo="maria@correo.cl", etiqueta="acceso")
        salida = StringIO()
        call_command("reparar_negocio", self.esquema, stdout=salida)
        self.assertEqual(Negocio.objects.get(pk=self.negocio.pk).estado, Negocio.Estado.ACTIVO)
        self.assertIn("quedó activo", salida.getvalue())
        with schema_context(self.esquema):
            self.assertEqual(User.objects.filter(email="maria@correo.cl").count(), 1)
            self.assertEqual(Perfil.objects.filter(rol=Perfil.Rol.PROPIETARIO).count(), 1)

    def test_reparar_rechaza_negocios_activos_o_inexistentes(self):
        for negocio in (self.esquema, "no-existe"):
            with self.subTest(negocio=negocio), self.assertRaises(CommandError):
                call_command("reparar_negocio", negocio, stdout=StringIO())
        respuesta = self.panel.post(url_panel("tenancy_negocio_reparar", self.negocio.pk))
        self.assertRedirects(
            respuesta, url_panel("tenancy_negocio_change", self.negocio.pk), fetch_redirect_response=False
        )

    def test_solo_un_superusuario_restablece_o_repara(self):
        connection.set_schema_to_public()
        staff = User.objects.create_user(username="staff", password="x", is_staff=True)
        navegador = Client(HTTP_HOST="admin.localhost")
        navegador.force_login(staff)
        for nombre in ("tenancy_negocio_clave_propietario", "tenancy_negocio_reparar"):
            with self.subTest(nombre=nombre):
                self.assertEqual(navegador.get(url_panel(nombre, self.negocio.pk)).status_code, 403)
