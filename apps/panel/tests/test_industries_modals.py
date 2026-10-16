from django.contrib.admin.models import ADDITION, CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import Dominio, Negocio, Persona, Rubro

User = get_user_model()

PANEL = "admin.localhost"
LIST_URL = "/admin/tenancy/rubro/"
CREATE_URL = "/admin/tenancy/rubro/add/modal/"


class IndustryModalsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        Rubro.objects.all().delete()
        public = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
        cls.barber = Rubro.objects.create(codigo="barberia", nombre="Barbería", orden=1)
        cls.spa = Rubro.objects.create(codigo="spa", nombre="Spa", orden=4, activo=False)
        Negocio.objects.create(
            schema_name="el_corte", nombre="El Corte", titular=Persona.objects.create(nombres="Carlos"), rubro=cls.barber
        )
        cls.superuser = User.objects.create_superuser(username="admin", password="x")
        cls.viewer = User.objects.create_user(username="viewer", password="x", is_staff=True)
        cls.viewer.user_permissions.add(Permission.objects.get(codename="view_rubro"))

    def setUp(self):
        connection.set_schema_to_public()

    def browser(self, user=None):
        browser = Client(HTTP_HOST=PANEL)
        if user:
            browser.force_login(user)
        return browser

    def edit_url(self, industry):
        return f"/admin/tenancy/rubro/{industry.pk}/change/modal/"

    def payload(self, **changes):
        data = {"nombre": "Peluquería", "codigo": "peluqueria", "orden": "2", "activo": "on"}
        data.update(changes)
        return {key: value for key, value in data.items() if value is not None}

    def post(self, url, user=None, **changes):
        return self.browser(user or self.superuser).post(url, self.payload(**changes), HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def get(self, url, user=None):
        return self.browser(user or self.superuser).get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def errors(self, response):
        self.assertEqual(response.status_code, 400)
        return {error["id_element"]: error["error"] for error in response.json()["errors"]}

    def test_create_modal_proposes_the_next_order(self):
        response = self.get(CREATE_URL)
        self.assertTemplateUsed(response, "panel/industries/industry_modal.html")
        html = response.content.decode()
        self.assertIn("Nuevo rubro", html)
        self.assertRegex(html, r'name="orden" value="5"')
        self.assertRegex(html, r'name="activo"[^>]*checked')
        self.assertNotIn("Negocios que usan este rubro", html)

    def test_creates_an_industry_and_logs_it(self):
        response = self.post(CREATE_URL, nombre="  Peluquería   canina ")
        self.assertEqual(response.json()["message"], "Rubro Peluquería canina creado exitosamente.")
        industry = Rubro.objects.get(codigo="peluqueria")
        self.assertEqual((industry.nombre, industry.orden, industry.activo), ("Peluquería canina", 2, True))
        log = LogEntry.objects.get(object_id=str(industry.pk), content_type__model="rubro")
        self.assertEqual(log.action_flag, ADDITION)

    def test_can_be_created_inactive(self):
        self.post(CREATE_URL, activo=None)
        self.assertFalse(Rubro.objects.get(codigo="peluqueria").activo)

    def test_name_rules(self):
        cases = {
            "": "requerido",
            "Peluquería 2": "caracteres alfabéticos",
            "a" * 81: "no debe superar 80",
            "barbería": "Ya existe un rubro con ese nombre.",
        }
        for nombre, message in cases.items():
            with self.subTest(nombre=nombre):
                self.assertIn(message, self.errors(self.post(CREATE_URL, nombre=nombre))["id_nombre"])

    def test_code_rules(self):
        cases = {
            "Peluqueria": "minúsculas",
            "pe": "entre 3 y 30",
            "1peluqueria": "debe empezar con una letra",
            "peluquería": "debe empezar con una letra",
            "pelu queria": "debe empezar con una letra",
            "barberia": "Ya existe un rubro con ese código.",
        }
        for codigo, message in cases.items():
            with self.subTest(codigo=codigo):
                self.assertIn(message, self.errors(self.post(CREATE_URL, codigo=codigo))["id_codigo"])

    def test_order_must_be_a_valid_number(self):
        for orden in ("-1", "40000", "abc"):
            with self.subTest(orden=orden):
                self.assertIn("id_orden", self.errors(self.post(CREATE_URL, orden=orden)))

    def test_edit_modal_loads_the_industry_and_its_businesses(self):
        html = self.get(self.edit_url(self.barber)).content.decode()
        self.assertIn("Editar rubro · Barbería", html)
        self.assertRegex(html, r'name="codigo" value="barberia"')
        self.assertRegex(html, r'name="orden" value="1"')
        self.assertIn("Negocios que usan este rubro: 1.", html)

    def test_edits_every_field_and_logs_the_change(self):
        response = self.post(self.edit_url(self.spa), nombre="Spa y masajes", codigo="spa_masajes", orden="9", activo="on")
        self.assertEqual(response.json()["message"], "Rubro Spa y masajes actualizado exitosamente.")
        spa = Rubro.objects.get(pk=self.spa.pk)
        self.assertEqual((spa.nombre, spa.codigo, spa.orden, spa.activo), ("Spa y masajes", "spa_masajes", 9, True))
        log = LogEntry.objects.filter(object_id=str(spa.pk), content_type__model="rubro").latest("action_time")
        self.assertEqual(log.action_flag, CHANGE)

    def test_editing_keeps_its_own_name_and_code_but_not_anothers(self):
        self.assertEqual(self.post(self.edit_url(self.spa), nombre="Spa", codigo="spa").status_code, 200)
        errors = self.errors(self.post(self.edit_url(self.spa), nombre="Barbería", codigo="barberia"))
        self.assertEqual(errors["id_nombre"], "Ya existe un rubro con ese nombre.")
        self.assertEqual(errors["id_codigo"], "Ya existe un rubro con ese código.")

    def test_requires_add_and_change_permissions(self):
        self.assertEqual(self.get(CREATE_URL, user=self.viewer).status_code, 403)
        self.assertEqual(self.post(CREATE_URL, user=self.viewer).status_code, 403)
        self.assertEqual(self.post(self.edit_url(self.spa), user=self.viewer, nombre="Otro").status_code, 403)
        self.assertFalse(Rubro.objects.filter(codigo="peluqueria").exists())
        self.assertEqual(Rubro.objects.get(pk=self.spa.pk).nombre, "Spa")

    def test_without_session_answers_401_and_missing_industry_404(self):
        response = self.browser().post(CREATE_URL, self.payload(), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.get("/admin/tenancy/rubro/999999/change/modal/").status_code, 404)

    def test_old_django_pages_redirect_to_the_list(self):
        browser = self.browser(self.superuser)
        for url in ("/admin/tenancy/rubro/add/", f"/admin/tenancy/rubro/{self.spa.pk}/change/",
                    f"/admin/tenancy/rubro/{self.spa.pk}/", f"/admin/tenancy/rubro/{self.spa.pk}/delete/"):
            with self.subTest(url=url):
                self.assertRedirects(browser.get(url, follow=True), LIST_URL)

    def test_posting_to_old_django_pages_changes_nothing(self):
        browser = self.browser(self.superuser)
        browser.post("/admin/tenancy/rubro/add/", self.payload())
        browser.post(f"/admin/tenancy/rubro/{self.spa.pk}/delete/", {"post": "yes"})
        self.assertFalse(Rubro.objects.filter(codigo="peluqueria").exists())
        self.assertTrue(Rubro.objects.filter(pk=self.spa.pk).exists())
