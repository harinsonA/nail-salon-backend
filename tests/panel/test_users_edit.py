import re

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import Dominio, Negocio
from tests.base import IDENTIFICADOR_VALIDO
from apps.panel.models import PerfilPanel

User = get_user_model()

PANEL = "admin.localhost"
LIST_URL = "/admin/auth/user/"


def permission(app_label, codename):
    return Permission.objects.get(content_type__app_label=app_label, codename=codename)


class UserUpdateModalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
        cls.superuser = User.objects.create_superuser(username="admin", password="Clave#123", email="admin@hiagenda.test")
        cls.other_superuser = User.objects.create_superuser(username="root", password="x", email="root@hiagenda.test")
        cls.support = Group.objects.create(name="Soporte")
        cls.support.permissions.add(permission("tenancy", "view_negocio"), permission("tenancy", "view_persona"))
        cls.sales = Group.objects.create(name="Ventas")
        cls.sales.permissions.add(permission("tenancy", "change_negocio"))
        cls.ana = User.objects.create_user(
            username="ana.rojas",
            password="Inicial#123",
            email="ana@hiagenda.test",
            first_name="Ana María",
            last_name="Rojas Pérez",
            is_staff=True,
        )
        cls.ana.groups.add(cls.support)
        cls.ana.user_permissions.add(
            permission("tenancy", "view_rubro"),
            permission("tenancy", "view_negocio"),
            permission("clients", "view_cliente"),
        )
        cls.viewer = User.objects.create_user(username="viewer", password="x", is_staff=True)
        cls.viewer.user_permissions.add(permission("auth", "view_user"))
        cls.manager = User.objects.create_user(username="manager", password="x", is_staff=True)
        cls.manager.user_permissions.add(permission("auth", "view_user"), permission("auth", "change_user"))

    def setUp(self):
        connection.set_schema_to_public()

    def browser(self, user=None):
        browser = Client(HTTP_HOST=PANEL)
        if user:
            browser.force_login(user)
        return browser

    def url(self, user):
        return f"/admin/auth/user/{user.pk}/change/modal/"

    def payload(self, user=None, **changes):
        user = user or self.ana
        data = {
            **IDENTIFICADOR_VALIDO,
            "username": user.username,
            "first_name": user.first_name.partition(" ")[0] or "Prueba",
            "second_name": user.first_name.partition(" ")[2],
            "first_surname": user.last_name.partition(" ")[0] or "Prueba",
            "second_surname": user.last_name.partition(" ")[2],
            "email": user.email or f"{user.username}@hiagenda.test",
            "is_active": "on" if user.is_active else None,
            "is_staff": "on" if user.is_staff else None,
            "is_superuser": "on" if user.is_superuser else None,
            "groups": [str(group.pk) for group in user.groups.all()],
            "user_permissions": [],
            "password": "",
            "password_confirmation": "",
        }
        data.update(changes)
        return {key: value for key, value in data.items() if value is not None}

    def submit(self, editor=None, user=None, **changes):
        user = user or self.ana
        return self.browser(editor or self.superuser).post(
            self.url(user), self.payload(user, **changes), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def modal(self, editor=None, user=None):
        return self.browser(editor or self.superuser).get(
            self.url(user or self.ana), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def errors(self, response):
        self.assertEqual(response.status_code, 400)
        return {error["id_element"]: error["error"] for error in response.json()["errors"]}

    def reload(self, user):
        return User.objects.get(pk=user.pk)

    def test_modal_has_three_tabs_and_the_dates(self):
        response = self.modal()
        self.assertTemplateUsed(response, "panel/users/user_edit_modal.html")
        for tab in ("user-tab-basic", "user-tab-password", "user-tab-permissions"):
            with self.subTest(tab=tab):
                self.assertContains(response, f'id="{tab}"')
        self.assertContains(response, "Fecha de alta")
        self.assertContains(response, "Último acceso")
        self.assertContains(response, 'id="user-group-permissions"')

    def test_names_are_split_into_the_four_fields(self):
        html = self.modal().content.decode()
        for name, value in (("first_name", "Ana"), ("second_name", "María"), ("first_surname", "Rojas"),
                            ("second_surname", "Pérez")):
            with self.subTest(name=name):
                self.assertRegex(html, rf'name="{name}" value="{value}"')

    def test_permission_table_only_lists_panel_permissions(self):
        html = self.modal().content.decode()
        self.assertEqual(len(re.findall(r'name="user_permissions"', html)), 20)
        self.assertNotIn(f'value="{permission("clients", "view_cliente").pk}"', html)

    def test_permissions_from_groups_are_marked(self):
        html = self.modal().content.decode()
        inherited = re.search(rf'value="{permission("tenancy", "view_persona").pk}"[^>]*>', html).group(0)
        direct = re.search(rf'value="{permission("tenancy", "view_rubro").pk}"[^>]*>', html).group(0)
        self.assertIn("disabled", inherited)
        self.assertIn("checked", direct)
        self.assertNotIn("disabled", direct)

    def test_updates_the_basic_data_and_logs_the_change(self):
        response = self.submit(username="ana.perez", second_name="", second_surname="", email="ANA.P@hiagenda.test")
        self.assertEqual(response.json()["message"], "Usuario ana.perez actualizado exitosamente.")
        ana = self.reload(self.ana)
        self.assertEqual((ana.username, ana.first_name, ana.last_name, ana.email),
                         ("ana.perez", "Ana", "Rojas", "ana.p@hiagenda.test"))
        log = LogEntry.objects.filter(object_id=str(ana.pk), content_type__model="user").latest("action_time")
        self.assertEqual(log.action_flag, CHANGE)
        self.assertIn("Usuario", log.get_change_message())

    def test_keeping_the_same_username_and_email_is_allowed(self):
        self.assertEqual(self.submit().status_code, 200)

    def test_username_and_email_stay_unique(self):
        errors = self.errors(self.submit(username="ROOT", email="root@hiagenda.test"))
        self.assertIn("minúsculas", errors["id_username"])
        self.assertEqual(errors["id_email"], "Ese correo ya lo usa otro usuario del panel.")
        self.assertEqual(self.errors(self.submit(username="root"))["id_username"], "Ese usuario ya existe en el panel.")

    def test_empty_password_keeps_the_current_one(self):
        self.submit()
        self.assertTrue(self.reload(self.ana).check_password("Inicial#123"))

    def test_changes_the_password_with_the_policy(self):
        self.submit(password="Nueva#456", password_confirmation="Nueva#456")
        self.assertTrue(self.reload(self.ana).check_password("Nueva#456"))

    def test_password_rules_and_confirmation(self):
        self.assertIn("3 números", self.errors(self.submit(password="Nueva#45x", password_confirmation="Nueva#45x"))["id_password"])
        self.assertEqual(
            self.errors(self.submit(password="Nueva#456", password_confirmation="Nueva#457"))["id_password_confirmation"],
            "Las contraseñas no coinciden.",
        )
        self.assertIn("id_password_confirmation", self.errors(self.submit(password="Nueva#456")))
        self.assertIn("id_password", self.errors(self.submit(password_confirmation="Nueva#456")))
        self.assertTrue(self.reload(self.ana).check_password("Inicial#123"))

    def test_changing_your_own_password_keeps_you_signed_in(self):
        browser = self.browser(self.superuser)
        response = browser.post(
            self.url(self.superuser),
            self.payload(self.superuser, password="Nueva#456", password_confirmation="Nueva#456"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(browser.get(LIST_URL).status_code, 200)

    def test_saves_groups_and_panel_permissions_keeping_the_rest(self):
        add_rubro = permission("tenancy", "add_rubro")
        self.submit(groups=[str(self.sales.pk), str(self.support.pk)], user_permissions=[str(add_rubro.pk)])
        ana = self.reload(self.ana)
        self.assertEqual(set(ana.groups.all()), {self.sales, self.support})
        self.assertEqual(
            set(ana.user_permissions.all()),
            {add_rubro, permission("tenancy", "view_negocio"), permission("clients", "view_cliente")},
        )

    def test_superuser_forces_panel_access(self):
        self.submit(is_staff=None, is_superuser="on")
        ana = self.reload(self.ana)
        self.assertTrue(ana.is_superuser and ana.is_staff)

    def test_your_own_account_keeps_its_status_access_and_permissions(self):
        self.submit(user=self.superuser, is_active=None, is_staff=None, is_superuser=None,
                    groups=[str(self.sales.pk)], first_name="Admin")
        admin = self.reload(self.superuser)
        self.assertEqual((admin.is_active, admin.is_staff, admin.is_superuser), (True, True, True))
        self.assertFalse(admin.groups.exists())
        self.assertEqual(admin.first_name, "Admin")

    def test_your_own_account_shows_its_switches_disabled(self):
        html = self.modal(user=self.superuser).content.decode()
        self.assertRegex(html, r'name="is_active"[^>]*disabled')
        self.assertRegex(html, r'name="is_superuser"[^>]*disabled')
        self.assertIn("Es tu propia cuenta", html)

    def test_only_superusers_change_who_is_superuser(self):
        self.submit(editor=self.manager, is_superuser="on")
        self.assertFalse(self.reload(self.ana).is_superuser)
        self.assertRegex(self.modal(editor=self.manager).content.decode(), r'name="is_superuser"[^>]*disabled')

    def test_non_superusers_cannot_edit_superusers(self):
        self.assertEqual(self.modal(editor=self.manager, user=self.other_superuser).status_code, 403)
        rows = self.browser(self.manager).get(
            "/admin/auth/user/list/", {"draw": 1, "start": 0, "length": 10}, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        ).json()["data"]
        root = next(row for row in rows if row["username"] == "root")
        self.assertNotIn("Editar", [option["label"] for option in root["options"]])

    def test_superuser_notice_is_shown_for_superusers(self):
        html = self.modal(user=self.other_superuser).content.decode()
        self.assertRegex(html, r'class="[^"]*superuser-notice(?![^"]*d-none)[^"]*"')

    def test_requires_change_permission_and_a_session(self):
        self.assertEqual(self.modal(editor=self.viewer).status_code, 403)
        self.assertEqual(self.submit(editor=self.viewer, first_name="Otra").status_code, 403)
        response = self.browser().get(self.url(self.ana), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.browser(self.superuser).get("/admin/auth/user/999999/change/modal/").status_code, 404)
        self.assertEqual(self.reload(self.ana).first_name, "Ana María")

    def test_old_django_pages_redirect_to_the_list(self):
        browser = self.browser(self.superuser)
        for url in (f"/admin/auth/user/{self.ana.pk}/change/", f"/admin/auth/user/{self.ana.pk}/password/",
                    f"/admin/auth/user/{self.ana.pk}/delete/", "/admin/auth/user/add/"):
            with self.subTest(url=url):
                self.assertRedirects(browser.get(url), LIST_URL, fetch_redirect_response=False)

    def test_posting_to_the_old_delete_page_deletes_nothing(self):
        response = self.browser(self.superuser).post(f"/admin/auth/user/{self.ana.pk}/delete/", {"post": "yes"})
        self.assertRedirects(response, LIST_URL, fetch_redirect_response=False)
        self.assertTrue(User.objects.filter(pk=self.ana.pk).exists())

    def test_loads_and_updates_the_national_identifier(self):
        PerfilPanel.objects.create(
            user=self.ana, pais="MX", tipo_identificador_nacional="curp",
            identificador_nacional="BOXW310820HNERXN09",
        )
        html = self.modal().content.decode()
        self.assertRegex(html, r'<option value="curp" selected>CURP</option>')
        self.assertEqual(self.submit().status_code, 200)
        perfil = PerfilPanel.objects.get(user=self.ana)
        self.assertEqual(
            (perfil.pais, perfil.identificador_nacional), ("CL", "12345678-5")
        )

    def test_a_user_without_panel_profile_gets_one_when_saved(self):
        self.assertFalse(PerfilPanel.objects.filter(user=self.ana).exists())
        self.assertEqual(self.submit().status_code, 200)
        self.assertEqual(PerfilPanel.objects.get(user=self.ana).tipo_identificador_nacional, "rut")

    def test_saving_without_changes_does_not_add_history(self):
        self.submit()
        perfil = PerfilPanel.objects.get(user=self.ana)
        self.submit()
        self.assertEqual(perfil.history.count(), 1)

    def test_the_identifier_cannot_be_left_empty(self):
        errors = self.errors(
            self.submit(national_id_country="", national_id_type="", national_id="")
        )
        self.assertIn("id_national_id_country", errors)
