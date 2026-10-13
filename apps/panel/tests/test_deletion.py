from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import deletion
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name

from apps.panel.deletion import deletion_limited_to_current_schema
from apps.tenancy.models import Dominio, Negocio

User = get_user_model()


def related_apps():
    return {relation.related_model._meta.app_label for relation in deletion.get_candidate_relations_to_delete(User._meta)}


class CurrentSchemaDeletionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain="admin.localhost", tenant=public, is_primary=True)
        cls.superuser = User.objects.create_superuser(username="admin", password="x")
        cls.victim = User.objects.create_user(username="victim", password="x")

    def setUp(self):
        connection.set_schema_to_public()

    def test_outside_the_switch_django_keeps_every_relation(self):
        self.assertIn("authtoken", related_apps())
        self.assertIn("profiles", related_apps())

    def test_inside_the_switch_only_public_relations_remain(self):
        with deletion_limited_to_current_schema():
            apps = related_apps()
        self.assertNotIn("authtoken", apps)
        self.assertNotIn("profiles", apps)
        self.assertIn("admin", apps)
        self.assertIn("tenancy", apps)

    def test_the_switch_turns_itself_off(self):
        with deletion_limited_to_current_schema():
            pass
        self.assertIn("authtoken", related_apps())

    def test_django_delete_page_for_users_works_in_the_panel(self):
        browser = Client(HTTP_HOST="admin.localhost")
        browser.force_login(self.superuser)
        url = f"/admin/auth/user/{self.victim.pk}/delete/"
        self.assertEqual(browser.get(url).status_code, 200)
        self.assertRedirects(browser.post(url, {"post": "yes"}), "/admin/auth/user/", fetch_redirect_response=False)
        self.assertFalse(User.objects.filter(pk=self.victim.pk).exists())
