from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.profiles.models import Perfil
from apps.settings.preferences.registry import (
    APP_CALENDAR_VIEW,
    APP_IDLE_LOCK_MINUTES,
    CALENDAR_DEFAULT_VIEW,
    RESERVATION_AMOUNT,
    RESERVATION_ENABLED,
    SESSION_IDLE_MINUTES,
)
from apps.settings.preferences.service import get_preference, set_preference
from apps.tenancy.models import Negocio
from tests.apis.base import ApiTestCase

User = get_user_model()
Rol = Perfil.Rol

ADMIN_CAPABILITIES = [
    "view_dashboard",
    "manage_services",
    "manage_categories",
    "view_payments",
    "view_incomes",
    "view_debtors",
    "manage_appointment_settings",
    "view_all_appointments",
    "assign_appointments",
]


class MeTests(ApiTestCase):
    esquema = "api_me"
    dominio = "api-me.localhost"

    def set_user_limit(self, limit):
        Negocio.objects.filter(pk=self.negocio.pk).update(limite_usuarios=limit)
        self.negocio.refresh_from_db()

    def me(self):
        response = self.api_client.get(reverse("api_me"))
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def colleague(self, rol, name):
        user = User.objects.create_user(username=name, email=f"{name}@correo.cl", first_name=name.title())
        Perfil.objects.filter(user=user).update(rol=rol, debe_cambiar_clave=False)
        return user

    def test_owner_gets_everything_and_cannot_edit_profile(self):
        self.set_user_limit(None)
        owner = self.log_in_as(Rol.PROPIETARIO)
        collaborator = self.colleague(Rol.COLABORADOR, "carla")
        data = self.me()
        self.assertEqual(data["user"]["rol"], Rol.PROPIETARIO)
        self.assertFalse(data["can_edit_profile"])
        self.assertEqual(data["capabilities"], [*ADMIN_CAPABILITIES[:6], "manage_team", *ADMIN_CAPABILITIES[6:]])
        ids = [member["id"] for member in data["assignable_users"]]
        self.assertIn(owner.pk, ids)
        self.assertIn(collaborator.pk, ids)

    def test_manager_can_edit_profile_and_sees_team_only_with_team(self):
        self.set_user_limit(1)
        self.log_in_as(Rol.ENCARGADO)
        data = self.me()
        self.assertTrue(data["can_edit_profile"])
        self.assertEqual(data["capabilities"], ADMIN_CAPABILITIES)
        self.set_user_limit(3)
        self.assertIn("manage_team", self.me()["capabilities"])

    def test_collaborator_only_gets_her_own_things(self):
        self.set_user_limit(None)
        self.colleague(Rol.ENCARGADO, "elena")
        self.log_in_as(Rol.COLABORADOR)
        data = self.me()
        self.assertTrue(data["can_edit_profile"])
        self.assertEqual(data["capabilities"], [])
        self.assertEqual(data["assignable_users"], [])

    def test_user_block(self):
        user = self.log_in_as(Rol.ENCARGADO)
        user.first_name, user.last_name = "Ana", "Rojas"
        user.save()
        data = self.me()
        self.assertEqual(data["user"]["initials"], "AR")
        self.assertEqual(data["user"]["email"], user.email)
        self.assertIsNone(data["user"]["pais"])
        self.assertEqual(data["user"]["role_label"], "Encargado")
        self.assertNotIn("payment_methods", data)

    def test_default_preferences_and_reservation_from_the_web(self):
        set_preference(RESERVATION_ENABLED.key, True)
        set_preference(RESERVATION_AMOUNT.key, 5000)
        self.log_in_as(Rol.COLABORADOR)
        preferences = self.me()["preferences"]
        self.assertEqual(preferences["calendar_view"], "day")
        self.assertTrue(preferences["calendar_show_pending"])
        self.assertTrue(preferences["calendar_show_completed"])
        self.assertTrue(preferences["calendar_show_cancelled"])
        self.assertEqual(preferences["idle_lock_minutes"], 120)
        self.assertTrue(preferences["reservation_enabled"])
        self.assertEqual(preferences["reservation_amount"], 5000)
        self.assertEqual(preferences["reservation_payment_method"], "EFECTIVO")


