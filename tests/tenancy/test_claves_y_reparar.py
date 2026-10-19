from io import StringIO
from unittest import mock

from django.conf import settings
from django.contrib.admin.models import LogEntry
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
from tests.base import NegocioTestCase

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

    def ajax(self, metodo, url, datos=None):
        return getattr(self.panel, metodo)(url, datos or {}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def test_el_modal_pide_confirmar_la_identidad(self):
        url = url_panel("tenancy_negocio_clave_propietario", self.negocio.pk)
        modal = self.ajax("get", url)
        self.assertTemplateUsed(modal, "panel/businesses/owner_password_modal.html")
        self.assertContains(modal, 'name="identity_confirmed"')
        self.assertContains(modal, 'id="owner_password_submit_btn"')
        self.assertContains(modal, f'action="{url}"')
        self.assertNotContains(modal, "Dirección del negocio")
        Dominio.objects.create(domain="claves.localhost", tenant=self.negocio, is_primary=True)
        modal = self.ajax("get", url)
        self.assertContains(modal, "Dirección del negocio")
        self.assertContains(
            modal,
            'href="http://claves.localhost/" class="icon-link-button" target="_blank" rel="noopener noreferrer"',
        )
        self.assertRedirects(
            self.panel.get(url), url_panel("tenancy_negocio_change", self.negocio.pk), fetch_redirect_response=False
        )

    def test_restablecer_la_clave_del_propietario_exige_confirmar_identidad(self):
        url = url_panel("tenancy_negocio_clave_propietario", self.negocio.pk)
        sin_confirmar = self.ajax("post", url)
        self.assertEqual(sin_confirmar.status_code, 400)
        self.assertEqual(
            sin_confirmar.json()["errors"],
            [{"id_element": "id_identity_confirmed", "error": "Confirma la identidad del titular antes de generar la clave."}],
        )
        with schema_context(self.esquema):
            self.assertTrue(User.objects.get(pk=self.propietario.pk).check_password("vieja"))
        respuesta = self.ajax("post", url, {"identity_confirmed": "on"})
        self.assertIn("no-store", respuesta["Cache-Control"])
        datos = respuesta.json()
        self.assertEqual(datos["email"], "maria@correo.cl")
        clave = datos["password"]
        self.assertRegex(clave, r"^[a-z2-9]{4}-[a-z2-9]{4}-[a-z2-9]{4}$")
        registro = LogEntry.objects.filter(object_id=str(self.negocio.pk), content_type__model="negocio").latest("action_time")
        self.assertEqual(registro.change_message, "Clave del propietario restablecida.")
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
        url = url_panel("tenancy_negocio_clave_propietario", self.negocio.pk)
        modal = self.ajax("get", url)
        self.assertContains(modal, "El negocio todavía no está listo: primero repara su alta.")
        self.assertNotContains(modal, 'id="owner_password_submit_btn"')
        respuesta = self.ajax("post", url, {"identity_confirmed": "on"})
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["message"], "El negocio todavía no está listo: primero repara su alta.")
        with schema_context(self.esquema):
            self.assertTrue(User.objects.get(pk=self.propietario.pk).check_password("vieja"))

    def test_sin_propietario_no_genera_clave(self):
        with schema_context(self.esquema):
            Perfil.objects.filter(user=self.propietario).update(rol=Perfil.Rol.ENCARGADO)
        respuesta = self.ajax(
            "post", url_panel("tenancy_negocio_clave_propietario", self.negocio.pk), {"identity_confirmed": "on"}
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(respuesta.json()["message"], "Este negocio no tiene propietario: repara su alta.")

    def test_el_modal_de_reparar_muestra_el_error_y_el_correo(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(
            estado=Negocio.Estado.PREPARANDO, error_preparacion="OperationalError: sin espacio en disco"
        )
        PersonaCorreo.objects.create(persona=self.negocio.titular, correo="maria@correo.cl", etiqueta="acceso")
        modal = self.ajax("get", url_panel("tenancy_negocio_reparar", self.negocio.pk))
        self.assertTemplateUsed(modal, "panel/businesses/business_repair_modal.html")
        self.assertContains(modal, "La última preparación falló")
        self.assertContains(modal, "OperationalError: sin espacio en disco")
        self.assertContains(modal, "maria@correo.cl")
        self.assertContains(modal, "status-current__badge--fallido")
        self.assertContains(modal, 'status-current__badge--fallido">Falló</span>')
        self.assertContains(modal, 'id="business_repair_submit_btn"')

    def test_sin_error_registrado_avisa_que_la_tarea_no_termino(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=Negocio.Estado.PREPARANDO)
        PersonaCorreo.objects.create(persona=self.negocio.titular, correo="maria@correo.cl", etiqueta="acceso")
        modal = self.ajax("get", url_panel("tenancy_negocio_reparar", self.negocio.pk))
        self.assertContains(modal, "La preparación no terminó")
        self.assertContains(modal, "status-current__badge--preparando")
        self.assertNotContains(modal, "La última preparación falló")

    def test_reparar_desde_el_panel_vuelve_a_encolar_con_el_correo_de_acceso(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=Negocio.Estado.PREPARANDO)
        PersonaCorreo.objects.create(persona=self.negocio.titular, correo="personal@correo.cl", es_principal=True)
        PersonaCorreo.objects.create(persona=self.negocio.titular, correo="maria@correo.cl", etiqueta="acceso")
        with mock.patch.object(preparar_negocio, "delay") as encolar:
            respuesta = self.ajax("post", url_panel("tenancy_negocio_reparar", self.negocio.pk))
        encolar.assert_called_once_with(self.negocio.pk, "maria@correo.cl", None)
        self.assertEqual(respuesta.json(), {"message": "La preparación se volvió a encolar.", "email": "maria@correo.cl"})
        registro = LogEntry.objects.filter(object_id=str(self.negocio.pk), content_type__model="negocio").latest("action_time")
        self.assertEqual(registro.change_message, "Preparación encolada de nuevo.")

    def test_sin_correo_de_acceso_no_se_repara(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=Negocio.Estado.PREPARANDO)
        url = url_panel("tenancy_negocio_reparar", self.negocio.pk)
        self.assertContains(self.ajax("get", url), "El titular no tiene correo")
        with mock.patch.object(preparar_negocio, "delay") as encolar:
            respuesta = self.ajax("post", url)
        self.assertEqual(respuesta.status_code, 400)
        encolar.assert_not_called()

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
        url = url_panel("tenancy_negocio_reparar", self.negocio.pk)
        modal = self.ajax("get", url)
        self.assertContains(modal, "Solo se reparan las altas que quedaron en «preparando».")
        self.assertNotContains(modal, 'id="business_repair_submit_btn"')
        with mock.patch.object(preparar_negocio, "delay") as encolar:
            self.assertEqual(self.ajax("post", url).status_code, 400)
        encolar.assert_not_called()
        self.assertRedirects(
            self.panel.get(url), url_panel("tenancy_negocio_change", self.negocio.pk), fetch_redirect_response=False
        )

    def test_solo_un_superusuario_restablece_o_repara(self):
        connection.set_schema_to_public()
        staff = User.objects.create_user(username="staff", password="x", is_staff=True)
        navegador = Client(HTTP_HOST="admin.localhost")
        navegador.force_login(staff)
        for nombre in ("tenancy_negocio_clave_propietario", "tenancy_negocio_reparar"):
            with self.subTest(nombre=nombre):
                self.assertEqual(navegador.get(url_panel(nombre, self.negocio.pk)).status_code, 403)
        respuesta = navegador.post(
            url_panel("tenancy_negocio_clave_propietario", self.negocio.pk),
            {"identity_confirmed": "on"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(respuesta.status_code, 403)
        with schema_context(self.esquema):
            self.assertTrue(User.objects.get(pk=self.propietario.pk).check_password("vieja"))
