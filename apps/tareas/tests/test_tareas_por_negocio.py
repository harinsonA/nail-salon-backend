from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test import Client, TestCase
from django.urls import reverse
from django_tenants.utils import schema_context

from apps.clients.models import Cliente
from apps.profiles.models import Perfil
from apps.tareas.cola import encolar
from apps.tareas.decorators import background_task
from apps.tareas.models import TareaEnProceso
from apps.tenancy.testing import borrar_negocio_de_prueba, crear_negocio_de_prueba
from nail_salon_api.celery import app

User = get_user_model()

NEGOCIOS = {"tareas_uno": "tareas-uno.localhost", "tareas_dos": "tareas-dos.localhost"}


@background_task
def crear_cliente_de_prueba(tarea, user):
    Cliente.objects.create(nombre=f"Creada en {connection.schema_name}")
    tarea.completar()


class TareasPorNegocioTests(TestCase):
    @classmethod
    def setUpClass(cls):
        settings.ALLOWED_HOSTS += list(NEGOCIOS.values())
        cls.negocios = [crear_negocio_de_prueba(esquema, dominio=host) for esquema, host in NEGOCIOS.items()]
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        for negocio in cls.negocios:
            borrar_negocio_de_prueba(negocio)
        for host in NEGOCIOS.values():
            settings.ALLOWED_HOSTS.remove(host)

    def setUp(self):
        self.modo_inmediato = app.conf.CELERY_TASK_ALWAYS_EAGER
        app.conf.CELERY_TASK_ALWAYS_EAGER = True

    def tearDown(self):
        app.conf.CELERY_TASK_ALWAYS_EAGER = self.modo_inmediato
        connection.set_schema_to_public()

    def crear_tarea(self, esquema):
        with schema_context(esquema):
            usuario = User.objects.create_user(username=f"usuario_{esquema}")
            return TareaEnProceso.objects.create(nombre_proceso="Prueba", origen="prueba", user_id=usuario.id)

    def test_la_tarea_trabaja_en_el_negocio_que_la_encolo(self):
        tarea = self.crear_tarea("tareas_uno")
        with schema_context("tareas_uno"):
            encolar(crear_cliente_de_prueba, tarea)
            tarea.refresh_from_db()
            self.assertEqual(tarea.estado, TareaEnProceso.Estado.COMPLETADO)
            self.assertTrue(tarea.celery_task_id)
            self.assertEqual(list(Cliente.all_objects.values_list("nombre", flat=True)), ["Creada en tareas_uno"])
        with schema_context("tareas_dos"):
            self.assertFalse(Cliente.all_objects.exists())

    def test_rechaza_esquemas_que_no_son_negocios(self):
        tarea = self.crear_tarea("tareas_uno")
        for esquema in ("public", "no_existe"):
            with self.subTest(esquema=esquema), self.assertRaises(ValueError):
                crear_cliente_de_prueba(esquema, tarea.id)
        with schema_context("tareas_uno"):
            self.assertEqual(TareaEnProceso.objects.get(pk=tarea.pk).estado, TareaEnProceso.Estado.PENDIENTE)

    def test_el_id_de_una_tarea_no_cruza_a_otro_negocio(self):
        tarea = self.crear_tarea("tareas_uno")
        with self.assertRaises(TareaEnProceso.DoesNotExist):
            crear_cliente_de_prueba("tareas_dos", tarea.id)

    def test_no_se_encola_desde_public(self):
        connection.set_schema_to_public()
        with self.assertRaises(RuntimeError):
            encolar(crear_cliente_de_prueba, mock.Mock(id=1))

    def test_la_importacion_de_clientes_funciona_dentro_de_un_negocio(self):
        with schema_context("tareas_uno"):
            usuario = User.objects.create_user(username="ana", password="clave-de-prueba")
            usuario.perfil.debe_cambiar_clave = False
            usuario.perfil.rol = Perfil.Rol.ENCARGADO
            usuario.perfil.save()
        navegador = Client(HTTP_HOST=NEGOCIOS["tareas_uno"])
        with schema_context("tareas_uno"):
            navegador.force_login(usuario)
        contenido = "Nombre,Apellido,Teléfono,Email,Estado,Notas\nLaura,Pérez,,laura@correo.cl,activo,\n"
        archivo = SimpleUploadedFile("clientes.csv", contenido.encode("utf-8"), content_type="text/csv")

        respuesta = navegador.post(reverse("client_import"), {"archivo": archivo})

        self.assertEqual(respuesta.status_code, 302)
        with schema_context("tareas_uno"):
            tarea = TareaEnProceso.objects.get()
            self.assertEqual(tarea.estado, TareaEnProceso.Estado.COMPLETADO, tarea.resultado_metadata)
            self.assertTrue(Cliente.objects.filter(nombre="Laura", apellido="Pérez").exists())
        with schema_context("tareas_dos"):
            self.assertFalse(Cliente.all_objects.exists())
