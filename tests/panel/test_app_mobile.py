from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django_tenants.utils import get_public_schema_name

from apps.panel.permissions import build_permission_rows
from apps.settings.models import Preference
from apps.settings.preferences import (
    APP_LATEST_VERSION,
    APP_MAINTENANCE,
    APP_MAINTENANCE_MESSAGE,
    APP_MINIMUM_VERSION,
    Scope,
)
from apps.settings.preferences.versions import AppVersion
from apps.tenancy.models import Dominio, Negocio

User = get_user_model()

PANEL = "admin.localhost"
PAGE_URL = "/admin/settings/preferenciaplataforma/"
CHANGE_URL = f"{PAGE_URL}change/modal/"
HISTORY_URL = f"{PAGE_URL}history/modal/"
HISTORY_LIST_URL = f"{PAGE_URL}history/list/"


class AppVersionTests(SimpleTestCase):
    def test_compares_each_part_as_a_number(self):
        self.assertTrue(AppVersion.is_above("1.10.0", "1.9.0"))
        self.assertFalse(AppVersion.is_above("1.9.9", "1.10.0"))
        self.assertFalse(AppVersion.is_above("1.4.0", "1.4.0"))

    def test_an_empty_version_never_is_above(self):
        self.assertFalse(AppVersion.is_above("", "1.0.0"))
        self.assertFalse(AppVersion.is_above("2.0.0", ""))

    def test_check_range_rejects_minimum_above_latest(self):
        with self.assertRaisesMessage(ValidationError, "La versión mínima no puede ser mayor"):
            AppVersion.check_range("2.0.0", "1.9.9")
        AppVersion.check_range("1.0.0", "1.0.0")
        AppVersion.check_range("1.0.0", "")

    def test_clean_requires_the_shape(self):
        self.assertEqual(AppVersion.clean(" 1.4.0 "), "1.4.0")
        for value in ("1.4", "v1.4.0", "1.4.0.1", "1.a.0"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                AppVersion.clean(value)


@override_settings(DOMINIO_BASE="localhost")
class AppMobilePanelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
        cls.superuser = User.objects.create_superuser(
            username="admin", password="x", first_name="Ana", last_name="Rojas"
        )
        cls.viewer = User.objects.create_user(username="viewer", password="x", is_staff=True)
        cls.viewer.user_permissions.add(Permission.objects.get(codename="view_preferenciaplataforma"))
        cls.staff = User.objects.create_user(username="staff", password="x", is_staff=True)

    def setUp(self):
        connection.set_schema_to_public()

    def browser(self, user=None):
        browser = Client(HTTP_HOST=PANEL)
        browser.force_login(user or self.superuser)
        return browser

    def payload(self, **changes):
        data = {
            "app_version_minima": "1.0.0",
            "app_version_ultima": "1.2.0",
            "app_mantenimiento": "",
            "app_mantenimiento_mensaje": "",
        }
        data.update(changes)
        return {key: value for key, value in data.items() if value != ""}

    def post(self, user=None, **changes):
        return self.browser(user).post(
            CHANGE_URL, self.payload(**changes), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def errors(self, response):
        self.assertEqual(response.status_code, 400)
        return {error["id_element"]: error["error"] for error in response.json()["errors"]}

    def history(self, user=None):
        return self.browser(user).get(
            HISTORY_LIST_URL, {"draw": 1, "start": 0, "length": 10}, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def test_the_menu_has_the_section(self):
        response = self.browser().get("/admin/")
        self.assertContains(response, "Configuraciones")
        self.assertContains(response, f'href="{PAGE_URL}"')
        self.assertContains(response, "App móvil")

    def test_the_menu_hides_it_without_permission(self):
        response = self.browser(self.staff).get("/admin/")
        self.assertNotContains(response, f'href="{PAGE_URL}"')

    def test_the_page_shows_the_four_values_with_their_empty_labels(self):
        response = self.browser().get(PAGE_URL)
        self.assertTemplateUsed(response, "panel/app_mobile/detail.html")
        for label in ("Versión mínima", "Última versión", "Mantenimiento", "Mensaje de mantenimiento"):
            self.assertContains(response, label)
        self.assertContains(response, "Sin mínima")
        self.assertContains(response, "Sin registrar")
        self.assertContains(response, "Apagado")
        self.assertContains(response, "Texto por defecto")
        self.assertContains(response, 'id="app_mobile_table" class="table table-hover"')
        self.assertContains(response, '<th scope="col">Valor</th>')
        self.assertContains(response, "tableID: '#app_mobile_table'")
        self.assertContains(response, 'images/common/cancel.svg')
        self.assertContains(response, f'data-form-url="{CHANGE_URL}"')
        self.assertContains(response, f'data-form-url="{HISTORY_URL}"')

    def test_the_page_shows_saved_values(self):
        APP_MINIMUM_VERSION.set("1.1.0")
        APP_MAINTENANCE.set(True)
        response = self.browser().get(PAGE_URL)
        self.assertContains(response, "1.1.0")
        self.assertContains(response, 'images/common/check_circle.svg')

    def test_viewer_sees_the_page_without_the_edit_button(self):
        response = self.browser(self.viewer).get(PAGE_URL)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, f'data-form-url="{CHANGE_URL}"')
        self.assertContains(response, f'data-form-url="{HISTORY_URL}"')

    def test_staff_without_permission_cannot_open_it(self):
        self.assertEqual(self.browser(self.staff).get(PAGE_URL).status_code, 403)

    def test_the_modal_loads_current_values(self):
        APP_LATEST_VERSION.set("1.3.0")
        response = self.browser().get(CHANGE_URL, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTemplateUsed(response, "panel/app_mobile/app_mobile_modal.html")
        self.assertContains(response, 'value="1.3.0"')
        self.assertContains(response, 'id="app_mobile_submit_btn"')

    def test_saves_the_four_values(self):
        response = self.post(
            app_version_minima="1.1.0",
            app_version_ultima="1.4.0",
            app_mantenimiento="on",
            app_mantenimiento_mensaje="Volvemos a las 10",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "App móvil actualizada exitosamente.")
        self.assertEqual(APP_MINIMUM_VERSION.get(), "1.1.0")
        self.assertEqual(APP_LATEST_VERSION.get(), "1.4.0")
        self.assertIs(APP_MAINTENANCE.get(), True)
        self.assertEqual(APP_MAINTENANCE_MESSAGE.get(), "Volvemos a las 10")
        self.assertEqual(Preference.objects.filter(scope=Scope.PLATAFORMA).count(), 4)

    def test_rejects_versions_without_the_shape(self):
        errors = self.errors(self.post(app_version_minima="1.4", app_version_ultima="v2.0.0"))
        self.assertIn("id_app_version_minima", errors)
        self.assertIn("id_app_version_ultima", errors)
        self.assertFalse(Preference.objects.exists())

    def test_rejects_minimum_above_latest(self):
        errors = self.errors(self.post(app_version_minima="1.10.0", app_version_ultima="1.9.0"))
        self.assertIn("La versión mínima no puede ser mayor", errors["id_app_version_minima"])
        self.assertFalse(Preference.objects.exists())

    def test_allows_minimum_without_latest_and_equal_versions(self):
        self.assertEqual(self.post(app_version_minima="1.0.0", app_version_ultima="").status_code, 200)
        self.assertEqual(self.post(app_version_minima="1.2.0", app_version_ultima="1.2.0").status_code, 200)

    def test_only_changed_values_are_written(self):
        self.post()
        self.assertEqual(
            set(Preference.objects.values_list("key", flat=True)),
            {APP_MINIMUM_VERSION.key, APP_LATEST_VERSION.key},
        )
        response = self.post()
        self.assertEqual(response.json()["message"], "No hubo cambios que guardar.")
        self.assertEqual(Preference.history.count(), 2)

    def test_viewer_cannot_save(self):
        response = self.post(user=self.viewer)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Preference.objects.exists())

    def test_each_change_goes_to_the_history_with_author_and_reason(self):
        self.post()
        self.post(app_version_ultima="1.3.0", app_mantenimiento="on")
        data = self.history().json()
        self.assertEqual(data["recordsTotal"], 4)
        latest = data["data"][0]
        self.assertEqual(latest["author"], "Ana Rojas")
        self.assertEqual(latest["reason"], "Edición desde el panel")
        changes = [change for row in data["data"] for change in row["changes"]]
        self.assertIn({"field": "Última versión", "old": "1.2.0", "new": "1.3.0"}, changes)
        self.assertIn({"field": "Última versión", "old": "Sin registrar", "new": "1.2.0"}, changes)
        self.assertIn({"field": "Mantenimiento", "old": "Apagado", "new": "Encendido"}, changes)

    def test_history_modal_has_summary(self):
        self.post()
        response = self.browser().get(HISTORY_URL, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTemplateUsed(response, "panel/history_modal.html")
        self.assertContains(response, "Historial · App móvil")
        self.assertEqual(response.context["total"], 2)
        self.assertEqual(response.context["last_change"]["author"], "Ana Rojas")
        self.assertContains(response, f"url: '{HISTORY_LIST_URL}'")

    def test_history_ignores_other_preferences(self):
        Preference.objects.create(scope=Scope.USER, scope_id="1", key="calendario_vista_inicial", value="dia")
        self.post()
        self.assertEqual(self.history().json()["recordsTotal"], 2)

    def test_viewer_can_read_the_history(self):
        self.post()
        self.assertEqual(self.history(self.viewer).status_code, 200)

    def test_permission_matrix_has_the_section_with_view_and_change(self):
        row = next(row for row in build_permission_rows(set()) if row["label"] == "App móvil")
        self.assertEqual([cell["action"] if cell else None for cell in row["cells"]], ["Ver", None, "Editar", None])
