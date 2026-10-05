from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name, schema_context

from apps.clients.models import Cliente
from apps.tenancy.models import Dominio, Negocio

User = get_user_model()

NEGOCIOS = ("uno", "dos")
HOST_INEXISTENTE = "inexistente.localhost"
CORREO = "ana@correo.cl"
CLAVES = {"uno": "Clave-Del-Negocio-Uno-1", "dos": "Clave-Del-Negocio-Dos-2"}
LOGIN_URL = "/inicio_sesion/"
CALENDARIO_URL = "/calendario/"


def host(esquema):
    return f"{esquema}.localhost"


class UsuariosPorNegocioTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hosts_agregados = [host(n) for n in NEGOCIOS] + [HOST_INEXISTENTE]
        settings.ALLOWED_HOSTS += cls.hosts_agregados
        connection.set_schema_to_public()
        cls.negocios = {}
        for esquema in NEGOCIOS:
            negocio = Negocio.objects.create(schema_name=esquema, nombre=f"Negocio {esquema}")
            negocio.create_schema(check_if_exists=True, verbosity=0)
            Dominio.objects.create(domain=host(esquema), tenant=negocio, is_primary=True)
            cls.negocios[esquema] = negocio
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        connection.set_schema_to_public()
        for negocio in cls.negocios.values():
            negocio.domains.all().delete()
            negocio.delete(force_drop=True)
        for h in cls.hosts_agregados:
            settings.ALLOWED_HOSTS.remove(h)

    def crear_usuario(self, esquema):
        with schema_context(esquema):
            return User.objects.create_user(username="ana", email=CORREO, password=CLAVES[esquema])

    def iniciar_sesion(self, esquema, clave):
        cliente = Client(HTTP_HOST=host(esquema))
        respuesta = cliente.post(LOGIN_URL, {"username": "ana", "password": clave})
        return cliente, respuesta

    def test_el_mismo_correo_existe_por_separado_en_cada_negocio(self):
        for esquema in NEGOCIOS:
            self.crear_usuario(esquema)
        for esquema in NEGOCIOS:
            with schema_context(esquema):
                self.assertEqual(User.objects.filter(email=CORREO).count(), 1)
                self.assertTrue(User.objects.get(email=CORREO).check_password(CLAVES[esquema]))
        with schema_context(get_public_schema_name()):
            self.assertFalse(User.objects.filter(email=CORREO).exists())

    def test_cada_negocio_acepta_solo_su_propia_clave(self):
        for esquema in NEGOCIOS:
            self.crear_usuario(esquema)
        _, propia = self.iniciar_sesion("uno", CLAVES["uno"])
        self.assertRedirects(propia, CALENDARIO_URL, fetch_redirect_response=False)
        _, ajena = self.iniciar_sesion("dos", CLAVES["uno"])
        self.assertEqual(ajena.status_code, 200)
        self.assertFalse(ajena.wsgi_request.user.is_authenticated)

    def test_la_sesion_de_un_negocio_no_sirve_en_otro(self):
        for esquema in NEGOCIOS:
            self.crear_usuario(esquema)
        cliente, respuesta = self.iniciar_sesion("uno", CLAVES["uno"])
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(cliente.get(CALENDARIO_URL).status_code, 200)
        en_otro_negocio = cliente.get(CALENDARIO_URL, HTTP_HOST=host("dos"))
        self.assertEqual(en_otro_negocio.status_code, 302)
        self.assertTrue(en_otro_negocio.url.startswith(LOGIN_URL))

    def test_los_datos_de_un_negocio_no_aparecen_en_otro(self):
        with schema_context("uno"):
            Cliente.objects.create(nombre="Laura")
            self.assertEqual(Cliente.all_objects.count(), 1)
        with schema_context("dos"):
            self.assertEqual(Cliente.all_objects.count(), 0)

    def test_las_tablas_de_negocio_no_existen_en_public(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT table_schema FROM information_schema.tables WHERE table_name = %s ORDER BY 1",
                ["clientes"],
            )
            esquemas = [fila[0] for fila in cursor.fetchall()]
        self.assertEqual(esquemas, sorted(NEGOCIOS))

    def test_un_subdominio_inexistente_responde_404(self):
        respuesta = Client(HTTP_HOST=HOST_INEXISTENTE).get(LOGIN_URL)
        self.assertEqual(respuesta.status_code, 404)

    def test_el_middleware_de_negocios_va_antes_de_sesion_y_autenticacion(self):
        middleware = settings.MIDDLEWARE
        posicion = middleware.index("django_tenants.middleware.main.TenantMainMiddleware")
        self.assertEqual(posicion, 0)
        self.assertLess(posicion, middleware.index("django.contrib.sessions.middleware.SessionMiddleware"))
        self.assertLess(posicion, middleware.index("django.contrib.auth.middleware.AuthenticationMiddleware"))
