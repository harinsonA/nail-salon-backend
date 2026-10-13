from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name

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

    def test_menu_link_opens_the_panel_list(self):
        response = self.browser(self.superuser).get(LIST_URL)
        self.assertTemplateUsed(response, "panel/groups/list.html")
        self.assertTemplateUsed(response, "panel/base.html")
        self.assertContains(response, 'id="groups_table"')
        self.assertContains(response, f'url: \'{LIST_AJAX_URL}\'')
        self.assertContains(response, 'href="/admin/auth/group/add/"')

    def test_add_button_requires_add_permission(self):
        response = self.browser(self.viewer).get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "/admin/auth/group/add/")

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

    def test_options_link_to_django_forms(self):
        row = next(row for row in self.fetch(self.superuser).json()["data"] if row["name"] == "Soporte")
        links = {option["label"]: option["link"] for option in row["options"]}
        self.assertEqual(links["Editar"], f"/admin/auth/group/{self.support.pk}/change/")
        self.assertEqual(links["Eliminar"], f"/admin/auth/group/{self.support.pk}/delete/")

    def test_options_follow_permissions(self):
        rows = self.fetch(self.viewer).json()["data"]
        self.assertTrue(all(row["options"] == [] for row in rows))

    def test_list_rejects_staff_without_permission(self):
        self.assertEqual(self.fetch(self.staff).status_code, 403)

    def test_list_without_session_answers_401(self):
        response = Client(HTTP_HOST=PANEL).get(LIST_AJAX_URL, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["redirect"], "/admin/login/")

    def test_add_form_is_still_the_django_one(self):
        response = self.browser(self.superuser).get("/admin/auth/group/add/")
        self.assertTemplateUsed(response, "admin/change_form.html")

    def test_saving_a_group_returns_to_the_panel_list(self):
        response = self.browser(self.superuser).post("/admin/auth/group/add/", {"name": "Ventas"})
        self.assertRedirects(response, LIST_URL, fetch_redirect_response=False)
        self.assertTrue(Group.objects.filter(name="Ventas").exists())
