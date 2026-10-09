from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import Client, TestCase, override_settings
from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import Dominio, Negocio, Persona


class PaginaPublicaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain="localhost", tenant=publico, is_primary=True)
        el_corte = Negocio.objects.create(
            schema_name="el_corte", nombre="El Corte", titular=Persona.objects.create(nombres="X")
        )
        Dominio.objects.create(domain="el-corte.localhost", tenant=el_corte, is_primary=True)

    def setUp(self):
        self.raiz = Client(HTTP_HOST="localhost")

    def test_la_raiz_muestra_la_entrada_a_los_negocios(self):
        respuesta = self.raiz.get("/")
        self.assertContains(respuesta, "Entrar a mi negocio")
        self.assertContains(respuesta, ".localhost")

    def test_lleva_al_login_del_negocio(self):
        respuesta = self.raiz.get("/", {"negocio": "  El-Corte "})
        self.assertRedirects(respuesta, "http://el-corte.localhost/inicio_sesion/", fetch_redirect_response=False)

    def test_el_enlace_usa_el_puerto_del_navegador_no_el_del_servidor(self):
        detras_del_proxy = Client(HTTP_HOST="localhost", SERVER_PORT="10000")
        respuesta = detras_del_proxy.get("/", {"negocio": "el-corte"})
        self.assertEqual(respuesta["Location"], "http://el-corte.localhost/inicio_sesion/")
        en_desarrollo = Client(HTTP_HOST="localhost:8000")
        respuesta = en_desarrollo.get("/", {"negocio": "el-corte"})
        self.assertEqual(respuesta["Location"], "http://el-corte.localhost:8000/inicio_sesion/")

    def test_no_redirige_fuera_de_la_plataforma_ni_a_lo_que_no_existe(self):
        for negocio in ("no-existe", "admin", "evil.com", "//evil.com", "el-corte.evil.com", "localhost"):
            with self.subTest(negocio=negocio):
                respuesta = self.raiz.get("/", {"negocio": negocio})
                self.assertEqual(respuesta.status_code, 200)
                self.assertContains(respuesta, "No encontramos ese negocio")

    def test_el_resto_de_la_raiz_sigue_en_404(self):
        for ruta in ("/admin/login/", "/inicio_sesion/", "/calendario/"):
            with self.subTest(ruta=ruta):
                self.assertEqual(self.raiz.get(ruta).status_code, 404)


class ConfigurarPlataformaTests(TestCase):
    def setUp(self):
        connection.set_schema_to_public()

    @override_settings(DEBUG=False, DOMINIO_BASE="localhost")
    def test_en_produccion_exige_dominio_base(self):
        with self.assertRaises(CommandError):
            call_command("configurar_plataforma", stdout=StringIO())

    @override_settings(DOMINIO_BASE="hi-agenda.test", RENDER_EXTERNAL_HOSTNAME="hai-agenda.onrender.com")
    def test_registra_la_plataforma_con_sus_dominios_y_se_puede_repetir(self):
        call_command("configurar_plataforma", "--extra", "otro.test", stdout=StringIO())
        salida = StringIO()
        call_command("configurar_plataforma", stdout=salida)
        publico = Negocio.objects.get(schema_name=get_public_schema_name())
        self.assertEqual(publico.estado, Negocio.Estado.ACTIVO)
        self.assertEqual(
            set(publico.domains.values_list("domain", flat=True)),
            {"hi-agenda.test", "www.hi-agenda.test", "admin.hi-agenda.test", "hai-agenda.onrender.com", "otro.test"},
        )
        self.assertEqual(publico.domains.get(is_primary=True).domain, "hi-agenda.test")
        self.assertIn("ya existía", salida.getvalue())

    @override_settings(DOMINIO_BASE="hi-agenda.test", RENDER_EXTERNAL_HOSTNAME="")
    def test_no_le_quita_un_dominio_a_otro_negocio(self):
        otro = Negocio.objects.create(schema_name="otro", nombre="Otro", titular=Persona.objects.create(nombres="X"))
        Dominio.objects.create(domain="www.hi-agenda.test", tenant=otro)
        salida = StringIO()
        call_command("configurar_plataforma", stdout=salida)
        self.assertEqual(Dominio.objects.get(domain="www.hi-agenda.test").tenant, otro)
        self.assertIn("ya apunta a otro negocio", salida.getvalue())
