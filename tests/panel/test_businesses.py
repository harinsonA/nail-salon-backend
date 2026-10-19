from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import Dominio, Negocio, Persona, Rubro

User = get_user_model()

PANEL = "admin.localhost"
LIST_URL = "/admin/tenancy/negocio/"
LIST_AJAX_URL = "/admin/tenancy/negocio/list/"


class BusinessesScreenTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
        cls.barber = Rubro.objects.get_or_create(codigo="barberia", defaults={"nombre": "Barbería"})[0]
        cls.cut = Negocio.objects.create(
            schema_name="el_corte",
            nombre="El Corte",
            titular=Persona.objects.create(nombres="Carlos", apellidos="Rojas"),
            rubro=cls.barber,
            estado=Negocio.Estado.ACTIVO,
        )
        Dominio.objects.create(domain="el-corte.localhost", tenant=cls.cut, is_primary=True)
        cls.nails = Negocio.objects.create(
            schema_name="unas_lucia",
            nombre="Uñas Lucía",
            titular=Persona.objects.create(nombres="Lucía"),
            estado=Negocio.Estado.PREPARANDO,
        )
        cls.superuser = User.objects.create_superuser(username="admin", password="x")
        cls.viewer = User.objects.create_user(username="viewer", password="x", is_staff=True)
        cls.viewer.user_permissions.add(*Permission.objects.filter(codename__in=["view_negocio", "add_negocio"]))
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

    def row(self, user, name):
        return next(row for row in self.fetch(user).json()["data"] if row["nombre"] == name)

    def test_menu_link_opens_the_panel_list(self):
        response = self.browser(self.superuser).get(LIST_URL)
        self.assertTemplateUsed(response, "panel/businesses/list.html")
        self.assertContains(response, 'id="businesses_table"')
        self.assertContains(response, f'url: \'{LIST_AJAX_URL}\'')
        self.assertContains(response, 'href="/admin/tenancy/negocio/add/"')

    def test_add_button_is_only_for_superusers(self):
        response = self.browser(self.viewer).get(LIST_URL)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "/admin/tenancy/negocio/add/")

    def test_staff_without_permission_gets_forbidden(self):
        response = self.browser(self.staff).get(LIST_URL)
        self.assertContains(response, "Tu usuario del panel no tiene permiso para esta acción.", status_code=403)

    def test_list_returns_businesses_without_the_platform(self):
        payload = self.fetch(self.superuser).json()
        self.assertEqual(self.names(self.superuser), ["El Corte", "Uñas Lucía"])
        self.assertEqual(
            (payload["total_businesses"], payload["active_businesses"], payload["overdue_businesses"],
             payload["preparing_businesses"]),
            (2, 1, 0, 1),
        )
        cut = self.row(self.superuser, "El Corte")
        self.assertEqual(cut["domain"], "el-corte.localhost")
        self.assertEqual(cut["status_label"], "Activo")
        self.assertEqual(cut["owner_name"], "Carlos Rojas")
        self.assertEqual(cut["industry_name"], "Barbería")
        nails = self.row(self.superuser, "Uñas Lucía")
        self.assertEqual((nails["domain"], nails["industry_name"], nails["owner_name"]), ("—", "—", "Lucía"))

    def test_status_and_industry_filters(self):
        self.assertEqual(self.names(self.superuser, status="preparando"), ["Uñas Lucía"])
        self.assertEqual(self.names(self.superuser, industry=self.barber.pk), ["El Corte"])

    def test_a_failed_preparation_shows_its_own_status(self):
        failed = Negocio.objects.create(
            schema_name="fallo",
            nombre="Fallo",
            titular=Persona.objects.create(nombres="Ana"),
            error_preparacion="OperationalError: sin espacio",
        )
        row = self.row(self.superuser, "Fallo")
        self.assertEqual((row["status_key"], row["status_label"], row["estado"]), ("fallido", "Falló", "preparando"))
        self.assertEqual([option["label"] for option in row["options"]], ["Editar", "Reparar alta", "Cambiar estado"])
        self.assertEqual(self.row(self.superuser, "Uñas Lucía")["status_key"], "preparando")
        self.assertEqual(self.names(self.superuser, status="fallido"), ["Fallo"])
        self.assertEqual(self.names(self.superuser, status="preparando"), ["Uñas Lucía"])
        payload = self.fetch(self.superuser).json()
        self.assertEqual((payload["preparing_businesses"], payload["failed_businesses"]), (1, 1))
        Negocio.objects.filter(pk=failed.pk).update(error_preparacion="")
        self.assertEqual(self.row(self.superuser, "Fallo")["status_key"], "preparando")
        page = self.browser(self.superuser).get(LIST_URL)
        self.assertContains(page, '<option value="fallido">Falló</option>')
        self.assertContains(page, "fallido: 'text-bg-danger'")
        self.assertContains(page, 'id="failed_businesses_note"')

    def test_search_by_name_owner_or_domain(self):
        self.assertEqual(self.names(self.superuser, **{"search[value]": "uñas"}), ["Uñas Lucía"])
        self.assertEqual(self.names(self.superuser, **{"search[value]": "rojas"}), ["El Corte"])
        self.assertEqual(self.names(self.superuser, **{"search[value]": "el-corte.local"}), ["El Corte"])

    def test_superuser_options_follow_the_business_state(self):
        active = [option["label"] for option in self.row(self.superuser, "El Corte")["options"]]
        preparing = [option["label"] for option in self.row(self.superuser, "Uñas Lucía")["options"]]
        self.assertEqual(active, ["Editar", "Cambiar estado"])
        self.assertEqual(preparing, ["Editar", "Reparar alta", "Cambiar estado"])
        repair = next(option for option in self.row(self.superuser, "Uñas Lucía")["options"] if option["label"] == "Reparar alta")
        self.assertEqual((repair["bsModal"], repair["className"], repair["icon"]), (True, "bs-modal", "build"))
        options = {option["label"]: option for option in self.row(self.superuser, "El Corte")["options"]}
        status = options["Cambiar estado"]
        self.assertEqual(status["link"], f"/admin/tenancy/negocio/{self.cut.pk}/estado/")
        self.assertEqual((status["bsModal"], status["className"], status["icon"]), (True, "bs-modal", "sync_alt"))

    def test_owner_modal_actions_are_only_in_the_edit_page(self):
        links = [option["link"] for option in self.row(self.superuser, "El Corte")["options"]]
        self.assertNotIn(f"/admin/tenancy/negocio/{self.cut.pk}/clave-propietario/", links)
        self.assertNotIn(f"/admin/tenancy/negocio/{self.cut.pk}/desbloquear-propietario/", links)
        page = self.browser(self.superuser).get(LIST_URL)
        self.assertContains(page, 'id="modal"')
        self.assertContains(page, "initializeBusinessActionModal('#modal', { onDone: () => table.draw(false) });")

    def test_there_is_no_delete_option(self):
        for row in self.fetch(self.superuser).json()["data"]:
            self.assertNotIn("Eliminar", [option["label"] for option in row["options"]])

    def test_staff_without_change_permission_gets_no_options(self):
        self.assertTrue(all(row["options"] == [] for row in self.fetch(self.viewer).json()["data"]))

    def test_list_without_session_answers_401(self):
        response = Client(HTTP_HOST=PANEL).get(LIST_AJAX_URL, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 401)
