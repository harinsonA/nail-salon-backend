from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import Dominio, Negocio
from tests.base import IDENTIFICADOR_VALIDO
from apps.panel.models import PerfilPanel

User = get_user_model()

PANEL = "admin.localhost"
MODAL_URL = "/admin/auth/user/add/modal/"


class UserCreateModalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
        cls.superuser = User.objects.create_superuser(username="admin", password="x", email="admin@hiagenda.test")
        cls.viewer = User.objects.create_user(username="viewer", password="x", is_staff=True)
        cls.viewer.user_permissions.add(Permission.objects.get(codename="view_user"))

    def setUp(self):
        connection.set_schema_to_public()

    def browser(self, user=None):
        browser = Client(HTTP_HOST=PANEL)
        if user:
            browser.force_login(user)
        return browser

    def payload(self, **changes):
        data = {
            **IDENTIFICADOR_VALIDO,
            "username": "ana.rojas",
            "password": "Clave#123",
            "password_confirmation": "Clave#123",
            "first_name": "Ana",
            "second_name": "María",
            "first_surname": "Rojas",
            "second_surname": "Pérez",
            "email": "Ana.Rojas@HiAgenda.test",
            "is_active": "on",
            "is_staff": "on",
        }
        data.update(changes)
        return {key: value for key, value in data.items() if value is not None}

    def submit(self, user=None, **changes):
        return self.browser(user or self.superuser).post(
            MODAL_URL, self.payload(**changes), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def errors(self, response):
        self.assertEqual(response.status_code, 400)
        return {error["id_element"]: error["error"] for error in response.json()["errors"]}

    def test_modal_shows_the_form(self):
        response = self.browser(self.superuser).get(MODAL_URL, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTemplateUsed(response, "panel/users/user_modal.html")
        for field in ("username", "password", "password_confirmation", "first_name", "second_name",
                      "first_surname", "second_surname", "email", "is_active", "is_staff", "is_superuser"):
            with self.subTest(field=field):
                self.assertContains(response, f'id="id_{field}"')
        self.assertContains(response, 'id="user_submit_btn"')
        self.assertContains(response, f'action="{MODAL_URL}"')

    def test_switches_start_with_active_and_staff_on_and_superuser_off(self):
        html = self.browser(self.superuser).get(MODAL_URL, HTTP_X_REQUESTED_WITH="XMLHttpRequest").content.decode()
        self.assertRegex(html, r'name="is_active"[^>]*checked')
        self.assertRegex(html, r'name="is_staff"[^>]*checked')
        self.assertNotRegex(html, r'name="is_superuser"[^>]*checked')

    def test_creates_the_user_with_joined_names_and_hashed_password(self):
        response = self.submit()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Usuario ana.rojas creado exitosamente.")
        user = User.objects.get(username="ana.rojas")
        self.assertEqual((user.first_name, user.last_name), ("Ana María", "Rojas Pérez"))
        self.assertEqual(user.email, "ana.rojas@hiagenda.test")
        self.assertTrue(user.check_password("Clave#123"))
        self.assertNotEqual(user.password, "Clave#123")
        self.assertEqual((user.is_active, user.is_staff, user.is_superuser), (True, True, False))

    def test_second_name_and_surname_are_optional(self):
        self.submit(second_name="", second_surname="")
        user = User.objects.get(username="ana.rojas")
        self.assertEqual((user.first_name, user.last_name), ("Ana", "Rojas"))

    def test_superuser_always_gets_panel_access(self):
        self.submit(is_staff=None, is_superuser="on")
        user = User.objects.get(username="ana.rojas")
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)

    def test_switches_can_be_turned_off(self):
        self.submit(is_active=None, is_staff=None)
        user = User.objects.get(username="ana.rojas")
        self.assertEqual((user.is_active, user.is_staff), (False, False))

    def test_creation_is_logged_in_the_admin_history(self):
        self.submit()
        user = User.objects.get(username="ana.rojas")
        log = LogEntry.objects.get(object_id=str(user.pk), content_type__model="user")
        self.assertEqual((log.action_flag, log.user_id), (ADDITION, self.superuser.pk))

    def test_username_rules(self):
        cases = {
            "Ana.Rojas": "minúsculas",
            "ab": "entre 3 y 30",
            "1ana": "debe empezar con una letra",
            "ana rojas": "debe empezar con una letra",
            "ADMIN": "minúsculas",
        }
        for username, message in cases.items():
            with self.subTest(username=username):
                self.assertIn(message, self.errors(self.submit(username=username))["id_username"])

    def test_username_is_unique_ignoring_case(self):
        User.objects.create_user(username="ana.rojas", password="x", email="otra@hiagenda.test")
        self.assertEqual(self.errors(self.submit())["id_username"], "Ese usuario ya existe en el panel.")

    def test_email_is_required_and_unique_ignoring_case(self):
        self.assertIn("id_email", self.errors(self.submit(email="")))
        self.assertEqual(
            self.errors(self.submit(email="ADMIN@hiagenda.test"))["id_email"],
            "Ese correo ya lo usa otro usuario del panel.",
        )

    def test_password_rules(self):
        cases = {
            "Ab#1234": "entre 8 y 20",
            "Abcdefgh#123456789012": "entre 8 y 20",
            "clave#123": "1 mayúscula",
            "Clave#12x": "3 números",
            "Clave1234": "1 carácter especial",
        }
        for password, message in cases.items():
            with self.subTest(password=password):
                response = self.submit(password=password, password_confirmation=password)
                self.assertIn(message, self.errors(response)["id_password"])
        self.assertFalse(User.objects.filter(username="ana.rojas").exists())

    def test_password_cannot_resemble_the_user(self):
        response = self.submit(password="Ana.Rojas#123", password_confirmation="Ana.Rojas#123")
        self.assertIn("id_password", self.errors(response))

    def test_password_confirmation_must_match(self):
        response = self.submit(password_confirmation="Clave#124")
        self.assertEqual(self.errors(response)["id_password_confirmation"], "Las contraseñas no coinciden.")

    def test_names_only_accept_letters_and_spaces(self):
        errors = self.errors(self.submit(first_name="Ana1", second_surname="Pérez!"))
        self.assertIn("primer nombre", errors["id_first_name"])
        self.assertIn("segundo apellido", errors["id_second_surname"])

    def test_first_name_and_surname_are_required(self):
        errors = self.errors(self.submit(first_name="", first_surname="   "))
        self.assertIn("id_first_name", errors)
        self.assertIn("id_first_surname", errors)

    def test_requires_add_permission(self):
        self.assertEqual(self.browser(self.viewer).get(MODAL_URL, HTTP_X_REQUESTED_WITH="XMLHttpRequest").status_code, 403)
        self.assertEqual(self.submit(user=self.viewer).status_code, 403)
        self.assertFalse(User.objects.filter(username="ana.rojas").exists())

    def test_without_session_answers_401(self):
        response = self.browser().post(MODAL_URL, self.payload(), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 401)
        self.assertFalse(User.objects.filter(username="ana.rojas").exists())

    def test_the_national_identifier_is_mandatory(self):
        errors = self.errors(
            self.submit(national_id_country="", national_id_type="", national_id="")
        )
        for field in ("id_national_id_country", "id_national_id_type", "id_national_id"):
            self.assertIn(field, errors)
        self.assertFalse(User.objects.filter(username="ana.rojas").exists())

    def test_saves_the_national_identifier_in_its_panel_profile(self):
        self.assertEqual(
            self.submit(
                national_id_country="VE", national_id_type="cedula", national_id="v-12.345.678"
            ).status_code,
            200,
        )
        perfil = PerfilPanel.objects.get(user__username="ana.rojas")
        self.assertEqual(
            (perfil.pais, perfil.tipo_identificador_nacional, perfil.identificador_nacional),
            ("VE", "cedula", "V-12345678"),
        )

    def test_the_national_identifier_cannot_repeat_between_panel_users(self):
        other = User.objects.create_user(username="otro", password="x", is_staff=True)
        PerfilPanel.objects.create(
            user=other,
            pais="CL",
            tipo_identificador_nacional="rut",
            identificador_nacional="12345678-5",
        )
        self.assertEqual(
            self.errors(self.submit())["id_national_id"],
            "Ese identificador nacional ya lo tiene otro usuario del panel.",
        )
