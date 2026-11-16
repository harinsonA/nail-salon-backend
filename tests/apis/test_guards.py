from unittest.mock import patch

from django.test import override_settings
from rest_framework.test import APIClient

from apps.profiles.models import Perfil
from apps.settings.preferences.registry import (
    APP_MAINTENANCE,
    APP_MAINTENANCE_MESSAGE,
    APP_MINIMUM_VERSION,
    APP_MODULE,
)
from apps.settings.preferences.service import set_preference
from apps.tenancy.models import Negocio
from tests.apis.base import ApiTestCase

TEST_URLCONF = "tests.apis.urls_for_tests"
ADMINISTRATION_ONLY = {"api_sample_admin"}
TEAM_ONLY = {"api_sample_team"}


@override_settings(ROOT_URLCONF=TEST_URLCONF)
@patch("apis.common.guards.SOLO_ADMINISTRACION", ADMINISTRATION_ONLY)
@patch("apis.common.guards.SOLO_CON_EQUIPO", TEAM_ONLY)
@patch("apps.tenancy.business_status.status.SOLO_ADMINISTRACION", ADMINISTRATION_ONLY)
class GuardChainTests(ApiTestCase):
    esquema = "api_guards"
    dominio = "api-guards.localhost"

    def call(self, path="/api/v1/sample/", **headers):
        return self.api_client.get(path, **headers)

    def set_status(self, estado):
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=estado)

    def test_route_answers_when_everything_is_in_order(self):
        self.log_in_as(Perfil.Rol.COLABORADOR)
        self.assertEqual(self.call().status_code, 200)

    def test_version_below_minimum_answers_426(self):
        set_preference(APP_MINIMUM_VERSION.key, "1.10.0")
        self.log_in_as(Perfil.Rol.PROPIETARIO)
        self.assertApiError(self.call(HTTP_X_APP_VERSION="1.9.0"), 426, "outdated_version")
        self.assertEqual(self.call(HTTP_X_APP_VERSION="1.10.0").status_code, 200)

    def test_missing_or_malformed_version_answers_426_only_with_a_minimum(self):
        self.api_client = APIClient(HTTP_HOST=self.dominio)
        self.log_in_as(Perfil.Rol.PROPIETARIO)
        self.assertEqual(self.call().status_code, 200)
        set_preference(APP_MINIMUM_VERSION.key, "1.0.0")
        self.assertApiError(self.call(), 426, "outdated_version")
        self.assertApiError(self.call(HTTP_X_APP_VERSION="one"), 426, "outdated_version")

    def test_version_is_checked_before_session(self):
        set_preference(APP_MINIMUM_VERSION.key, "2.0.0")
        self.assertApiError(self.call(), 426, "outdated_version")

    def test_disabled_app_answers_403(self):
        set_preference(APP_MODULE.key, False)
        self.assertApiError(self.call(), 403, "app_disabled")

    def test_maintenance_answers_503_with_its_message(self):
        set_preference(APP_MAINTENANCE.key, True)
        self.assertApiError(self.call(), 503, "maintenance")
        set_preference(APP_MAINTENANCE_MESSAGE.key, "Volvemos a las 10")
        self.assertEqual(self.call().json()["message"], "Volvemos a las 10")

    def test_unavailable_business_answers_like_the_web(self):
        expected = {
            Negocio.Estado.PREPARANDO: (503, "business_preparing"),
            Negocio.Estado.PAUSADO: (410, "business_paused"),
            Negocio.Estado.CANCELADO: (410, "business_cancelled"),
        }
        self.log_in_as(Perfil.Rol.PROPIETARIO)
        for estado, (status_code, code) in expected.items():
            with self.subTest(estado=estado):
                self.set_status(estado)
                self.assertApiError(self.call(), status_code, code)

    def test_without_session_answers_401_except_open_routes(self):
        self.assertApiError(self.call(), 401, "session_required")
        self.assertEqual(self.call("/api/v1/sample/open/").status_code, 200)

    def test_user_limit_lets_only_the_owner_in(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(limite_usuarios=1)
        self.make_user(Perfil.Rol.PROPIETARIO)
        self.log_in_as(Perfil.Rol.ENCARGADO)
        self.assertApiError(self.call(), 401, "user_limit_reached")

    def test_temporary_password_answers_428_except_where_allowed(self):
        self.log_in_as(Perfil.Rol.ENCARGADO, debe_cambiar_clave=True)
        self.assertApiError(self.call(), 428, "temporary_password")
        self.assertEqual(self.call("/api/v1/sample/password/").status_code, 200)

    def test_collaborator_cannot_enter_administration(self):
        self.log_in_as(Perfil.Rol.COLABORADOR)
        self.assertApiError(self.call("/api/v1/sample/admin/"), 403, "forbidden")

    def test_manager_and_owner_enter_administration(self):
        for rol in (Perfil.Rol.ENCARGADO, Perfil.Rol.PROPIETARIO):
            with self.subTest(rol=rol):
                self.log_in_as(rol)
                self.assertEqual(self.call("/api/v1/sample/admin/").status_code, 200)
                self.api_client.force_authenticate(None)
                Perfil.objects.filter(rol=rol).delete()

    def test_without_team_answers_403(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(limite_usuarios=1)
        self.log_in_as(Perfil.Rol.PROPIETARIO)
        self.assertApiError(self.call("/api/v1/sample/team/"), 403, "team_disabled")

    def test_overdue_pauses_administration_and_keeps_the_calendar(self):
        self.set_status(Negocio.Estado.MOROSO)
        self.log_in_as(Perfil.Rol.PROPIETARIO)
        self.assertApiError(self.call("/api/v1/sample/admin/"), 402, "payment_pending")
        self.assertEqual(self.call().status_code, 200)
