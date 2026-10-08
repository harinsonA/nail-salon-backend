import re
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase
from django.urls import reverse
from django_tenants.utils import get_public_schema_name, schema_context

from apps.clients.models import Cliente
from apps.profiles.models import Perfil
from apps.settings.models import ConfiguracionNegocio
from apps.tenancy.alta import generar_clave_temporal
from apps.tenancy.models import Dominio, Negocio, Persona, PersonaCorreo, Rubro
from apps.tenancy.tasks import preparar_negocio
from nail_salon_api.celery import app

User = get_user_model()

PANEL = "admin.localhost"


def url_panel(nombre, *args):
    return reverse(f"admin:{nombre}", args=args, urlconf=settings.PUBLIC_SCHEMA_URLCONF)


class PanelYAltaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=publico, is_primary=True)
        cls.admin = User.objects.create_superuser(username="admin", email="admin@correo.cl", password="x")

    def setUp(self):
        connection.set_schema_to_public()
        self.modo_inmediato = app.conf.CELERY_TASK_ALWAYS_EAGER
        app.conf.CELERY_TASK_ALWAYS_EAGER = True
        self.panel = Client(HTTP_HOST=PANEL)
        self.panel.force_login(self.admin)

    def tearDown(self):
        app.conf.CELERY_TASK_ALWAYS_EAGER = self.modo_inmediato
        connection.set_schema_to_public()

    def datos(self, **cambios):
        datos = {
            "nombre": "Barbería El Corte",
            "subdominio": "el-corte",
            "rubro": Rubro.objects.get(codigo="barberia").pk,
            "zona_horaria": "America/Santiago",
            "nombres": "Carlos",
            "apellidos": "Rojas",
            "codigo_pais": "+56",
            "telefono": "912345678",
            "correo": "Carlos@ElCorte.cl",
        }
        datos.update(cambios)
        return datos

    def dar_de_alta(self, **cambios):
        return self.panel.post(url_panel("tenancy_negocio_alta"), self.datos(**cambios))

    def test_el_formulario_de_alta_carga_y_agregar_lleva_ahi(self):
        self.assertContains(self.panel.get(url_panel("tenancy_negocio_alta")), "Dar de alta")
        self.assertRedirects(
            self.panel.get(url_panel("tenancy_negocio_add")),
            url_panel("tenancy_negocio_alta"),
            fetch_redirect_response=False,
        )

    @mock.patch.object(preparar_negocio, "delay")
    def test_rechaza_subdominios_invalidos_reservados_o_tomados(self, encolar):
        tomado = Negocio.objects.create(schema_name="tomado", nombre="Tomado", titular=Persona.objects.create(nombres="X"))
        Dominio.objects.create(domain="tomado.localhost", tenant=tomado)
        for subdominio in ("admin", "Mi Barberia", "ab", "tomado", "legado"):
            with self.subTest(subdominio=subdominio):
                respuesta = self.dar_de_alta(subdominio=subdominio)
                self.assertEqual(respuesta.status_code, 200)
                self.assertIn("subdominio", respuesta.context["form"].errors)
        encolar.assert_not_called()

    @mock.patch.object(preparar_negocio, "delay")
    def test_pide_un_titular_y_valida_su_telefono(self, encolar):
        sin_titular = self.dar_de_alta(nombres="")
        self.assertIn("nombres", sin_titular.context["form"].errors)
        telefono_malo = self.dar_de_alta(telefono="812345678")
        self.assertIn("telefono", telefono_malo.context["form"].errors)
        encolar.assert_not_called()

    def test_alta_completa_de_punta_a_punta(self):
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.dar_de_alta()

        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("no-store", respuesta["Cache-Control"])
        clave = respuesta.context["clave"]
        self.assertContains(respuesta, clave)
        negocio = Negocio.objects.get(schema_name="el_corte")
        self.assertEqual(negocio.estado, Negocio.Estado.ACTIVO)
        self.assertIsNone(negocio.error_preparacion)
        self.assertEqual(negocio.creado_por, self.admin)
        self.assertEqual(negocio.rubro.codigo, "barberia")
        self.assertEqual(negocio.domains.get(is_primary=True).domain, "el-corte.localhost")
        self.assertEqual(negocio.titular.correos.get(es_principal=True).correo, "carlos@elcorte.cl")
        self.assertEqual(negocio.titular.telefonos.get(es_principal=True).numero, "912345678")
        self.assertEqual(
            list(negocio.history.values_list("history_change_reason", flat=True)),
            ["Alta terminada", "Alta desde el panel"],
        )

        with schema_context("el_corte"):
            propietario = User.objects.get(email="carlos@elcorte.cl")
            self.assertTrue(propietario.check_password(clave))
            self.assertNotIn(clave, propietario.password)
            self.assertEqual(propietario.perfil.rol, Perfil.Rol.PROPIETARIO)
            self.assertTrue(propietario.perfil.debe_cambiar_clave)
            self.assertFalse(propietario.is_superuser)
            self.assertEqual(ConfiguracionNegocio.objects.get().nombre_visible, "Barbería El Corte")
            self.assertFalse(Cliente.all_objects.exists())

        connection.set_schema_to_public()
        navegador = Client(HTTP_HOST="el-corte.localhost")
        entrada = navegador.post(reverse("login"), {"username": "carlos@elcorte.cl", "password": clave})
        self.assertRedirects(entrada, reverse("calendar"), fetch_redirect_response=False)
        self.assertRedirects(navegador.get(reverse("calendar")), reverse("cambiar_clave"), fetch_redirect_response=False)

    @mock.patch.object(preparar_negocio, "delay")
    def test_con_un_titular_existente_suma_el_correo_sin_cambiar_su_principal(self, encolar):
        persona = Persona.objects.create(nombres="Carlos")
        PersonaCorreo.objects.create(persona=persona, correo="carlos@gmail.com", es_principal=True)
        with self.captureOnCommitCallbacks(execute=True):
            self.dar_de_alta(titular=persona.pk, nombres="", correo="local@elcorte.cl")
        self.assertEqual(Negocio.objects.get(schema_name="el_corte").titular, persona)
        self.assertEqual(persona.correos.get(es_principal=True).correo, "carlos@gmail.com")
        self.assertTrue(persona.correos.filter(correo="local@elcorte.cl", es_principal=False).exists())
        encolar.assert_called_once()
        negocio_id, correo, hash_clave = encolar.call_args.args
        self.assertEqual(correo, "local@elcorte.cl")
        self.assertTrue(hash_clave.startswith("pbkdf2_"))

    def test_si_la_preparacion_falla_queda_el_motivo(self):
        negocio = Negocio.objects.create(
            schema_name="falla", nombre="Falla", titular=Persona.objects.create(nombres="X")
        )
        with mock.patch.object(Negocio, "create_schema", side_effect=RuntimeError("sin espacio en disco")):
            with self.assertRaises(RuntimeError):
                preparar_negocio(negocio.pk, "x@correo.cl", None)
        negocio.refresh_from_db()
        self.assertEqual(negocio.estado, Negocio.Estado.PREPARANDO)
        self.assertIn("sin espacio en disco", negocio.error_preparacion)
        self.assertEqual(negocio.history.first().history_change_reason, "La preparación falló")

    def test_solo_un_superusuario_da_de_alta(self):
        staff = User.objects.create_user(username="staff", password="x", is_staff=True)
        navegador = Client(HTTP_HOST=PANEL)
        navegador.force_login(staff)
        self.assertEqual(navegador.get(url_panel("tenancy_negocio_alta")).status_code, 403)

    def test_la_lista_no_muestra_public_y_no_se_borra_nada(self):
        negocio = Negocio.objects.create(schema_name="uno", nombre="Uno", titular=Persona.objects.create(nombres="X"))
        lista = self.panel.get(url_panel("tenancy_negocio_changelist"))
        self.assertEqual(list(lista.context["cl"].queryset), [negocio])
        borrar = self.panel.get(url_panel("tenancy_negocio_delete", negocio.pk))
        self.assertEqual(borrar.status_code, 403)

    def test_la_clave_temporal_es_legible_y_distinta_cada_vez(self):
        claves = {generar_clave_temporal() for _ in range(20)}
        self.assertEqual(len(claves), 20)
        for clave in claves:
            self.assertRegex(clave, re.compile(r"^[a-z2-9]{4}-[a-z2-9]{4}-[a-z2-9]{4}$"))
