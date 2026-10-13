import json

from django.conf import settings
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.test import RequestFactory, TestCase
from django.urls import set_urlconf
from django.views.generic import TemplateView

from apps.panel.views.base import PanelListViewAjax, PanelView

User = get_user_model()


class SamplePageView(PanelView, TemplateView):
    template_name = "panel/inicio.html"


class SampleListView(PanelListViewAjax):
    model = Group
    field_list = ["pk", "name"]


class PanelViewsAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        Group.objects.create(name="Soporte")
        cls.staff = User.objects.create_user(username="staff", password="x", is_staff=True)
        cls.viewer = User.objects.create_user(username="viewer", password="x", is_staff=True)
        cls.viewer.user_permissions.add(Permission.objects.get(codename="view_group"))
        cls.customer = User.objects.create_user(username="customer", password="x")

    def setUp(self):
        connection.set_schema_to_public()
        set_urlconf(settings.PUBLIC_SCHEMA_URLCONF)
        self.addCleanup(set_urlconf, None)

    def call(self, view_class, user, path="/admin/auth/group/"):
        request = RequestFactory().get(path, HTTP_HOST="admin.localhost")
        request.user = User.objects.get(pk=user.pk) if user else AnonymousUser()
        model_admin = admin.site._registry[Group]
        return view_class.as_view(admin_site=admin.site, model_admin=model_admin)(request)

    def test_page_without_session_redirects_to_panel_login(self):
        response = self.call(SamplePageView, None)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/admin/login/?next=/admin/auth/group/")

    def test_page_rejects_users_that_are_not_staff(self):
        response = self.call(SamplePageView, self.customer)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/admin/login/"))

    def test_page_without_model_permission_is_forbidden(self):
        with self.assertRaises(PermissionDenied):
            self.call(SamplePageView, self.staff)

    def test_page_with_model_permission_gets_site_context(self):
        response = self.call(SamplePageView, self.viewer)
        self.assertEqual(response.status_code, 200)
        self.assertIn("available_apps", response.context_data)
        self.assertIn("site_url", response.context_data)

    def test_ajax_without_session_answers_401_with_panel_login(self):
        response = self.call(SampleListView, None)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.content)["redirect"], "/admin/login/")

    def test_ajax_rejects_users_that_are_not_staff(self):
        self.assertEqual(self.call(SampleListView, self.customer).status_code, 401)

    def test_ajax_without_model_permission_answers_403(self):
        response = self.call(SampleListView, self.staff)
        self.assertEqual(response.status_code, 403)
        self.assertIn("message", json.loads(response.content))

    def test_ajax_with_model_permission_returns_the_list(self):
        response = self.call(SampleListView, self.viewer)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)["recordsTotal"], 1)
        self.assertEqual(json.loads(response.content)["data"][0]["name"], "Soporte")
