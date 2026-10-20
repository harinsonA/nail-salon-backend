from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name

from apps.common.historial import sin_autor_de_la_peticion
from apps.panel.views.history.view import display_value
from apps.tenancy.estados import cambiar_estado
from apps.tenancy.models import Dominio, Negocio, Persona, Rubro

User = get_user_model()

PANEL = "admin.localhost"


class BusinessHistoryModalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
        cls.superuser = User.objects.create_superuser(
            username="admin", password="x", first_name="Ana", last_name="Rojas"
        )
        cls.barber = Rubro.objects.get(codigo="barberia")
        cls.nails = Rubro.objects.get(codigo="unas")
        cls.business = Negocio(
            schema_name="el_corte",
            nombre="El Corte",
            titular=Persona.objects.create(nombres="Carlos"),
            rubro=cls.barber,
            estado=Negocio.Estado.ACTIVO,
        )
        cls.business._change_reason = "Creado desde el panel"
        cls.business._history_user = cls.superuser
        cls.business.save()
        del cls.business._history_user
        with sin_autor_de_la_peticion():
            cambiar_estado(cls.business, Negocio.Estado.MOROSO, "dos meses sin pago")
        cls.business.rubro = cls.nails
        cls.business.notas_internas = "Paga el día 5"
        cls.business._change_reason = "Edición desde el panel"
        cls.business._history_user = cls.superuser
        cls.business.save()
        cls.viewer = User.objects.create_user(username="viewer", password="x", is_staff=True)
        cls.viewer.user_permissions.add(Permission.objects.get(codename="view_negocio"))
        cls.staff = User.objects.create_user(username="staff", password="x", is_staff=True)

    def setUp(self):
        connection.set_schema_to_public()

    def browser(self, user=None):
        browser = Client(HTTP_HOST=PANEL)
        browser.force_login(user or self.superuser)
        return browser

    def url(self):
        return f"/admin/tenancy/negocio/{self.business.pk}/history/"

    def list_url(self):
        return f"{self.url()}list/"

    def modal(self, user=None):
        return self.browser(user).get(self.url(), HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def fetch(self, user=None, **params):
        query = {"draw": 1, "start": 0, "length": 10, **params}
        return self.browser(user).get(self.list_url(), query, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def test_the_modal_has_the_summary_and_the_table(self):
        response = self.modal()
        self.assertTemplateUsed(response, "panel/history_modal.html")
        self.assertContains(response, "Historial · El Corte")
        self.assertEqual(response.context["total"], 3)
        self.assertEqual(response.context["created"]["author"], "Ana Rojas")
        self.assertEqual(response.context["last_change"]["author"], "Ana Rojas")
        self.assertContains(response, 'id="history_table" class="table table-hover"')
        self.assertContains(response, f"url: '{self.list_url()}'")
        self.assertContains(response, "renderDataTable(historyDataTableConfig);")
        self.assertContains(response, "type: 'column', target: 0")
        self.assertNotContains(response, "modal-footer")
        self.assertContains(response, "Detalle de los cambios")

    def test_the_list_returns_every_change_newest_first(self):
        payload = self.fetch().json()
        self.assertEqual((payload["recordsTotal"], payload["recordsFiltered"]), (3, 3))
        rows = payload["data"]
        self.assertEqual([row["action"] for row in rows], ["Modificado", "Modificado", "Creado"])
        self.assertEqual([row["action_key"] for row in rows], ["updated", "updated", "created"])
        self.assertEqual([row["reason"] for row in rows], ["Edición desde el panel", "dos meses sin pago", "Creado desde el panel"])
        self.assertEqual([row["author"] for row in rows], ["Ana Rojas", "Sistema", "Ana Rojas"])
        oldest_first = self.fetch(**{"order[0][column]": "1", "order[0][dir]": "asc"}).json()["data"]
        self.assertEqual(oldest_first[0]["action"], "Creado")
        control_column = self.fetch(**{"order[0][column]": "0", "order[0][dir]": "asc"}).json()["data"]
        self.assertEqual(control_column[0]["reason"], "Edición desde el panel")

    def test_changes_show_readable_values_and_skip_noise(self):
        rows = self.fetch().json()["data"]
        self.assertEqual(
            sorted((change["field"], change["old"], change["new"]) for change in rows[0]["changes"]),
            [("Notas internas", "—", "Paga el día 5"), ("Rubro", "Barbería", "Manicure y uñas")],
        )
        self.assertEqual(
            [(change["field"], change["old"], change["new"]) for change in rows[1]["changes"]],
            [("Estado", "Activo", "Moroso")],
        )
        self.assertEqual(rows[2]["changes"], [])

    def test_search_and_pagination(self):
        self.assertEqual([row["reason"] for row in self.fetch(**{"search[value]": "meses"}).json()["data"]], ["dos meses sin pago"])
        self.assertEqual(len(self.fetch(**{"search[value]": "rojas"}).json()["data"]), 2)
        for number in range(12):
            self.business.notas_internas = f"Nota {number}"
            self.business.save()
        page = self.fetch(length=8).json()
        self.assertEqual((len(page["data"]), page["recordsTotal"]), (8, 15))

    def test_without_ajax_goes_to_the_business_page(self):
        browser = self.browser()
        self.assertRedirects(browser.get(self.url()), f"/admin/tenancy/negocio/{self.business.pk}/change/", fetch_redirect_response=False)
        record = self.business.history.first()
        self.assertRedirects(
            browser.get(f"{self.url()}{record.history_id}/"),
            f"/admin/tenancy/negocio/{self.business.pk}/change/",
            fetch_redirect_response=False,
        )

    def test_permissions_and_missing_business(self):
        self.assertEqual(self.modal(self.viewer).status_code, 200)
        self.assertEqual(self.modal(self.staff).status_code, 403)
        self.assertEqual(self.fetch(self.viewer).status_code, 200)
        self.assertEqual(self.fetch(self.staff).status_code, 403)
        self.assertEqual(Client(HTTP_HOST=PANEL).get(self.list_url(), HTTP_X_REQUESTED_WITH="XMLHttpRequest").status_code, 401)
        missing = self.browser().get("/admin/tenancy/negocio/999999/history/", HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(missing.status_code, 404)

    def test_the_business_page_opens_it_in_the_large_modal(self):
        page = self.browser().get(f"/admin/tenancy/negocio/{self.business.pk}/change/")
        self.assertContains(page, f'class="btn btn-sm btn-outline-primary bs-xl-modal" data-form-url="{self.url()}"')
        self.assertContains(page, 'id="xl_modal"')
        self.assertContains(page, "initializeAllBSXLModals();")
        self.assertNotContains(page, "initializeHistoryModal")

    def test_display_value_formats_each_kind_of_field(self):
        self.assertEqual(display_value(Negocio, "estado", "pausado"), "Pausado")
        self.assertEqual(display_value(Negocio, "rubro", self.barber.pk), "Barbería")
        self.assertEqual(display_value(Negocio, "rubro", 999999), "#999999")
        self.assertEqual(display_value(Negocio, "notas_internas", ""), "—")
        self.assertEqual(display_value(Negocio, "notas_internas", None), "—")
        self.assertEqual(display_value(Rubro, "activo", False), "No")
