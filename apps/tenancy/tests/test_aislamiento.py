from django.apps import apps
from django.conf import settings
from django.db import ProgrammingError, connection, transaction
from django.test import Client, SimpleTestCase
from django_tenants.utils import get_public_schema_name

from apps.clients.models import Cliente
from apps.tenancy.entorno_local import TABLAS_RENOMBRADAS, tablas_solo_de_negocio
from apps.tenancy.models import Dominio, Negocio
from apps.tenancy.testing import NegocioTestCase


class AislamientoDeEsquemasTests(NegocioTestCase):
    esquema = "aislado"

    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain="localhost", tenant=publico, is_primary=True)
        Dominio.objects.create(domain="admin.localhost", tenant=publico, is_primary=False)

    def esquemas_por_tabla(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_name, array_agg(table_schema::text) FROM information_schema.tables "
                "WHERE table_schema IN (%s, %s) GROUP BY table_name",
                [get_public_schema_name(), self.esquema],
            )
            return {tabla: set(esquemas) for tabla, esquemas in cursor.fetchall()}

    def test_cada_tabla_de_negocio_existe_solo_dentro_del_negocio(self):
        esquemas = self.esquemas_por_tabla()
        tablas = tablas_solo_de_negocio() - set(TABLAS_RENOMBRADAS)
        self.assertGreater(len(tablas), 20)
        for tabla in sorted(tablas):
            with self.subTest(tabla=tabla):
                self.assertEqual(esquemas.get(tabla), {self.esquema})

    def test_cada_tabla_de_la_plataforma_existe_solo_en_public(self):
        esquemas = self.esquemas_por_tabla()
        modelos = apps.get_app_config("tenancy").get_models(include_auto_created=True)
        for tabla in sorted(modelo._meta.db_table for modelo in modelos):
            with self.subTest(tabla=tabla):
                self.assertEqual(esquemas.get(tabla), {get_public_schema_name()})

    def test_consultar_datos_de_negocio_sin_negocio_activo_falla(self):
        connection.set_schema_to_public()
        with self.assertRaises(ProgrammingError), transaction.atomic():
            Cliente.objects.count()

    def test_la_raiz_publica_no_expone_la_agenda_ni_el_panel(self):
        raiz = Client(HTTP_HOST="localhost")
        for ruta in ("/admin/login/", "/inicio_sesion/", "/calendario/", "/clientes/"):
            with self.subTest(ruta=ruta):
                self.assertEqual(raiz.get(ruta).status_code, 404)

    def test_el_panel_responde_solo_en_su_subdominio(self):
        panel = Client(HTTP_HOST="admin.localhost")
        self.assertEqual(panel.get("/admin/login/").status_code, 200)
        for ruta in ("/inicio_sesion/", "/calendario/"):
            with self.subTest(ruta=ruta):
                self.assertEqual(panel.get(ruta).status_code, 404)


class OrdenDelMiddlewareTests(SimpleTestCase):
    def test_el_middleware_de_negocios_va_primero(self):
        middleware = settings.MIDDLEWARE
        posicion = middleware.index("django_tenants.middleware.main.TenantMainMiddleware")
        self.assertEqual(posicion, 0)
        self.assertLess(posicion, middleware.index("django.contrib.sessions.middleware.SessionMiddleware"))
        self.assertLess(posicion, middleware.index("django.contrib.auth.middleware.AuthenticationMiddleware"))
