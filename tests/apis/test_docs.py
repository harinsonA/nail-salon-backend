from django.test import override_settings
from django.urls import reverse

from tests.apis.base import ApiTestCase


class DocsTests(ApiTestCase):
    esquema = "api_docs"
    dominio = "api-docs.localhost"

    @override_settings(DEBUG=True)
    def test_locally_the_schema_lists_the_api_routes(self):
        response = self.api_client.get(reverse("api_schema"), {"format": "json"})
        self.assertEqual(response.status_code, 200)
        paths = response.json()["paths"]
        self.assertIn("/api/v1/startup/", paths)
        self.assertNotIn("/api/v1/schema/", paths)

    @override_settings(DEBUG=True)
    def test_locally_the_docs_page_opens(self):
        self.assertEqual(self.api_client.get(reverse("api_docs")).status_code, 200)

    def test_outside_local_they_do_not_exist(self):
        for name in ("api_schema", "api_docs"):
            with self.subTest(route=name):
                self.assertApiError(self.api_client.get(reverse(name)), 404, "not_found")
