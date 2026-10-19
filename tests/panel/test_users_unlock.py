from datetime import timedelta

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import Client, TestCase
from django.utils import timezone
from django_tenants.utils import get_public_schema_name

from apps.seguridad.access import lock_status, register_failure
from apps.seguridad.models import AccesoUsuario
from apps.tenancy.models import Dominio, Negocio

User = get_user_model()

PANEL = "admin.localhost"
LIST_AJAX_URL = "/admin/auth/user/list/"


def lock(user, times=5):
    for _ in range(times):
        register_failure(user)


def lock_permanently(user):
    lock(user)
    AccesoUsuario.objects.filter(user=user).update(bloqueado_hasta=timezone.now() - timedelta(seconds=1))
    lock(user)


class UsersUnlockTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
        cls.superuser = User.objects.create_superuser(username="admin", password="x", email="admin@hiagenda.cl")
        cls.editor = User.objects.create_user(username="editor", password="x", is_staff=True)
        cls.editor.user_permissions.add(*Permission.objects.filter(codename__in=["view_user", "change_user"]))
        cls.viewer = User.objects.create_user(username="viewer", password="x", is_staff=True)
        cls.viewer.user_permissions.add(Permission.objects.get(codename="view_user"))
        cls.ana = User.objects.create_user(username="ana", password="x", is_staff=True)
        cls.otro_admin = User.objects.create_superuser(username="otro_admin", password="x", email="otro@hiagenda.cl")

    def setUp(self):
        connection.set_schema_to_public()

    def browser(self, user):
        browser = Client(HTTP_HOST=PANEL)
        browser.force_login(user)
        return browser

    def fetch(self, user, **params):
        query = {"draw": 1, "start": 0, "length": 10, "order[0][column]": "0", "order[0][dir]": "asc", **params}
        return self.browser(user).get(LIST_AJAX_URL, query, HTTP_X_REQUESTED_WITH="XMLHttpRequest").json()

    def row(self, payload, username):
        return next(row for row in payload["data"] if row["username"] == username)

    def unlock_url(self, user):
        return f"/admin/auth/user/{user.pk}/unlock/modal/"

    def post_unlock(self, editor, user):
        return self.browser(editor).post(self.unlock_url(user), HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def test_list_shows_the_lock_state(self):
        lock(self.ana)
        lock_permanently(self.otro_admin)
        payload = self.fetch(self.superuser)
        until = timezone.localtime(AccesoUsuario.objects.get(user=self.ana).bloqueado_hasta).strftime("%H:%M")
        self.assertEqual(self.row(payload, "ana")["lock_label"], f"Bloqueado hasta las {until}")
        self.assertEqual(self.row(payload, "otro_admin")["lock_label"], "Bloqueado hasta que alguien lo desbloquee")
        self.assertEqual(self.row(payload, "viewer")["lock_label"], "")
        self.assertEqual(payload["locked_users"], 2)

    def test_an_expired_temporary_lock_is_not_shown(self):
        lock(self.ana)
        AccesoUsuario.objects.filter(user=self.ana).update(bloqueado_hasta=timezone.now() - timedelta(seconds=1))
        payload = self.fetch(self.superuser)
        self.assertEqual(self.row(payload, "ana")["lock_label"], "")
        self.assertEqual(payload["locked_users"], 0)

    def test_filter_shows_only_locked_users(self):
        lock(self.ana)
        usernames = [row["username"] for row in self.fetch(self.superuser, status="locked")["data"]]
        self.assertEqual(usernames, ["ana"])

    def test_unlock_option_only_for_locked_users_and_editors(self):
        lock(self.ana)
        payload = self.fetch(self.superuser)
        labels = [option["label"] for option in self.row(payload, "ana")["options"]]
        self.assertIn("Desbloquear", labels)
        self.assertNotIn("Desbloquear", [option["label"] for option in self.row(payload, "viewer")["options"]])
        viewer_payload = self.fetch(self.viewer)
        self.assertNotIn("Desbloquear", [option["label"] for option in self.row(viewer_payload, "ana")["options"]])

    def test_non_superuser_cannot_unlock_a_superuser(self):
        lock(self.otro_admin)
        payload = self.fetch(self.editor)
        self.assertNotIn("Desbloquear", [option["label"] for option in self.row(payload, "otro_admin")["options"]])
        self.assertEqual(self.post_unlock(self.editor, self.otro_admin).status_code, 403)
        self.assertTrue(lock_status(self.otro_admin).is_locked)

    def test_modal_describes_the_lock(self):
        lock(self.ana)
        response = self.browser(self.superuser).get(self.unlock_url(self.ana))
        self.assertTemplateUsed(response, "panel/users/unlock_modal.html")
        self.assertContains(response, "Desbloquear usuario · ana")
        self.assertContains(response, f"Bloqueado hasta las {timezone.localtime(lock_status(self.ana).until).strftime('%H:%M')}")
        self.assertContains(response, "5 intentos fallidos seguidos.")
        self.assertContains(response, "lock.svg")
        self.assertContains(response, 'id="unlock_submit_btn"')

    def test_modal_for_an_unlocked_user_has_no_button(self):
        response = self.browser(self.superuser).get(self.unlock_url(self.ana))
        self.assertContains(response, "Este usuario no está bloqueado.")
        self.assertNotContains(response, 'id="unlock_submit_btn"')

    def test_editor_unlocks_and_leaves_a_trace(self):
        lock_permanently(self.ana)
        response = self.post_unlock(self.editor, self.ana)
        self.assertEqual(response.json()["message"], "«ana» quedó desbloqueado.")
        self.assertFalse(lock_status(self.ana).is_locked)
        latest = AccesoUsuario.objects.get(user=self.ana).history.first()
        self.assertEqual(latest.history_change_reason, "Desbloqueado desde el panel")
        self.assertEqual(latest.history_user, self.editor)
        self.assertTrue(LogEntry.objects.filter(object_id=str(self.ana.pk), action_flag=CHANGE).exists())

    def test_unlocking_a_free_user_says_so(self):
        response = self.post_unlock(self.superuser, self.ana)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "«ana» no está bloqueado.")

    def test_viewer_cannot_unlock(self):
        lock(self.ana)
        self.assertEqual(self.post_unlock(self.viewer, self.ana).status_code, 403)
        self.assertTrue(lock_status(self.ana).is_locked)

    def test_setting_a_new_password_unlocks(self):
        lock_permanently(self.ana)
        browser = self.browser(self.superuser)
        response = browser.post(
            f"/admin/auth/user/{self.ana.pk}/change/modal/",
            {
                "username": "ana",
                "first_name": "Ana",
                "first_surname": "Rojas",
                "email": "ana@hiagenda.cl",
                "is_active": "on",
                "is_staff": "on",
                "password": "Nueva-Clave-2026x",
                "password_confirmation": "Nueva-Clave-2026x",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(lock_status(self.ana).is_locked)
        self.assertEqual(
            AccesoUsuario.objects.get(user=self.ana).history.first().history_change_reason,
            "Desbloqueado al cambiar la contraseña desde el panel",
        )
