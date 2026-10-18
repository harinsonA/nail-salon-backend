from django.contrib.admin.models import DELETION, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import Dominio, Negocio, Persona, Rubro

User = get_user_model()

PANEL = "admin.localhost"
LIST_URL = "/admin/tenancy/rubro/"
LIST_AJAX_URL = "/admin/tenancy/rubro/list/"


class IndustriesScreenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        Rubro.objects.all().delete()
        public = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
        cls.barber = Rubro.objects.create(codigo="barberia", nombre="Barbería")
        cls.spa = Rubro.objects.create(codigo="spa", nombre="Spa", activo=False)
        Negocio.objects.create(
            schema_name="el_corte", nombre="El Corte", titular=Persona.objects.create(nombres="Carlos"), rubro=cls.barber
        )
        cls.superuser = User.objects.create_superuser(username="admin", password="x")
        cls.viewer = User.objects.create_user(username="viewer", password="x", is_staff=True)
        cls.viewer.user_permissions.add(Permission.objects.get(codename="view_rubro"))
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

    def names(self, user, **params):
        return [row["nombre"] for row in self.fetch(user, **params).json()["data"]]

    def delete_modal_url(self, industry):
        return f"/admin/tenancy/rubro/{industry.pk}/delete/modal/"

    def test_menu_link_opens_the_panel_list(self):
        response = self.browser(self.superuser).get(LIST_URL)
        self.assertTemplateUsed(response, "panel/industries/list.html")
        self.assertContains(response, 'id="industries_table"')
        self.assertContains(response, f'url: \'{LIST_AJAX_URL}\'')
        self.assertContains(response, 'data-form-url="/admin/tenancy/rubro/add/modal/"')

    def test_add_button_requires_add_permission(self):
        response = self.browser(self.viewer).get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "/admin/tenancy/rubro/add/modal/")

    def test_staff_without_permission_gets_forbidden(self):
        response = self.browser(self.staff).get(LIST_URL)
        self.assertContains(response, "Tu usuario del panel no tiene permiso para esta acción.", status_code=403)

    def test_list_returns_industries_with_business_count_and_totals(self):
        payload = self.fetch(self.superuser).json()
        self.assertEqual((payload["total_industries"], payload["active_industries"]), (2, 1))
        rows = {row["nombre"]: row for row in payload["data"]}
        self.assertEqual(rows["Barbería"]["codigo"], "barberia")
        self.assertEqual(rows["Barbería"]["business_count"], 1)
        self.assertFalse(rows["Spa"]["activo"])

    def test_status_filter(self):
        self.assertEqual(self.names(self.superuser, status="active"), ["Barbería"])
        self.assertEqual(self.names(self.superuser, status="inactive"), ["Spa"])

    def test_search_by_name_or_code(self):
        self.assertEqual(self.names(self.superuser, **{"search[value]": "barb"}), ["Barbería"])
        self.assertEqual(self.names(self.superuser, **{"search[value]": "spa"}), ["Spa"])

    def test_order_by_business_count(self):
        self.assertEqual(self.names(self.superuser, **{"order[0][column]": "3", "order[0][dir]": "desc"}), ["Barbería", "Spa"])

    def test_the_list_has_no_order_column(self):
        response = self.browser(self.superuser).get(LIST_URL)
        self.assertNotContains(response, "<th scope=\"col\">Orden</th>", html=False)
        self.assertNotIn("orden", self.fetch(self.superuser).json()["data"][0])

    def test_industries_are_listed_by_name_everywhere(self):
        Rubro.objects.create(codigo="aaa", nombre="Uñas", orden=0)
        Rubro.objects.create(codigo="zzz", nombre="Aromaterapia", orden=99)
        self.assertEqual(list(Rubro.objects.values_list("nombre", flat=True)), ["Aromaterapia", "Barbería", "Spa", "Uñas"])

    def test_options_link_to_edit_form_and_delete_modal(self):
        row = next(row for row in self.fetch(self.superuser).json()["data"] if row["nombre"] == "Spa")
        options = {option["label"]: option for option in row["options"]}
        self.assertEqual(options["Editar"]["link"], f"/admin/tenancy/rubro/{self.spa.pk}/change/modal/")
        self.assertTrue(options["Editar"]["bsModal"])
        self.assertEqual(options["Eliminar"]["link"], self.delete_modal_url(self.spa))
        self.assertTrue(options["Eliminar"]["bsModal"])

    def test_options_follow_permissions(self):
        self.assertTrue(all(row["options"] == [] for row in self.fetch(self.viewer).json()["data"]))

    def test_list_without_session_answers_401(self):
        response = Client(HTTP_HOST=PANEL).get(LIST_AJAX_URL, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 401)

    def test_delete_modal_shows_the_industry_details(self):
        response = self.browser(self.superuser).get(
            self.delete_modal_url(self.barber), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertTemplateUsed(response, "common/delete_modal.html")
        self.assertContains(response, "Nombre: Barbería")
        self.assertContains(response, "Código: barberia")
        self.assertContains(response, "Negocios asociados: 1")

    def test_delete_modal_of_an_unused_industry_offers_the_deletion(self):
        response = self.browser(self.superuser).get(
            self.delete_modal_url(self.spa), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertContains(response, 'id="delete_submit_btn"')
        self.assertNotContains(response, "No se puede eliminar")

    def test_deleting_an_unused_industry_logs_it(self):
        response = self.browser(self.superuser).post(
            self.delete_modal_url(self.spa), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.json()["message"], "Rubro Spa eliminado exitosamente.")
        self.assertFalse(Rubro.objects.filter(pk=self.spa.pk).exists())
        log = LogEntry.objects.get(object_id=str(self.spa.pk), content_type__model="rubro")
        self.assertEqual(log.action_flag, DELETION)

    def test_an_industry_in_use_cannot_be_deleted(self):
        modal = self.browser(self.superuser).get(
            self.delete_modal_url(self.barber), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertContains(modal, "No se puede eliminar el rubro «Barbería»: tiene negocios asociados.")
        self.assertNotContains(modal, 'id="delete_submit_btn"')
        response = self.browser(self.superuser).post(
            self.delete_modal_url(self.barber), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "No se puede eliminar el rubro «Barbería»: tiene negocios asociados.")
        self.assertTrue(Rubro.objects.filter(pk=self.barber.pk).exists())

    def test_delete_requires_delete_permission(self):
        response = self.browser(self.viewer).post(
            self.delete_modal_url(self.spa), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Rubro.objects.filter(pk=self.spa.pk).exists())
