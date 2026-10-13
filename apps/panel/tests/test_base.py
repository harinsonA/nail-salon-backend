from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase
from django.urls import set_urlconf
from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import Dominio, Negocio

User = get_user_model()


class BaseAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        publico = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain="admin.localhost", tenant=publico, is_primary=True)
        cls.admin = User.objects.create_superuser(username="admin", password="x")

    def renderizar(self):
        connection.set_schema_to_public()
        pedido = RequestFactory().get("/admin/", HTTP_HOST="admin.localhost")
        pedido.user = self.admin
        pedido.session = {}
        set_urlconf(settings.PUBLIC_SCHEMA_URLCONF)
        try:
            return render_to_string("panel/base.html", request=pedido)
        finally:
            set_urlconf(None)

    def test_se_renderiza_en_el_panel_sin_rutas_de_negocio(self):
        html = self.renderizar()
        self.assertIn('data-login-url="/admin/login/"', html)
        self.assertIn('action="/admin/logout/"', html)
        self.assertIn("<title>Panel · Hi Agenda</title>", html)

    def test_no_arrastra_piezas_del_negocio(self):
        html = self.renderizar()
        for pieza in ("menu__brand", "session_expiry_modal", "profile_modal", "data-session-ping-url", "pago pendiente"):
            with self.subTest(pieza=pieza):
                self.assertNotIn(pieza, html)

    def test_trae_las_librerias_compartidas(self):
        html = self.renderizar()
        for libreria in ("dataTables.min.js", "select2.min.js", "bootstrap-datepicker.min.js",
                         "jquery.bootstrap.modal.forms.min.js", "custom.main.js", "custom.bs_modals.js"):
            with self.subTest(libreria=libreria):
                self.assertIn(libreria, html)
