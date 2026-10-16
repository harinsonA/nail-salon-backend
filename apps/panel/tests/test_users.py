from unittest import mock

from django.contrib.admin.models import DELETION, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name

from apps.panel.admin.user import UserAdmin
from apps.tenancy.models import Dominio, Negocio

User = get_user_model()

PANEL = "admin.localhost"
LIST_URL = "/admin/auth/user/"
LIST_AJAX_URL = "/admin/auth/user/list/"


class UsersScreenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
        cls.support = Group.objects.create(name="Soporte")
        cls.superuser = User.objects.create_superuser(
            username="admin", password="x", email="admin@hiagenda.cl", first_name="Ana", last_name="Rojas"
        )
        cls.viewer = User.objects.create_user(username="viewer", password="x", is_staff=True)
        cls.viewer.user_permissions.add(Permission.objects.get(codename="view_user"))
        cls.viewer.groups.add(cls.support)
        cls.retired = User.objects.create_user(username="retired", password="x", is_active=False)
        cls.staff = User.objects.create_user(username="staff", password="x", is_staff=True)

    def setUp(self):
        connection.set_schema_to_public()

    def browser(self, user):
        browser = Client(HTTP_HOST=PANEL)
        browser.force_login(user)
        return browser

    def fetch(self, user, **params):
        query = {"draw": 1, "start": 0, "length": 10, "order[0][column]": "0", "order[0][dir]": "asc", **params}
        return self.browser(user).get(LIST_AJAX_URL, query, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def usernames(self, user, **params):
        return [row["username"] for row in self.fetch(user, **params).json()["data"]]

    def delete_modal_url(self, user):
        return f"/admin/auth/user/{user.pk}/delete/modal/"

    def test_menu_link_opens_the_panel_list(self):
        response = self.browser(self.superuser).get(LIST_URL)
        self.assertTemplateUsed(response, "panel/users/list.html")
        self.assertContains(response, 'id="users_table"')
        self.assertContains(response, f'url: \'{LIST_AJAX_URL}\'')
        self.assertContains(response, 'data-form-url="/admin/auth/user/add/modal/"')
        self.assertContains(response, 'id="id_group"')

    def test_add_button_requires_add_permission(self):
        response = self.browser(self.viewer).get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "/admin/auth/user/add/modal/")

    def test_staff_without_permission_gets_forbidden(self):
        response = self.browser(self.staff).get(LIST_URL)
        self.assertContains(response, "No tienes permiso para esta acción del panel.", status_code=403)

    def test_list_returns_users_and_totals(self):
        payload = self.fetch(self.superuser).json()
        self.assertEqual(payload["recordsTotal"], 4)
        self.assertEqual((payload["total_users"], payload["active_users"], payload["staff_users"]), (4, 3, 3))
        admin_row = next(row for row in payload["data"] if row["username"] == "admin")
        self.assertEqual(admin_row["full_name"], "Ana Rojas")
        self.assertEqual(admin_row["email"], "admin@hiagenda.cl")
        self.assertTrue(admin_row["is_superuser"])
        self.assertEqual(next(row for row in payload["data"] if row["username"] == "retired")["last_login"], "—")

    def test_status_filter(self):
        self.assertEqual(self.usernames(self.superuser, status="inactive"), ["retired"])
        self.assertNotIn("retired", self.usernames(self.superuser, status="active"))

    def test_role_filter(self):
        self.assertEqual(self.usernames(self.superuser, role="superuser"), ["admin"])
        self.assertEqual(self.usernames(self.superuser, role="staff"), ["staff", "viewer"])
        self.assertEqual(self.usernames(self.superuser, role="no_panel"), ["retired"])

    def test_group_filter(self):
        self.assertEqual(self.usernames(self.superuser, group=self.support.pk), ["viewer"])

    def test_search_by_name_and_email(self):
        self.assertEqual(self.usernames(self.superuser, **{"search[value]": "rojas"}), ["admin"])
        self.assertEqual(self.usernames(self.superuser, **{"search[value]": "hiagenda"}), ["admin"])

    def test_options_link_to_edit_form_and_delete_modal(self):
        row = next(row for row in self.fetch(self.superuser).json()["data"] if row["username"] == "retired")
        options = {option["label"]: option for option in row["options"]}
        self.assertEqual(options["Editar"]["link"], f"/admin/auth/user/{self.retired.pk}/change/modal/")
        self.assertEqual(options["Editar"]["className"], "bs-xl-modal")
        self.assertEqual(options["Eliminar"]["link"], self.delete_modal_url(self.retired))
        self.assertTrue(options["Eliminar"]["bsModal"])

    def test_own_row_has_no_delete_option(self):
        row = next(row for row in self.fetch(self.superuser).json()["data"] if row["username"] == "admin")
        self.assertEqual([option["label"] for option in row["options"]], ["Editar"])

    def test_options_follow_permissions(self):
        rows = self.fetch(self.viewer).json()["data"]
        self.assertTrue(all(row["options"] == [] for row in rows))

    def test_list_without_session_answers_401(self):
        response = Client(HTTP_HOST=PANEL).get(LIST_AJAX_URL, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 401)

    def test_django_add_page_redirects_to_the_list(self):
        response = self.browser(self.superuser).get("/admin/auth/user/add/")
        self.assertRedirects(response, LIST_URL, fetch_redirect_response=False)

    def test_delete_modal_shows_the_user_details(self):
        response = self.browser(self.superuser).get(
            self.delete_modal_url(self.viewer), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertTemplateUsed(response, "common/delete_modal.html")
        self.assertContains(response, "Nombre: viewer")
        self.assertContains(response, "Grupos: 1")
        self.assertContains(response, "Último acceso: —")

    def test_deleting_removes_the_user_and_logs_it(self):
        response = self.browser(self.superuser).post(
            self.delete_modal_url(self.retired), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.json()["message"], "Usuario retired eliminado exitosamente.")
        self.assertFalse(User.objects.filter(pk=self.retired.pk).exists())
        log = LogEntry.objects.get(object_id=str(self.retired.pk), content_type__model="user")
        self.assertEqual((log.action_flag, log.user_id), (DELETION, self.superuser.pk))

    def test_nobody_deletes_their_own_account(self):
        response = self.browser(self.superuser).post(
            self.delete_modal_url(self.superuser), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "No puedes eliminar tu propia cuenta.")
        self.assertTrue(User.objects.filter(pk=self.superuser.pk).exists())

    def test_delete_requires_delete_permission(self):
        response = self.browser(self.viewer).post(
            self.delete_modal_url(self.retired), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(User.objects.filter(pk=self.retired.pk).exists())

    def test_protected_relations_block_the_deletion(self):
        blocked = ([], {}, set(), ["registro protegido"])
        with mock.patch.object(UserAdmin, "get_deleted_objects", return_value=blocked):
            response = self.browser(self.superuser).post(
                self.delete_modal_url(self.retired), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
            )
        self.assertEqual(response.status_code, 400)
        self.assertTrue(User.objects.filter(pk=self.retired.pk).exists())
