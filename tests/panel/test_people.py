from django.contrib.admin.models import DELETION, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import Dominio, Negocio, Persona, PersonaCorreo, PersonaTelefono

User = get_user_model()

PANEL = "admin.localhost"
LIST_URL = "/admin/tenancy/persona/"
LIST_AJAX_URL = "/admin/tenancy/persona/list/"


class PeopleScreenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
        cls.owner = Persona.objects.create(nombres="Carlos", apellidos="Rojas")
        PersonaCorreo.objects.create(persona=cls.owner, correo="carlos@elcorte.cl", es_principal=True)
        PersonaTelefono.objects.create(persona=cls.owner, codigo_pais="+56", numero="912345678", es_principal=True)
        Negocio.objects.create(schema_name="el_corte", nombre="El Corte", titular=cls.owner)
        cls.contact = Persona.objects.create(nombres="Lucía")
        cls.superuser = User.objects.create_superuser(username="admin", password="x")
        cls.viewer = User.objects.create_user(username="viewer", password="x", is_staff=True)
        cls.viewer.user_permissions.add(Permission.objects.get(codename="view_persona"))
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
        return [row["full_name"] for row in self.fetch(user, **params).json()["data"]]

    def delete_modal_url(self, person):
        return f"/admin/tenancy/persona/{person.pk}/delete/modal/"

    def test_menu_link_opens_the_panel_list(self):
        response = self.browser(self.superuser).get(LIST_URL)
        self.assertTemplateUsed(response, "panel/people/list.html")
        self.assertContains(response, 'id="people_table"')
        self.assertContains(response, f'url: \'{LIST_AJAX_URL}\'')
        self.assertContains(response, 'data-form-url="/admin/tenancy/persona/add/modal/"')

    def test_add_button_requires_add_permission(self):
        response = self.browser(self.viewer).get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="person-create-btn"')

    def test_staff_without_permission_gets_forbidden(self):
        response = self.browser(self.staff).get(LIST_URL)
        self.assertContains(response, "Tu usuario del panel no tiene permiso para esta acción.", status_code=403)

    def test_list_returns_people_with_contact_data_and_totals(self):
        payload = self.fetch(self.superuser).json()
        self.assertEqual((payload["total_people"], payload["business_owners"]), (2, 1))
        rows = {row["full_name"]: row for row in payload["data"]}
        self.assertEqual(rows["Carlos Rojas"]["main_email"], "carlos@elcorte.cl")
        self.assertEqual(rows["Carlos Rojas"]["main_phone"], "+56 912345678")
        self.assertEqual(rows["Carlos Rojas"]["business_count"], 1)
        self.assertEqual((rows["Lucía"]["main_email"], rows["Lucía"]["main_phone"]), ("—", "—"))

    def test_ownership_filter(self):
        self.assertEqual(self.names(self.superuser, ownership="owners"), ["Carlos Rojas"])
        self.assertEqual(self.names(self.superuser, ownership="without_business"), ["Lucía"])

    def test_search_by_name_email_or_phone(self):
        self.assertEqual(self.names(self.superuser, **{"search[value]": "rojas"}), ["Carlos Rojas"])
        self.assertEqual(self.names(self.superuser, **{"search[value]": "elcorte"}), ["Carlos Rojas"])
        self.assertEqual(self.names(self.superuser, **{"search[value]": "912345"}), ["Carlos Rojas"])

    def test_soft_deleted_people_are_not_listed(self):
        Persona.objects.create(nombres="Borrada").delete()
        self.assertNotIn("Borrada", self.names(self.superuser))

    def test_options_link_to_edit_and_delete_modals(self):
        row = next(row for row in self.fetch(self.superuser).json()["data"] if row["full_name"] == "Lucía")
        options = {option["label"]: option for option in row["options"]}
        self.assertEqual(options["Editar"]["link"], f"/admin/tenancy/persona/{self.contact.pk}/change/modal/")
        self.assertEqual(options["Editar"]["className"], "bs-xl-modal")
        self.assertEqual(options["Eliminar"]["link"], self.delete_modal_url(self.contact))
        self.assertTrue(options["Eliminar"]["bsModal"])

    def test_options_follow_permissions(self):
        self.assertTrue(all(row["options"] == [] for row in self.fetch(self.viewer).json()["data"]))

    def test_list_without_session_answers_401(self):
        response = Client(HTTP_HOST=PANEL).get(LIST_AJAX_URL, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 401)

    def test_delete_modal_shows_the_person_details(self):
        response = self.browser(self.superuser).get(
            self.delete_modal_url(self.owner), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertTemplateUsed(response, "common/delete_modal.html")
        self.assertContains(response, "Nombre: Carlos Rojas")
        self.assertContains(response, "Correos: 1")
        self.assertContains(response, "Teléfonos: 1")
        self.assertContains(response, "Negocios como titular: 1")

    def test_deleting_a_person_without_business_soft_deletes_and_logs_it(self):
        response = self.browser(self.superuser).post(
            self.delete_modal_url(self.contact), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.json()["message"], "Persona Lucía eliminada exitosamente.")
        self.assertFalse(Persona.objects.filter(pk=self.contact.pk).exists())
        self.assertTrue(Persona.all_objects.filter(pk=self.contact.pk, is_removed=True).exists())
        log = LogEntry.objects.get(object_id=str(self.contact.pk), content_type__model="persona")
        self.assertEqual(log.action_flag, DELETION)

    def test_a_business_owner_cannot_be_deleted(self):
        message = "No se puede eliminar a «Carlos Rojas»: es titular de un negocio. Primero cambia el titular."
        browser = self.browser(self.superuser)
        modal = browser.get(self.delete_modal_url(self.owner), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertContains(modal, message)
        self.assertNotContains(modal, 'id="delete_submit_btn"')
        response = browser.post(self.delete_modal_url(self.owner), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], message)
        self.assertTrue(Persona.objects.filter(pk=self.owner.pk).exists())

    def test_delete_modal_of_a_person_without_business_offers_the_deletion(self):
        response = self.browser(self.superuser).get(
            self.delete_modal_url(self.contact), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertContains(response, 'id="delete_submit_btn"')
        self.assertNotContains(response, "No se puede eliminar")

    def test_delete_requires_delete_permission(self):
        response = self.browser(self.viewer).post(
            self.delete_modal_url(self.contact), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Persona.objects.filter(pk=self.contact.pk).exists())
