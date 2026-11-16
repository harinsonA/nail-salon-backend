from django.urls import reverse

from apps.settings.preferences.registry import (
    APP_LATEST_VERSION,
    APP_MAINTENANCE,
    APP_MAINTENANCE_MESSAGE,
    APP_MINIMUM_VERSION,
    APP_MODULE,
)
from apps.settings.preferences.service import set_preference
from apps.tenancy.models import Negocio
from tests.apis.base import ApiTestCase


class StartupTests(ApiTestCase):
    esquema = "api_startup"
    dominio = "api-startup.localhost"

    def startup(self, **headers):
        return self.api_client.get(reverse("api_startup"), **headers)

    def test_answers_without_session_with_the_whole_contract(self):
        response = self.startup()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "business": {"nombre": self.negocio.nombre, "estado": "activo", "overdue": False},
                "app_enabled": True,
                "maintenance": {"active": False, "message": None},
                "version": {"minimum": None, "latest": None},
                "currency": "CLP",
                "zona_horaria": "America/Santiago",
            },
        )

    def test_reports_platform_versions_and_maintenance(self):
        set_preference(APP_MINIMUM_VERSION.key, "1.2.0")
        set_preference(APP_LATEST_VERSION.key, "1.4.0")
        set_preference(APP_MAINTENANCE.key, True)
        set_preference(APP_MAINTENANCE_MESSAGE.key, "Volvemos a las 10")
        data = self.startup().json()
        self.assertEqual(data["version"], {"minimum": "1.2.0", "latest": "1.4.0"})
        self.assertEqual(data["maintenance"], {"active": True, "message": "Volvemos a las 10"})

    def test_answers_even_with_old_version_or_disabled_app(self):
        set_preference(APP_MINIMUM_VERSION.key, "2.0.0")
        set_preference(APP_MODULE.key, False)
        response = self.startup(HTTP_X_APP_VERSION="1.0.0")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["app_enabled"])

    def test_reports_business_status_even_when_unavailable(self):
        for estado, overdue in ((Negocio.Estado.MOROSO, True), (Negocio.Estado.PAUSADO, False)):
            with self.subTest(estado=estado):
                Negocio.objects.filter(pk=self.negocio.pk).update(estado=estado)
                response = self.startup()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["business"]["estado"], estado)
                self.assertEqual(response.json()["business"]["overdue"], overdue)

    def test_only_accepts_get_and_answers_errors_as_json(self):
        self.assertApiError(self.api_client.post(reverse("api_startup")), 405, "method_not_allowed")
        self.assertApiError(self.api_client.get("/api/v1/missing/"), 404, "not_found")
