import re
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase
from django.urls import reverse
from django_tenants.utils import get_public_schema_name, schema_context

from apps.clients.models import Cliente
from apps.common.claves import generar_clave_temporal
from apps.profiles.models import Perfil
from apps.settings.models import ConfiguracionNegocio
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
        publico = Negocio.objects.create(
            schema_name=get_public_schema_name(), nombre="Hi Agenda"
        )
        Dominio.objects.create(domain=PANEL, tenant=publico, is_primary=True)
        cls.admin = User.objects.create_superuser(
            username="admin", email="admin@correo.cl", password="x"
        )
        cls.titular = Persona.objects.create(nombres="Carlos", apellidos="Rojas")

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
            "esquema": "el_corte",
            "titular": self.titular.pk,
            "correo": "Carlos@ElCorte.cl",
            "rubro": Rubro.objects.get(codigo="barberia").pk,
            "zona_horaria": "America/Santiago",
            "notas_internas": "",
            "address-calle": "",
            "address-numero": "",
            "address-complemento": "",
            "address-codigo_postal": "",
            "address-comuna": "",
            "address-ciudad": "",
            "address-region": "",
            "address-pais": "CL",
            "address-referencia": "",
        }
        datos.update(cambios)
        return datos

    def crear(self, **cambios):
        return self.panel.post(url_panel("tenancy_negocio_add"), self.datos(**cambios))

    def test_la_pagina_de_crear_carga_y_la_de_alta_lleva_ahi(self):
        respuesta = self.panel.get(url_panel("tenancy_negocio_add"))
        self.assertTemplateUsed(respuesta, "panel/businesses/form.html")
        self.assertTemplateUsed(respuesta, "panel/base.html")
        for texto in (
            "Nuevo negocio",
            "Datos básicos",
            "Dirección",
            "Notas internas",
            "Crear negocio",
        ):
            with self.subTest(texto=texto):
                self.assertContains(respuesta, texto)
        for campo in ("nombres", "apellidos", "telefono", "codigo_pais"):
            with self.subTest(campo=campo):
                self.assertNotContains(respuesta, f'name="{campo}"')
        self.assertRedirects(
            self.panel.get(url_panel("tenancy_negocio_alta")),
            url_panel("tenancy_negocio_add"),
            fetch_redirect_response=False,
        )

    @mock.patch.object(preparar_negocio, "delay")
    def test_rechaza_subdominios_invalidos_reservados_o_tomados(self, encolar):
        tomado = Negocio.objects.create(
            schema_name="tomado",
            nombre="Tomado",
            titular=Persona.objects.create(nombres="X"),
        )
        Dominio.objects.create(domain="tomado.localhost", tenant=tomado)
        for subdominio in (
            "admin",
            "Mi Barberia",
            "ab",
            "tomado",
            "legado",
            "salon2",
            "el_corte",
        ):
            with self.subTest(subdominio=subdominio):
                respuesta = self.crear(subdominio=subdominio, esquema="otro_esquema")
                self.assertEqual(respuesta.status_code, 200)
                self.assertIn("subdominio", respuesta.context["form"].errors)
                self.assertEqual(respuesta.context["sections_with_errors"], ["basic"])
        encolar.assert_not_called()

    @mock.patch.object(preparar_negocio, "delay")
    def test_rechaza_esquemas_invalidos_reservados_o_tomados(self, encolar):
        Negocio.objects.create(
            schema_name="tomado",
            nombre="Tomado",
            titular=Persona.objects.create(nombres="X"),
        )
        casos = {
            "el-corte": "solo admite letras minúsculas",
            "corte2": "solo admite letras minúsculas",
            "ab": "entre 3 y 40",
            "pg_datos": "reservado",
            "public": "reservado",
            "tomado": "Ya existe un esquema",
        }
        for esquema, mensaje in casos.items():
            with self.subTest(esquema=esquema):
                errores = self.crear(esquema=esquema).context["form"].errors
                self.assertIn(mensaje, errores["esquema"][0])
        with mock.patch(
            "apps.panel.views.businesses.view.schema_exists", return_value=True
        ):
            errores = self.crear(esquema="huerfano").context["form"].errors
        self.assertIn("Ya existe un esquema", errores["esquema"][0])
        encolar.assert_not_called()

    @mock.patch.object(preparar_negocio, "delay")
    def test_pide_un_titular_existente_y_un_correo(self, encolar):
        sin_titular = self.crear(titular="", correo="")
        self.assertIn("titular", sin_titular.context["form"].errors)
        self.assertIn("correo", sin_titular.context["form"].errors)
        inexistente = self.crear(titular=999999)
        self.assertIn("titular", inexistente.context["form"].errors)
        self.assertContains(sin_titular, "is-invalid")
        encolar.assert_not_called()

    @mock.patch.object(preparar_negocio, "delay")
    def test_aplica_las_reglas_de_los_campos(self, encolar):
        respuesta = self.crear(
            nombre="Barbería 21",
            rubro="",
            notas_internas="x" * 251,
            **{"address-comuna": "Providencia 2"},
        )
        form = respuesta.context["form"]
        self.assertIn("caracteres alfabéticos y espacios", form.errors["nombre"][0])
        self.assertIn("rubro", form.errors)
        self.assertIn("250", form.errors["notas_internas"][0])
        direccion = respuesta.context["addresses"]
        self.assertEqual(
            direccion.errors["calle"][0], "Escribe la calle para guardar la dirección."
        )
        self.assertIn("caracteres alfabéticos", direccion.errors["comuna"][0])
        self.assertEqual(
            respuesta.context["sections_with_errors"], ["basic", "addresses", "notes"]
        )
        self.assertFalse(Negocio.objects.filter(schema_name="el_corte").exists())
        encolar.assert_not_called()

    def test_creacion_completa_de_punta_a_punta(self):
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.crear(
                esquema="corte_central",
                notas_internas="Primer mes sin costo.",
                **{
                    "address-calle": "Av. Providencia",
                    "address-numero": "1234",
                    "address-comuna": "Providencia",
                },
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "panel/businesses/created.html")
        self.assertIn("no-store", respuesta["Cache-Control"])
        clave = respuesta.context["password"]
        self.assertContains(respuesta, clave)
        negocio = Negocio.objects.get(schema_name="corte_central")
        self.assertEqual(negocio.estado, Negocio.Estado.ACTIVO)
        self.assertIsNone(negocio.error_preparacion)
        self.assertEqual(negocio.creado_por, self.admin)
        self.assertEqual(negocio.titular, self.titular)
        self.assertEqual(negocio.rubro.codigo, "barberia")
        self.assertEqual(negocio.notas_internas, "Primer mes sin costo.")
        self.assertEqual(
            negocio.domains.get(is_primary=True).domain, "el-corte.localhost"
        )
        direccion = negocio.direcciones.get()
        self.assertEqual(
            (
                direccion.calle,
                direccion.numero,
                direccion.comuna,
                direccion.es_principal,
            ),
            ("Av. Providencia", "1234", "Providencia", True),
        )
        self.assertTrue(
            self.titular.correos.filter(
                correo="carlos@elcorte.cl", etiqueta="acceso"
            ).exists()
        )
        self.assertEqual(
            list(negocio.history.values_list("history_change_reason", flat=True)),
            ["Alta terminada", "Creado desde el panel"],
        )

        with schema_context("corte_central"):
            propietario = User.objects.get(email="carlos@elcorte.cl")
            self.assertTrue(propietario.check_password(clave))
            self.assertNotIn(clave, propietario.password)
            self.assertEqual(propietario.perfil.rol, Perfil.Rol.PROPIETARIO)
            self.assertTrue(propietario.perfil.debe_cambiar_clave)
            self.assertFalse(propietario.is_superuser)
            self.assertEqual(
                ConfiguracionNegocio.objects.get().nombre_visible, "Barbería El Corte"
            )
            self.assertFalse(Cliente.all_objects.exists())

        connection.set_schema_to_public()
        navegador = Client(HTTP_HOST="el-corte.localhost")
        entrada = navegador.post(
            reverse("login"), {"username": "carlos@elcorte.cl", "password": clave}
        )
        self.assertRedirects(
            entrada, reverse("calendar"), fetch_redirect_response=False
        )
        self.assertRedirects(
            navegador.get(reverse("calendar")),
            reverse("cambiar_clave"),
            fetch_redirect_response=False,
        )

    @mock.patch.object(preparar_negocio, "delay")
    def test_no_repite_subdominio_ni_esquema(self, encolar):
        with self.captureOnCommitCallbacks(execute=True):
            self.crear()
        repetido = self.crear(nombre="Otro Corte").context["form"].errors
        self.assertEqual(
            repetido["subdominio"], ["Ese subdominio ya lo usa otro negocio."]
        )
        self.assertEqual(
            repetido["esquema"], ["Ya existe un esquema con ese nombre en la base."]
        )
        self.assertEqual(Negocio.objects.filter(nombre="Otro Corte").count(), 0)
        encolar.assert_called_once()

    @mock.patch.object(preparar_negocio, "delay")
    def test_sin_direccion_no_crea_ninguna(self, encolar):
        with self.captureOnCommitCallbacks(execute=True):
            self.crear()
        self.assertFalse(
            Negocio.objects.get(schema_name="el_corte").direcciones.exists()
        )

    @mock.patch.object(preparar_negocio, "delay")
    def test_con_un_titular_existente_suma_el_correo_sin_cambiar_su_principal(
        self, encolar
    ):
        PersonaCorreo.objects.create(
            persona=self.titular, correo="carlos@gmail.com", es_principal=True
        )
        with self.captureOnCommitCallbacks(execute=True):
            self.crear(correo="local@elcorte.cl")
        self.assertEqual(
            self.titular.correos.get(es_principal=True).correo, "carlos@gmail.com"
        )
        self.assertTrue(
            self.titular.correos.filter(
                correo="local@elcorte.cl", es_principal=False
            ).exists()
        )
        encolar.assert_called_once()
        negocio_id, correo, hash_clave = encolar.call_args.args
        self.assertEqual(correo, "local@elcorte.cl")
        self.assertTrue(hash_clave.startswith("pbkdf2_"))

    def test_si_la_preparacion_falla_queda_el_motivo(self):
        negocio = Negocio.objects.create(
            schema_name="falla",
            nombre="Falla",
            titular=Persona.objects.create(nombres="X"),
        )
        with mock.patch.object(
            Negocio, "create_schema", side_effect=RuntimeError("sin espacio en disco")
        ):
            with self.assertRaises(RuntimeError):
                preparar_negocio(negocio.pk, "x@correo.cl", None)
        negocio.refresh_from_db()
        self.assertEqual(negocio.estado, Negocio.Estado.PREPARANDO)
        self.assertIn("sin espacio en disco", negocio.error_preparacion)
        self.assertEqual(
            negocio.history.first().history_change_reason, "La preparación falló"
        )

    def test_solo_un_superusuario_crea_negocios(self):
        staff = User.objects.create_user(username="staff", password="x", is_staff=True)
        navegador = Client(HTTP_HOST=PANEL)
        navegador.force_login(staff)
        self.assertEqual(
            navegador.get(url_panel("tenancy_negocio_add")).status_code, 403
        )
        self.assertEqual(
            navegador.post(url_panel("tenancy_negocio_add"), self.datos()).status_code,
            403,
        )
        self.assertFalse(Negocio.objects.filter(schema_name="el_corte").exists())

    def test_la_lista_no_muestra_public_y_no_se_borra_nada(self):
        negocio = Negocio.objects.create(
            schema_name="uno", nombre="Uno", titular=Persona.objects.create(nombres="X")
        )
        datos = self.panel.get(
            url_panel("tenancy_negocio_list_ajax"),
            {"draw": 1, "start": 0, "length": 10},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual([fila["pk"] for fila in datos.json()["data"]], [negocio.pk])
        borrar = self.panel.get(url_panel("tenancy_negocio_delete", negocio.pk))
        self.assertEqual(borrar.status_code, 403)

    def test_la_clave_temporal_es_legible_y_distinta_cada_vez(self):
        claves = {generar_clave_temporal() for _ in range(20)}
        self.assertEqual(len(claves), 20)
        for clave in claves:
            self.assertRegex(
                clave, re.compile(r"^[a-z2-9]{4}-[a-z2-9]{4}-[a-z2-9]{4}$")
            )
