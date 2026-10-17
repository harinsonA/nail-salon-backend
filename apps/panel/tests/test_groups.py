from unittest import mock

from django.contrib.admin.models import DELETION, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name

from apps.panel.admin.group import GroupAdmin
from apps.tenancy.models import Dominio, Negocio

User = get_user_model()

PANEL = "admin.localhost"
LIST_URL = "/admin/auth/group/"
LIST_AJAX_URL = "/admin/auth/group/list/"


class GroupsScreenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
        cls.superuser = User.objects.create_superuser(username="admin", password="x")
        cls.support = Group.objects.create(name="Soporte")
        cls.billing = Group.objects.create(name="Cobranza")
        cls.support.permissions.add(*Permission.objects.filter(codename__in=["view_group", "view_user"]))
        cls.superuser.groups.add(cls.support)
        cls.viewer = User.objects.create_user(username="viewer", password="x", is_staff=True)
        cls.viewer.user_permissions.add(Permission.objects.get(codename="view_group"))
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

    def delete_modal_url(self, group):
        return f"/admin/auth/group/{group.pk}/delete/modal/"

    def test_menu_link_opens_the_panel_list(self):
        response = self.browser(self.superuser).get(LIST_URL)
        self.assertTemplateUsed(response, "panel/groups/list.html")
        self.assertTemplateUsed(response, "panel/base.html")
        self.assertContains(response, 'id="groups_table"')
        self.assertContains(response, f'url: \'{LIST_AJAX_URL}\'')
        self.assertContains(response, 'data-form-url="/admin/auth/group/add/modal/"')
        self.assertContains(response, 'id="modal"')
        self.assertContains(response, 'id="xl_modal"')

    def test_add_button_requires_add_permission(self):
        response = self.browser(self.viewer).get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "/admin/auth/group/add/modal/")

    def test_staff_without_permission_gets_forbidden(self):
        response = self.browser(self.staff).get(LIST_URL)
        self.assertContains(response, "No tienes permiso para esta acción del panel.", status_code=403)

    def test_list_returns_groups_with_counts_and_totals(self):
        payload = self.fetch(self.superuser).json()
        self.assertEqual(payload["recordsTotal"], 2)
        self.assertEqual(payload["total_groups"], 2)
        self.assertEqual(payload["groups_with_users"], 1)
        rows = {row["name"]: row for row in payload["data"]}
        self.assertEqual(rows["Soporte"]["permission_count"], 2)
        self.assertEqual(rows["Soporte"]["user_count"], 1)
        self.assertEqual(rows["Cobranza"]["user_count"], 0)

    def test_users_filter(self):
        with_users = self.fetch(self.superuser, users="with_users").json()["data"]
        without_users = self.fetch(self.superuser, users="without_users").json()["data"]
        self.assertEqual([row["name"] for row in with_users], ["Soporte"])
        self.assertEqual([row["name"] for row in without_users], ["Cobranza"])

    def test_search_by_name(self):
        payload = self.fetch(self.superuser, **{"search[value]": "cobr"}).json()
        self.assertEqual(payload["recordsFiltered"], 1)
        self.assertEqual(payload["data"][0]["name"], "Cobranza")

    def test_order_by_user_count(self):
        payload = self.fetch(self.superuser, **{"order[0][column]": "2", "order[0][dir]": "desc"}).json()
        self.assertEqual([row["name"] for row in payload["data"]], ["Soporte", "Cobranza"])

    def test_options_link_to_edit_form_and_delete_modal(self):
        row = next(row for row in self.fetch(self.superuser).json()["data"] if row["name"] == "Soporte")
        options = {option["label"]: option for option in row["options"]}
        self.assertEqual(options["Editar"]["link"], f"/admin/auth/group/{self.support.pk}/change/modal/")
        self.assertEqual(options["Editar"]["className"], "bs-xl-modal")
        self.assertEqual(options["Eliminar"]["link"], self.delete_modal_url(self.support))
        self.assertTrue(options["Eliminar"]["bsModal"])
        self.assertIn("bs-modal", options["Eliminar"]["className"])

    def test_options_follow_permissions(self):
        rows = self.fetch(self.viewer).json()["data"]
        self.assertTrue(all(row["options"] == [] for row in rows))

    def test_list_rejects_staff_without_permission(self):
        self.assertEqual(self.fetch(self.staff).status_code, 403)

    def test_list_without_session_answers_401(self):
        response = Client(HTTP_HOST=PANEL).get(LIST_AJAX_URL, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["redirect"], "/admin/login/")

    def test_old_django_pages_redirect_to_the_list(self):
        browser = self.browser(self.superuser)
        for url in ("/admin/auth/group/add/", f"/admin/auth/group/{self.support.pk}/change/",
                    f"/admin/auth/group/{self.support.pk}/", f"/admin/auth/group/{self.support.pk}/delete/"):
            with self.subTest(url=url):
                self.assertRedirects(browser.get(url, follow=True), LIST_URL)

    def test_posting_to_old_django_pages_changes_nothing(self):
        browser = self.browser(self.superuser)
        browser.post("/admin/auth/group/add/", {"name": "Ventas"})
        browser.post(f"/admin/auth/group/{self.support.pk}/delete/", {"post": "yes"})
        self.assertFalse(Group.objects.filter(name="Ventas").exists())
        self.assertTrue(Group.objects.filter(pk=self.support.pk).exists())

    def test_delete_modal_shows_the_group_details(self):
        response = self.browser(self.superuser).get(
            self.delete_modal_url(self.support), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertTemplateUsed(response, "common/delete_modal.html")
        self.assertContains(response, "Soporte")
        self.assertContains(response, f"ID: {self.support.pk}")
        self.assertContains(response, "Permisos: 2")
        self.assertContains(response, "Usuarios asignados: 1")

    def test_delete_modal_of_a_group_without_users_offers_the_deletion(self):
        response = self.browser(self.superuser).get(
            self.delete_modal_url(self.billing), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertContains(response, 'id="delete_submit_btn"')
        self.assertContains(response, "Esta acción es irreversible")
        self.assertNotContains(response, "No se puede eliminar")

    def test_deleting_removes_the_group_and_logs_it(self):
        response = self.browser(self.superuser).post(
            self.delete_modal_url(self.billing), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Grupo Cobranza eliminado exitosamente.")
        self.assertFalse(Group.objects.filter(pk=self.billing.pk).exists())
        log = LogEntry.objects.get(object_id=str(self.billing.pk), content_type__model="group")
        self.assertEqual((log.action_flag, log.object_repr, log.user_id), (DELETION, "Cobranza", self.superuser.pk))

    def test_a_group_with_users_cannot_be_deleted(self):
        message = "No se puede eliminar el grupo «Soporte»: tiene usuarios asignados. Primero quítalos del grupo."
        browser = self.browser(self.superuser)
        modal = browser.get(self.delete_modal_url(self.support), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertContains(modal, message)
        self.assertNotContains(modal, 'id="delete_submit_btn"')
        self.assertContains(modal, "Cerrar")
        response = browser.post(self.delete_modal_url(self.support), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], message)
        self.assertTrue(Group.objects.filter(pk=self.support.pk).exists())
        self.assertTrue(self.superuser.groups.filter(pk=self.support.pk).exists())
        self.assertFalse(LogEntry.objects.filter(object_id=str(self.support.pk), content_type__model="group").exists())

    def test_delete_requires_delete_permission(self):
        browser = self.browser(self.viewer)
        url = self.delete_modal_url(self.support)
        self.assertEqual(browser.get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest").status_code, 403)
        self.assertEqual(browser.post(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest").status_code, 403)
        self.assertTrue(Group.objects.filter(pk=self.support.pk).exists())

    def test_delete_without_session_answers_401(self):
        response = Client(HTTP_HOST=PANEL).post(
            self.delete_modal_url(self.support), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 401)
        self.assertTrue(Group.objects.filter(pk=self.support.pk).exists())

    def test_delete_of_a_missing_group_is_not_found(self):
        response = self.browser(self.superuser).get("/admin/auth/group/999999/delete/modal/")
        self.assertEqual(response.status_code, 404)

    def test_protected_relations_block_the_deletion(self):
        blocked = ([], {}, set(), ["registro protegido"])
        with mock.patch.object(GroupAdmin, "get_deleted_objects", return_value=blocked):
            response = self.browser(self.superuser).post(
                self.delete_modal_url(self.billing), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
            )
        self.assertEqual(response.status_code, 400)
        self.assertIn("No se puede eliminar «Cobranza»", response.json()["message"])
        self.assertTrue(Group.objects.filter(pk=self.billing.pk).exists())
