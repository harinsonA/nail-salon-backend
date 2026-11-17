from django.urls import reverse

from apis.v1.catalogs.registry import CATALOG_VIEWS
from apps.common.utils.countries.constants import Country
from apps.payments.choices import MetodoPago
from apps.profiles.models import Perfil
from tests.apis.base import ApiTestCase

Rol = Perfil.Rol


class CatalogTests(ApiTestCase):
    esquema = "api_catalogs"
    dominio = "api-catalogs.localhost"

    def catalog(self, name):
        response = self.api_client.get(reverse(name))
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_countries_carry_their_identifier_types(self):
        self.log_in_as(Rol.COLABORADOR)
        countries = self.catalog("api_catalogs_countries")
        self.assertEqual([country["code"] for country in countries], list(Country.values))
        chile = next(country for country in countries if country["code"] == "CL")
        self.assertEqual(chile["name"], "Chile")
        self.assertEqual(
            chile["identifier_types"],
            [{"value": "rut", "label": "RUT"}, {"value": "pasaporte", "label": "Pasaporte"}],
        )

    def test_phone_prefixes_match_the_web_labels(self):
        self.log_in_as(Rol.ENCARGADO)
        prefixes = self.catalog("api_catalogs_phone_prefixes")
        self.assertEqual(len(prefixes), len(Country.values))
        self.assertIn({"value": "+56", "label": "CL (+56)", "country": "CL"}, prefixes)

    def test_payment_methods_come_from_the_web(self):
        self.log_in_as(Rol.PROPIETARIO)
        methods = self.catalog("api_catalogs_payment_methods")
        self.assertEqual(methods, [{"value": value, "label": label} for value, label in MetodoPago.CHOICES])

    def test_catalogs_need_a_session(self):
        for view in CATALOG_VIEWS:
            with self.subTest(catalog=view.slug):
                response = self.api_client.get(reverse(view.route_name()))
                self.assertApiError(response, 401, "session_required")

    def test_unknown_catalog_answers_404_in_json(self):
        self.log_in_as(Rol.COLABORADOR)
        response = self.api_client.get("/api/v1/catalogs/colores/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(response.json()["code"])
