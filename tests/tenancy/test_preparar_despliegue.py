from io import StringIO

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import Negocio
from apps.tenancy.plataforma import asegurar_dominio, asegurar_negocio_publico

User = get_user_model()


class PrepararDespliegueTests(TestCase):
    def setUp(self):
        connection.set_schema_to_public()

    @override_settings(DOMINIO_BASE="hi-agenda.test", RENDER_EXTERNAL_HOSTNAME="hai-agenda.onrender.com")
    def test_migra_y_registra_la_plataforma_y_se_puede_repetir(self):
        call_command("preparar_despliegue", verbosity=0, stdout=StringIO())
        salida = StringIO()
        call_command("preparar_despliegue", verbosity=0, stdout=salida)
        publico = Negocio.objects.get(schema_name=get_public_schema_name())
        self.assertEqual(
            set(publico.domains.values_list("domain", flat=True)),
            {"hi-agenda.test", "www.hi-agenda.test", "admin.hi-agenda.test", "hai-agenda.onrender.com"},
        )
        self.assertIn("ya existía", salida.getvalue())

    @override_settings(DEBUG=False, DOMINIO_BASE="localhost")
    def test_falla_si_falta_dominio_base_en_produccion(self):
        with self.assertRaises(CommandError):
            call_command("preparar_despliegue", verbosity=0, stdout=StringIO())


class PanelSinTokensTests(TestCase):
    def setUp(self):
        connection.set_schema_to_public()
        publico, _ = asegurar_negocio_publico()
        asegurar_dominio("admin.localhost", publico, es_principal=True)
        self.panel = Client(HTTP_HOST="admin.localhost")
        self.panel.force_login(User.objects.create_superuser(username="admin", password="x"))

    def test_el_panel_no_muestra_los_tokens_de_la_api(self):
        inicio = self.panel.get(reverse("admin:index", urlconf=settings.PUBLIC_SCHEMA_URLCONF))
        self.assertEqual(inicio.status_code, 200)
        self.assertNotContains(inicio, "authtoken")
        self.assertNotContains(inicio, "Not available for global schema")
