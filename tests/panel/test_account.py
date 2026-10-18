from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import connection
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import Dominio, Negocio

User = get_user_model()

PANEL = "admin.localhost"
PROFILE_URL = "/admin/account/modal/"


class AccountModalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
        cls.support = Group.objects.create(name="Soporte")
        cls.ana = User.objects.create_user(
            username="ana.rojas",
            password="Inicial#123",
            email="ana@hiagenda.test",
            first_name="Ana",
            last_name="Rojas",
            is_staff=True,
        )
        cls.other = User.objects.create_user(username="otro", password="x", email="otro@hiagenda.test", is_staff=True)

    def setUp(self):
        connection.set_schema_to_public()
        self.browser = Client(HTTP_HOST=PANEL)
        self.browser.force_login(self.ana)

    def payload(self, **changes):
        data = {
            "username": "ana.rojas",
            "first_name": "Ana",
            "first_surname": "Rojas",
            "email": "ana@hiagenda.test",
            "password": "",
            "password_confirmation": "",
        }
        data.update(changes)
        return data

    def post(self, **changes):
        return self.browser.post(PROFILE_URL, self.payload(**changes), HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def test_staff_without_user_permissions_opens_their_own_profile(self):
        response = self.browser.get(PROFILE_URL, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTemplateUsed(response, "panel/users/user_edit_modal.html")
        html = response.content.decode()
        self.assertIn("Editar usuario · ana.rojas", html)
        self.assertIn(f'action="{PROFILE_URL}"', html)
        self.assertIn("Es tu propia cuenta", html)
        for field in ("is_active", "is_staff", "is_superuser", "groups"):
            self.assertRegex(html, rf'name="{field}"[^>]*disabled')
        self.assertNotIn("otro@hiagenda.test", html)

    def test_updates_own_data_and_keeps_the_session_after_a_new_password(self):
        response = self.post(second_name="María", password="Nueva#4567", password_confirmation="Nueva#4567")
        self.assertEqual(response.json()["message"], "Tu perfil se actualizó exitosamente.")
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.first_name, "Ana María")
        self.assertTrue(self.ana.check_password("Nueva#4567"))
        self.assertEqual(self.browser.get("/admin/").status_code, 200)
        log = LogEntry.objects.get(object_id=str(self.ana.pk), content_type__model="user")
        self.assertEqual((log.action_flag, log.user_id), (CHANGE, self.ana.pk))

    def test_cannot_grant_itself_access_or_permissions(self):
        response = self.post(
            is_superuser="on",
            groups=[str(self.support.pk)],
            user_permissions=[str(Permission.objects.get(codename="change_user").pk)],
        )
        self.assertEqual(response.status_code, 200)
        self.ana.refresh_from_db()
        self.assertFalse(self.ana.is_superuser)
        self.assertFalse(self.ana.groups.exists())
        self.assertFalse(self.ana.user_permissions.exists())
        self.assertTrue(self.ana.is_active and self.ana.is_staff)

    def test_validates_like_the_user_edit_modal(self):
        response = self.post(email="otro@hiagenda.test", password="corta", password_confirmation="corta")
        self.assertEqual(response.status_code, 400)
        errors = {error["id_element"] for error in response.json()["errors"]}
        self.assertEqual(errors, {"id_email", "id_password"})
        self.ana.refresh_from_db()
        self.assertTrue(self.ana.check_password("Inicial#123"))

    def test_only_edits_the_account_in_session(self):
        self.post(username="ana.rojas", first_name="Anita")
        self.other.refresh_from_db()
        self.assertEqual(self.other.username, "otro")
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.first_name, "Anita")

    def test_without_session_answers_401(self):
        response = Client(HTTP_HOST=PANEL).post(PROFILE_URL, self.payload(), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 401)

    def test_django_password_change_pages_redirect_to_the_panel(self):
        for url in ("/admin/password_change/", "/admin/password_change/done/"):
            with self.subTest(url=url):
                self.assertRedirects(self.browser.get(url), "/admin/")
        self.browser.post("/admin/password_change/", {"old_password": "Inicial#123", "new_password1": "Otra#4567", "new_password2": "Otra#4567"})
        self.ana.refresh_from_db()
        self.assertTrue(self.ana.check_password("Inicial#123"))
