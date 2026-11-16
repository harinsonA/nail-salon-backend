import json

from django.db import connection
from django.test import Client, TestCase, override_settings
from django_tenants.utils import get_public_schema_name

from apps.settings.models import Preference
from apps.settings.preferences import APP_LATEST_VERSION, APP_MINIMUM_VERSION
from apps.tenancy.models import Dominio, Negocio

ROOT = "localhost"
PANEL = "admin.localhost"
URL = "/api/platform/app-release/"
SECRET = "clave-de-prueba"


@override_settings(APP_RELEASE_SECRET=SECRET, DOMINIO_BASE=ROOT)
class AppReleaseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=ROOT, tenant=public, is_primary=True)
        Dominio.objects.create(domain=PANEL, tenant=public)

    def setUp(self):
        connection.set_schema_to_public()

    def post(self, body=None, secret=SECRET, host=ROOT, raw=None):
        headers = {"HTTP_AUTHORIZATION": f"Bearer {secret}"} if secret is not None else {}
        data = raw if raw is not None else json.dumps(body if body is not None else {"version": "1.4.0"})
        return Client(HTTP_HOST=host).post(URL, data, content_type="application/json", **headers)

    def test_registers_the_latest_version_with_its_reason(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"version": "1.4.0", "changed": True})
        self.assertEqual(APP_LATEST_VERSION.get(), "1.4.0")
        record = Preference.history.get(key=APP_LATEST_VERSION.key)
        self.assertIsNone(record.history_user)
        self.assertEqual(record.history_change_reason, "Publicación automática")

    def test_the_same_version_does_not_write_again(self):
        self.post()
        response = self.post()
        self.assertEqual(response.json(), {"version": "1.4.0", "changed": False})
        self.assertEqual(Preference.history.count(), 1)

    def test_rejects_calls_without_the_secret(self):
        for secret in (None, "", "otra-clave", SECRET.upper()):
            with self.subTest(secret=secret):
                response = self.post(secret=secret)
                self.assertEqual(response.status_code, 401)
        self.assertFalse(Preference.objects.exists())

    def test_rejects_a_secret_without_bearer(self):
        response = Client(HTTP_HOST=ROOT).post(
            URL, json.dumps({"version": "1.4.0"}), content_type="application/json", HTTP_AUTHORIZATION=SECRET
        )
        self.assertEqual(response.status_code, 401)

    @override_settings(APP_RELEASE_SECRET="")
    def test_an_empty_setting_rejects_everything(self):
        self.assertEqual(self.post(secret="").status_code, 401)
        self.assertFalse(Preference.objects.exists())

    def test_rejects_versions_without_the_shape(self):
        for body in ({"version": "1.4"}, {"version": "v1.4.0"}, {"version": ""}, {"version": 140}, {}, ["1.4.0"]):
            with self.subTest(body=body):
                self.assertEqual(self.post(body).status_code, 400)
        self.assertEqual(self.post(raw="no es json").status_code, 400)
        self.assertFalse(Preference.objects.exists())

    def test_rejects_a_version_below_the_minimum(self):
        APP_MINIMUM_VERSION.set("1.10.0")
        response = self.post({"version": "1.9.0"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("La versión mínima no puede ser mayor", response.json()["message"])
        self.assertEqual(APP_LATEST_VERSION.get(), "")
        self.assertEqual(self.post({"version": "1.10.0"}).status_code, 200)

    def test_only_accepts_post(self):
        response = Client(HTTP_HOST=ROOT).get(URL, HTTP_AUTHORIZATION=f"Bearer {SECRET}")
        self.assertEqual(response.status_code, 405)

    def test_only_lives_on_the_root_domain(self):
        self.assertEqual(self.post(host=PANEL).status_code, 404)
