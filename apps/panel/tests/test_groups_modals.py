import re

from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import Dominio, Negocio

User = get_user_model()

PANEL = "admin.localhost"
CREATE_URL = "/admin/auth/group/add/modal/"


def permission(app_label, codename):
    return Permission.objects.get(content_type__app_label=app_label, codename=codename)


class GroupModalsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
        cls.superuser = User.objects.create_superuser(username="admin", password="x")
        cls.support = Group.objects.create(name="Soporte")
        cls.support.permissions.add(permission("tenancy", "view_negocio"), permission("clients", "view_cliente"))
        cls.support.user_set.add(cls.superuser)
        cls.billing = Group.objects.create(name="Cobranza")
        cls.viewer = User.objects.create_user(username="viewer", password="x", is_staff=True)
        cls.viewer.user_permissions.add(permission("auth", "view_group"))

    def setUp(self):
        connection.set_schema_to_public()

    def browser(self, user=None):
        browser = Client(HTTP_HOST=PANEL)
        if user:
            browser.force_login(user)
        return browser

    def edit_url(self, group):
        return f"/admin/auth/group/{group.pk}/change/modal/"

    def post(self, url, user=None, **data):
        return self.browser(user or self.superuser).post(url, data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def get(self, url, user=None):
        return self.browser(user or self.superuser).get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def errors(self, response):
        self.assertEqual(response.status_code, 400)
        return {error["id_element"]: error["error"] for error in response.json()["errors"]}

    def test_create_modal_shows_name_and_permission_table(self):
        response = self.get(CREATE_URL)
        self.assertTemplateUsed(response, "panel/groups/group_modal.html")
        self.assertTemplateUsed(response, "panel/permission_matrix.html")
        html = response.content.decode()
        self.assertIn("Nuevo grupo", html)
        self.assertIn('id="id_name"', html)
        self.assertEqual(len(re.findall(r'name="permissions"', html)), 20)
        self.assertNotIn("Usuarios asignados", html)

    def test_creates_a_group_with_panel_permissions(self):
        view_rubro = permission("tenancy", "view_rubro")
        response = self.post(CREATE_URL, name="  Ventas   zona  norte ", permissions=[str(view_rubro.pk)])
        self.assertEqual(response.json()["message"], "Grupo Ventas zona norte creado exitosamente.")
        group = Group.objects.get(name="Ventas zona norte")
        self.assertEqual(list(group.permissions.all()), [view_rubro])
        log = LogEntry.objects.get(object_id=str(group.pk), content_type__model="group")
        self.assertEqual(log.action_flag, ADDITION)

    def test_name_rules(self):
        cases = {
            "": "requerido",
            "ab": "entre 3 y 80",
            "a" * 81: "entre 3 y 80",
            "-Soporte": "debe empezar con una letra o un número",
            "Soporte@": "solo admite",
            "soporte": "Ya existe un grupo con ese nombre.",
        }
        for name, message in cases.items():
            with self.subTest(name=name):
                self.assertIn(message, self.errors(self.post(CREATE_URL, name=name))["id_name"])

    def test_edit_modal_loads_the_group(self):
        html = self.get(self.edit_url(self.support)).content.decode()
        self.assertIn("Editar grupo · Soporte", html)
        self.assertRegex(html, r'name="name" value="Soporte"')
        checkbox = re.search(rf'value="{permission("tenancy", "view_negocio").pk}"[^>]*>', html).group(0)
        self.assertIn("checked", checkbox)
        self.assertIn("Usuarios asignados", html)

    def test_edits_name_and_permissions_keeping_the_rest(self):
        add_rubro = permission("tenancy", "add_rubro")
        response = self.post(self.edit_url(self.support), name="Soporte técnico", permissions=[str(add_rubro.pk)])
        self.assertEqual(response.json()["message"], "Grupo Soporte técnico actualizado exitosamente.")
        support = Group.objects.get(pk=self.support.pk)
        self.assertEqual(support.name, "Soporte técnico")
        self.assertEqual(set(support.permissions.all()), {add_rubro, permission("clients", "view_cliente")})
        self.assertTrue(support.user_set.filter(pk=self.superuser.pk).exists())
        log = LogEntry.objects.filter(object_id=str(support.pk), content_type__model="group").latest("action_time")
        self.assertEqual(log.action_flag, CHANGE)

    def test_keeping_the_same_name_is_allowed_but_not_another_groups(self):
        self.assertEqual(self.post(self.edit_url(self.support), name="Soporte").status_code, 200)
        errors = self.errors(self.post(self.edit_url(self.support), name="cobranza"))
        self.assertEqual(errors["id_name"], "Ya existe un grupo con ese nombre.")

    def test_requires_add_and_change_permissions(self):
        self.assertEqual(self.get(CREATE_URL, user=self.viewer).status_code, 403)
        self.assertEqual(self.post(CREATE_URL, user=self.viewer, name="Ventas").status_code, 403)
        self.assertEqual(self.get(self.edit_url(self.support), user=self.viewer).status_code, 403)
        self.assertEqual(self.post(self.edit_url(self.support), user=self.viewer, name="Otro").status_code, 403)
        self.assertFalse(Group.objects.filter(name__in=["Ventas", "Otro"]).exists())

    def test_without_session_answers_401_and_missing_group_404(self):
        response = self.browser().post(CREATE_URL, {"name": "Ventas"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get("/admin/auth/group/999999/change/modal/").status_code, 404)