class MePreferencesTests(ApiTestCase):
    esquema = "api_me_preferences"
    dominio = "api-me-preferences.localhost"

    def patch(self, data):
        return self.api_client.patch(reverse("api_me_preferences"), data, format="json")

    def test_saves_only_what_changed_without_touching_the_web(self):
        user = self.log_in_as(Rol.COLABORADOR)
        response = self.patch({"calendar_view": "list", "calendar_show_cancelled": False, "idle_lock_minutes": 0})
        self.assertEqual(response.status_code, 200, response.content)
        preferences = response.json()["preferences"]
        self.assertEqual(preferences["calendar_view"], "list")
        self.assertFalse(preferences["calendar_show_cancelled"])
        self.assertTrue(preferences["calendar_show_pending"])
        self.assertEqual(preferences["idle_lock_minutes"], 0)
        self.assertEqual(get_preference(APP_CALENDAR_VIEW.key, user=user), "list")
        self.assertEqual(get_preference(CALENDAR_DEFAULT_VIEW.key, user=user), "mes")
        self.assertEqual(get_preference(SESSION_IDLE_MINUTES.key, user=user), 120)

    def test_preferences_belong_to_each_person(self):
        other = self.make_user(Rol.ENCARGADO)
        self.log_in_as(Rol.COLABORADOR)
        self.patch({"idle_lock_minutes": 30})
        self.assertEqual(get_preference(APP_IDLE_LOCK_MINUTES.key, user=other), 120)

    def test_idle_lock_accepts_the_web_options_only(self):
        self.log_in_as(Rol.ENCARGADO)
        response = self.patch({"idle_lock_minutes": 45, "calendar_view": "month"})
        self.assertApiError(response, 400, "invalid_data")
        self.assertEqual(set(response.json()["fields"]), {"idle_lock_minutes", "calendar_view"})

    def test_reservation_is_read_only(self):
        self.log_in_as(Rol.PROPIETARIO)
        response = self.patch({"reservation_enabled": True, "reservation_amount": 9000})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(get_preference(RESERVATION_ENABLED.key))
        self.assertEqual(get_preference(RESERVATION_AMOUNT.key), 0)


class MeProfileTests(ApiTestCase):
    esquema = "api_me_profile"
    dominio = "api-me-profile.localhost"

    def patch(self, data):
        return self.api_client.patch(reverse("api_me_profile"), data, format="json")

    def complete(self, user):
        Perfil.objects.filter(user=user).update(pais="CL", tipo_identificador_nacional="rut", identificador_nacional="12.345.678-5")

    def test_owner_gets_403(self):
        self.log_in_as(Rol.PROPIETARIO)
        self.assertApiError(self.patch({"first_name": "Otra"}), 403, "forbidden")

    def test_manager_changes_only_what_she_sends(self):
        user = self.log_in_as(Rol.ENCARGADO)
        self.complete(user)
        response = self.patch({"first_name": "Elena", "email": " ELENA@Correo.cl "})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["user"]["first_name"], "Elena")
        user.refresh_from_db()
        self.assertEqual(user.email, "elena@correo.cl")
        self.assertEqual(user.username, "elena@correo.cl")
        self.assertNotIn("username", response.json()["user"])
        self.assertEqual(user.perfil.identificador_nacional, "12345678-5")

    def test_collaborator_saves_her_identifier(self):
        user = self.log_in_as(Rol.COLABORADOR)
        response = self.patch({"pais": "CL", "tipo_identificador_nacional": "rut", "identificador_nacional": "12345678-5"})
        self.assertEqual(response.status_code, 200, response.content)
        user.perfil.refresh_from_db()
        self.assertEqual(user.perfil.identificador_nacional, "12345678-5")

    def test_web_rules_with_model_field_names(self):
        self.make_user(Rol.ENCARGADO)
        user = self.log_in_as(Rol.COLABORADOR)
        response = self.patch({"email": "", "identificador_nacional": "11.111.111-2"})
        self.assertApiError(response, 400, "invalid_data")
        fields = response.json()["fields"]
        self.assertIn("email", fields)
        self.assertTrue({"pais", "tipo_identificador_nacional", "identificador_nacional"} & set(fields))
        taken = self.patch({"email": "encargado.api@correo.cl"})
        self.assertIn("email", taken.json()["fields"])
        user.refresh_from_db()
        self.assertEqual(user.email, "colaborador.api@correo.cl")

    def test_web_profile_still_locks_the_owner(self):
        owner = self.make_user(Rol.PROPIETARIO)
        browser = Client(HTTP_HOST=self.dominio)
        browser.force_login(owner)
        response = browser.post(
            reverse("profile_modal"),
            {"first_name": "Cambio", "session_idle_minutes": "60"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200, response.content)
        owner.refresh_from_db()
        self.assertNotEqual(owner.first_name, "Cambio")
        self.assertEqual(get_preference(SESSION_IDLE_MINUTES.key, user=owner), 60)
