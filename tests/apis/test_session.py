from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.profiles.models import Perfil
from apps.seguridad.access import lock_status, register_failure
from apps.seguridad.models import AccesoUsuario, SesionMovil
from apps.tenancy.models import Negocio
from tests.apis.base import ApiTestCase

PASSWORD = "Clave-Segura-2026"
NEW_PASSWORD = "Otra-Clave-Larga-77"
PHONE_A = "telefono-a"
PHONE_B = "telefono-b"


@override_settings(ROOT_URLCONF="tests.apis.urls_for_tests")
class MobileSessionTests(ApiTestCase):
    esquema = "api_session"
    dominio = "api-session.localhost"

    def setUp(self):
        super().setUp()
        cache.clear()
        self.user = self.make_user(Perfil.Rol.ENCARGADO)
        self.user.set_password(PASSWORD)
        self.user.save()

    def phone(self, device=PHONE_A):
        return APIClient(HTTP_HOST=self.dominio, HTTP_X_APP_VERSION=self.app_version, HTTP_X_DISPOSITIVO=device)

    def log_in(self, password=PASSWORD, client=None):
        client = client or self.phone()
        return client.post(reverse("api_session_login"), {"email": self.user.email, "password": password}, format="json")

    def session_key(self, client=None):
        response = self.log_in(client=client)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["session_key"]

    def with_key(self, key, device=PHONE_A):
        client = self.phone(device)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {key}")
        return client

    def probe(self, key, device=PHONE_A):
        return self.with_key(key, device).get("/api/v1/sample/")

    def enable_biometric(self, key):
        response = self.with_key(key).post(reverse("api_session_biometric"))
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()["device_key"]

    def refresh(self, device_key):
        return self.phone().post(reverse("api_session_refresh"), {"device_key": device_key}, format="json")

    def web_client(self):
        client = Client(HTTP_HOST=self.dominio)
        response = client.post(reverse("login"), {"username": self.user.email, "password": PASSWORD})
        self.assertEqual(response.status_code, 302)
        return client

    def web_is_open(self, client):
        return client.get(reverse("calendar")).status_code == 200

    def test_login_gives_a_session_key_until_the_next_cutoff(self):
        response = self.log_in()
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["temporary_password"], False)
        self.assertEqual(body["biometric"], False)
        expires_at = datetime.fromisoformat(body["expires_at"]).astimezone(ZoneInfo(self.negocio.zona_horaria))
        self.assertEqual((expires_at.hour, expires_at.minute), (4, 0))
        self.assertLessEqual(expires_at - timezone.now(), timedelta(days=1))
        self.assertEqual(self.probe(body["session_key"]).status_code, 200)

    def test_the_server_only_keeps_a_digest_of_the_keys(self):
        key = self.session_key()
        sesion = SesionMovil.objects.get(user=self.user)
        self.assertNotEqual(sesion.llave_sesion, key)
        self.assertEqual(len(sesion.llave_sesion), 64)

    def test_without_key_the_route_asks_for_a_session(self):
        self.assertApiError(self.phone().get("/api/v1/sample/"), 401, "session_required")
        self.assertApiError(self.probe("1.unknown"), 401, "session_required")

    def test_wrong_password_uses_the_web_message_and_counter(self):
        for _ in range(3):
            self.assertApiError(self.log_in("mala"), 401, "invalid_credentials")
        response = self.log_in("mala")
        self.assertApiError(response, 401, "invalid_credentials")
        self.assertIn("Te queda 1 intento", response.json()["message"])
        self.assertEqual(lock_status(self.user).failures, 4)

    def test_five_failures_lock_for_fifteen_minutes(self):
        for _ in range(4):
            self.log_in("mala")
        response = self.log_in("mala")
        self.assertApiError(response, 423, "account_locked")
        self.assertEqual(response.json()["minutes_left"], 15)
        self.assertApiError(self.log_in(), 423, "account_locked")

    def test_ten_failures_lock_for_good(self):
        AccesoUsuario.objects.update_or_create(user=self.user, defaults={"intentos_fallidos": 9})
        response = self.log_in("mala")
        self.assertApiError(response, 423, "account_locked")
        self.assertIsNone(response.json()["minutes_left"])

    def test_a_good_login_resets_the_counter(self):
        self.log_in("mala")
        self.session_key()
        self.assertEqual(lock_status(self.user).failures, 0)

    def test_a_lock_from_the_web_closes_the_phone(self):
        key = self.session_key()
        for _ in range(5):
            register_failure(self.user)
        self.assertApiError(self.probe(key), 423, "account_locked")
        self.assertIsNone(SesionMovil.objects.get(user=self.user).llave_sesion)

    def test_inactive_user_cannot_log_in_and_loses_the_phone(self):
        key = self.session_key()
        self.user.is_active = False
        self.user.save()
        self.assertApiError(self.probe(key), 401, "session_required")
        self.assertApiError(self.log_in(), 401, "invalid_credentials")

    def test_password_reset_from_the_web_closes_the_phone(self):
        key = self.session_key()
        self.user.set_password(NEW_PASSWORD)
        self.user.save()
        self.assertApiError(self.probe(key), 401, "session_required")

    def test_cutoff_expires_the_session_key(self):
        key = self.session_key()
        SesionMovil.objects.filter(user=self.user).update(llave_sesion_vence=timezone.now() - timedelta(minutes=1))
        self.assertApiError(self.probe(key), 401, "session_expired")

    def test_logging_in_on_another_phone_closes_the_first_one(self):
        first = self.session_key(self.phone(PHONE_A))
        second = self.session_key(self.phone(PHONE_B))
        self.assertApiError(self.probe(first, PHONE_A), 401, "session_closed_elsewhere")
        self.assertEqual(self.probe(second, PHONE_B).status_code, 200)

    def test_web_and_phone_live_together(self):
        web = self.web_client()
        key = self.session_key()
        self.assertTrue(self.web_is_open(web))
        self.assertEqual(self.probe(key).status_code, 200)
        other_web = self.web_client()
        self.assertFalse(self.web_is_open(web))
        self.assertTrue(self.web_is_open(other_web))
        self.assertEqual(self.probe(key).status_code, 200)

    def test_biometric_refresh_gives_a_new_session_key(self):
        key = self.session_key()
        device_key = self.enable_biometric(key)
        SesionMovil.objects.filter(user=self.user).update(llave_sesion_vence=timezone.now() - timedelta(minutes=1))
        response = self.refresh(device_key)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["biometric"])
        self.assertEqual(self.probe(response.json()["session_key"]).status_code, 200)
        self.assertApiError(self.probe(key), 401, "session_required")

    def test_refresh_extends_the_device_key(self):
        device_key = self.enable_biometric(self.session_key())
        SesionMovil.objects.filter(user=self.user).update(llave_telefono_vence=timezone.now() + timedelta(days=1))
        self.assertEqual(self.refresh(device_key).status_code, 200)
        vence = SesionMovil.objects.get(user=self.user).llave_telefono_vence
        self.assertGreater(vence, timezone.now() + timedelta(days=29))

    def test_expired_or_disabled_device_key_cannot_refresh(self):
        key = self.session_key()
        device_key = self.enable_biometric(key)
        SesionMovil.objects.filter(user=self.user).update(llave_telefono_vence=timezone.now() - timedelta(minutes=1))
        self.assertApiError(self.refresh(device_key), 401, "session_required")
        device_key = self.enable_biometric(key)
        self.assertEqual(self.with_key(key).delete(reverse("api_session_biometric")).status_code, 204)
        self.assertApiError(self.refresh(device_key), 401, "session_required")
        self.assertApiError(self.refresh("nada"), 401, "session_required")

    def test_password_login_on_the_same_phone_keeps_the_biometric(self):
        device_key = self.enable_biometric(self.session_key())
        self.assertTrue(self.log_in().json()["biometric"])
        self.assertEqual(self.refresh(device_key).status_code, 200)
        self.session_key(self.phone(PHONE_B))
        self.assertApiError(self.refresh(device_key), 401, "session_required")

    def test_logout_cancels_both_keys(self):
        key = self.session_key()
        device_key = self.enable_biometric(key)
        self.assertEqual(self.with_key(key).post(reverse("api_session_logout")).status_code, 204)
        self.assertApiError(self.probe(key), 401, "session_required")
        self.assertApiError(self.refresh(device_key), 401, "session_required")

    def test_temporary_password_must_be_changed_first(self):
        Perfil.objects.filter(user=self.user).update(debe_cambiar_clave=True)
        response = self.log_in()
        self.assertTrue(response.json()["temporary_password"])
        key = response.json()["session_key"]
        self.assertApiError(self.probe(key), 428, "temporary_password")
        self.assertApiError(self.with_key(key).post(reverse("api_session_biometric")), 428, "temporary_password")
        change = self.with_key(key).post(
            reverse("api_account_password"),
            {"new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
            format="json",
        )
        self.assertEqual(change.status_code, 200, change.content)
        self.assertEqual(self.probe(key).status_code, 200)
        self.assertFalse(Perfil.objects.get(user=self.user).debe_cambiar_clave)

    def test_temporary_password_uses_the_web_validators(self):
        Perfil.objects.filter(user=self.user).update(debe_cambiar_clave=True)
        key = self.log_in().json()["session_key"]
        response = self.with_key(key).post(
            reverse("api_account_password"), {"new_password": "123", "confirm_password": "123"}, format="json"
        )
        self.assertApiError(response, 400, "invalid_data")
        self.assertIn("confirm_password", response.json()["fields"])

    def test_voluntary_change_checks_the_current_password(self):
        key = self.session_key()
        response = self.with_key(key).post(
            reverse("api_account_password"),
            {"current_password": "mala", "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
            format="json",
        )
        self.assertApiError(response, 400, "invalid_data")
        self.assertEqual(response.json()["fields"]["current_password"], ["La contraseña actual es incorrecta."])
        response = self.with_key(key).post(
            reverse("api_account_password"),
            {"current_password": PASSWORD, "new_password": NEW_PASSWORD, "confirm_password": "otra"},
            format="json",
        )
        self.assertEqual(response.json()["fields"]["confirm_password"], ["Las contraseñas no coinciden."])

    def test_voluntary_change_closes_the_web_and_keeps_this_phone(self):
        web = self.web_client()
        key = self.session_key()
        device_key = self.enable_biometric(key)
        response = self.with_key(key).post(
            reverse("api_account_password"),
            {"current_password": PASSWORD, "new_password": NEW_PASSWORD, "confirm_password": NEW_PASSWORD},
            format="json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["message"], "Tu clave quedó guardada.")
        self.assertFalse(self.web_is_open(web))
        self.assertEqual(self.probe(key).status_code, 200)
        self.assertEqual(self.refresh(device_key).status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_user_limit_blocks_the_login(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(limite_usuarios=1)
        self.negocio.refresh_from_db()
        self.make_user(Perfil.Rol.PROPIETARIO)
        self.assertApiError(self.log_in(), 401, "user_limit_reached")

    def test_too_many_logins_from_one_connection(self):
        for _ in range(10):
            self.log_in("mala")
        self.assertApiError(self.log_in(), 429, "too_many_requests")

    def test_too_many_refreshes_from_one_connection(self):
        for _ in range(30):
            self.refresh("nada")
        self.assertApiError(self.refresh("nada"), 429, "too_many_requests")
