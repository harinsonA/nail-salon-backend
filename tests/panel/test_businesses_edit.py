import re

from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import (
    Dominio,
    Negocio,
    NegocioDireccion,
    Persona,
    PersonaCorreo,
    Rubro,
)

User = get_user_model()

PANEL = "admin.localhost"
ADDRESS_FIELDS = [
    "calle",
    "numero",
    "complemento",
    "codigo_postal",
    "comuna",
    "ciudad",
    "region",
    "pais",
    "referencia",
    "es_principal",
]


def address_rows(prefix, rows):
    data = {
        f"{prefix}-TOTAL_FORMS": len(rows),
        f"{prefix}-INITIAL_FORMS": sum(1 for row in rows if row.get("id")),
        f"{prefix}-MIN_NUM_FORMS": 0,
        f"{prefix}-MAX_NUM_FORMS": 1000,
    }
    for index, row in enumerate(rows):
        for field, value in row.items():
            if value is False or value is None:
                continue
            data[f"{prefix}-{index}-{field}"] = "on" if value is True else value
    return data


def address_row(address, **changes):
    return {
        "id": address.pk,
        **{field: getattr(address, field) for field in ADDRESS_FIELDS},
        **changes,
    }


class BusinessEditTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(
            schema_name=get_public_schema_name(), nombre="Hi Agenda"
        )
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
        cls.barber = Rubro.objects.get(codigo="barberia")
        cls.nails = Rubro.objects.get(codigo="unas")
        cls.owner = Persona.objects.create(nombres="Carlos", apellidos="Rojas")
        PersonaCorreo.objects.create(
            persona=cls.owner,
            correo="carlos@elcorte.cl",
            etiqueta="acceso",
            es_principal=True,
        )
        cls.superuser = User.objects.create_superuser(username="admin", password="x")
        cls.business = Negocio.objects.create(
            schema_name="el_corte",
            nombre="El Corte",
            titular=cls.owner,
            rubro=cls.barber,
            estado=Negocio.Estado.ACTIVO,
            notas_internas="Cliente desde 2025",
            creado_por=cls.superuser,
        )
        Dominio.objects.create(
            domain="el-corte.localhost", tenant=cls.business, is_primary=True
        )
        cls.local = NegocioDireccion.objects.create(
            negocio=cls.business,
            calle="Av. Providencia",
            numero="1234",
            es_principal=True,
        )
        cls.branch = NegocioDireccion.objects.create(
            negocio=cls.business, calle="Los Leones", numero="50"
        )
        cls.preparing = Negocio.objects.create(
            schema_name="nuevo",
            nombre="Nuevo",
            titular=Persona.objects.create(nombres="Ana"),
            error_preparacion="RuntimeError: sin espacio en disco",
        )
        cls.staff = User.objects.create_user(
            username="staff", password="x", is_staff=True
        )
        cls.staff.user_permissions.add(
            *Permission.objects.filter(codename__in=["view_negocio", "change_negocio"])
        )

    def setUp(self):
        connection.set_schema_to_public()

    def browser(self, user=None):
        browser = Client(HTTP_HOST=PANEL)
        browser.force_login(user or self.superuser)
        return browser

    def url(self, business=None):
        return f"/admin/tenancy/negocio/{(business or self.business).pk}/change/"

    def post(self, addresses=None, user=None, **changes):
        rows = (
            [address_row(self.local), address_row(self.branch)]
            if addresses is None
            else addresses
        )
        data = {
            "rubro": self.barber.pk,
            "pais": "CL",
            "zona_horaria": "America/Santiago",
            "notas_internas": "Cliente desde 2025",
            **changes,
            **address_rows("direcciones", rows),
        }
        return self.browser(user).post(self.url(), data)

    def test_page_shows_the_information_and_the_sections(self):
        response = self.browser().get(self.url())
        self.assertTemplateUsed(response, "panel/businesses/form.html")
        html = response.content.decode()
        self.assertIn("Editar negocio · El Corte", html)
        for text in (
            "el-corte.localhost",
            "el_corte",
            "Carlos Rojas",
            "carlos@elcorte.cl",
            "Activo desde el",
            "por admin",
        ):
            with self.subTest(text=text):
                self.assertIn(text, html)
        for tab in ("basic", "addresses", "notes", "actions"):
            self.assertIn(f'data-bs-target="#business-pane-{tab}"', html)
        for field in ("nombre", "subdominio", "esquema", "titular", "correo"):
            with self.subTest(field=field):
                self.assertNotIn(f'name="{field}"', html)
        self.assertRegex(html, rf'<option value="{self.barber.pk}" selected>')
        self.assertIn('name="direcciones-TOTAL_FORMS" value="2"', html)
        self.assertRegex(html, r'name="direcciones-0-calle" value="Av. Providencia"')
        self.assertIn("Guardar cambios", html)

    def test_subdomain_opens_the_business_in_a_new_tab(self):
        browser = Client(HTTP_HOST=f"{PANEL}:8000")
        browser.force_login(self.superuser)
        html = browser.get(self.url()).content.decode()
        self.assertRegex(
            html,
            r'href="http://el-corte\.localhost:8000/" class="icon-link-button" target="_blank" rel="noopener noreferrer"',
        )
        self.assertIn('aria-label="Abrir el negocio en una pestaña nueva"', html)

    def test_owner_password_action_opens_a_modal(self):
        response = self.browser().get(self.url())
        url = f"/admin/tenancy/negocio/{self.business.pk}/clave-propietario/"
        self.assertContains(response, f'class="btn btn-sm btn-outline-primary bs-modal" data-form-url="{url}"')
        self.assertNotContains(response, f'href="{url}"')
        self.assertContains(response, 'id="modal"')
        self.assertContains(
            response, "initializeActionModal('#modal', { onDone: () => window.location.reload() });"
        )
        status = f"/admin/tenancy/negocio/{self.business.pk}/estado/"
        self.assertContains(response, f'class="btn btn-sm btn-outline-primary bs-modal" data-form-url="{status}"')
        unlock = f"/admin/tenancy/negocio/{self.business.pk}/desbloquear-propietario/"
        self.assertContains(response, f'class="btn btn-sm btn-outline-primary bs-modal" data-form-url="{unlock}"')

    def test_actions_follow_the_status(self):
        active = self.browser().get(self.url()).context["actions"]
        self.assertEqual(
            [action["label"] for action in active],
            ["Restablecer clave del propietario", "Desbloquear propietario", "Cambiar estado", "Ver historial"],
        )
        self.assertEqual(
            active[-1]["link"], f"/admin/tenancy/negocio/{self.business.pk}/history/"
        )
        preparing = self.browser().get(self.url(self.preparing))
        self.assertEqual(
            [action["label"] for action in preparing.context["actions"]],
            ["Reparar alta", "Cambiar estado", "Ver historial"],
        )
        self.assertContains(preparing, "La preparación falló")
        self.assertContains(preparing, "sin espacio en disco")
        self.assertContains(preparing, "Falló desde el")
        self.assertContains(self.browser().get(self.url()), "Activo desde el")

    def selected_country(self):
        html = self.browser().get(self.url()).content.decode()
        select = re.search(r'<select name="pais".*?</select>', html, re.DOTALL).group(0)
        return re.findall(r'<option value="(\w+)" selected>', select)

    def test_country_defaults_to_chile_only_when_empty(self):
        self.assertEqual(self.selected_country(), ["CL"])
        self.business.pais = "PE"
        self.business.save()
        self.assertEqual(self.selected_country(), ["PE"])

    def test_updates_industry_country_time_zone_and_notes(self):
        response = self.post(
            rubro=self.nails.pk,
            pais="PE",
            zona_horaria="America/Lima",
            notas_internas="  Paga el día 5 ",
        )
        self.assertRedirects(response, self.url(), fetch_redirect_response=False)
        self.business.refresh_from_db()
        self.assertEqual(
            (
                self.business.rubro,
                self.business.pais,
                self.business.zona_horaria,
                self.business.notas_internas,
            ),
            (self.nails, "PE", "America/Lima", "Paga el día 5"),
        )
        self.assertEqual(
            self.business.history.first().history_change_reason,
            "Edición desde el panel",
        )
        log = LogEntry.objects.filter(
            object_id=str(self.business.pk), content_type__model="negocio"
        ).latest("action_time")
        self.assertEqual(log.action_flag, CHANGE)
        self.assertIn("Rubro", log.change_message)
        self.assertNotIn("Direcciones", log.change_message)

    def test_read_only_fields_cannot_be_changed(self):
        self.post(
            nombre="Otro",
            subdominio="otro",
            esquema="otro",
            titular=Persona.objects.create(nombres="X").pk,
            correo="x@x.cl",
        )
        self.business.refresh_from_db()
        self.assertEqual(
            (self.business.nombre, self.business.schema_name, self.business.titular),
            ("El Corte", "el_corte", self.owner),
        )
        self.assertTrue(
            Dominio.objects.filter(
                domain="el-corte.localhost", tenant=self.business
            ).exists()
        )

    def test_manages_addresses_with_a_single_main_one(self):
        rows = [
            address_row(self.local, es_principal=False, DELETE=True),
            address_row(self.branch, es_principal=False),
            {
                "calle": "Psje. Los Ñandúes",
                "numero": "45",
                "pais": "CL",
                "es_principal": True,
            },
        ]
        self.assertRedirects(
            self.post(addresses=rows), self.url(), fetch_redirect_response=False
        )
        self.assertFalse(NegocioDireccion.objects.filter(pk=self.local.pk).exists())
        new = self.business.direcciones.get(calle="Psje. Los Ñandúes")
        self.assertEqual(
            list(self.business.direcciones.filter(es_principal=True)), [new]
        )
        log = LogEntry.objects.filter(
            object_id=str(self.business.pk), content_type__model="negocio"
        ).latest("action_time")
        self.assertIn("Direcciones", log.change_message)

    def test_validates_fields_and_marks_the_sections(self):
        rows = [
            address_row(self.local, calle="Calle 5"),
            address_row(self.branch, es_principal=True),
        ]
        response = self.post(
            addresses=rows, rubro="", pais="", notas_internas="x" * 251
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["sections_with_errors"], ["basic", "addresses", "notes"]
        )
        self.assertIn("rubro", response.context["form"].errors)
        self.assertIn("pais", response.context["form"].errors)
        addresses = response.context["addresses"]
        self.assertIn("caracteres alfabéticos", addresses.forms[0].errors["calle"][0])
        self.assertContains(response, "is-invalid")
        self.business.refresh_from_db()
        self.assertEqual(self.business.rubro, self.barber)

    def test_only_one_main_address(self):
        rows = [address_row(self.local), address_row(self.branch, es_principal=True)]
        response = self.post(addresses=rows)
        self.assertEqual(
            response.context["addresses"].non_form_errors(),
            ["Solo puede haber una dirección principal."],
        )
        self.assertEqual(response.context["sections_with_errors"], ["addresses"])

    def test_keeps_an_inactive_industry_selectable(self):
        retired = Rubro.objects.create(codigo="antiguo", nombre="Antiguo", activo=False)
        Negocio.objects.filter(pk=self.business.pk).update(rubro=retired)
        response = self.browser().get(self.url())
        self.assertRegex(
            response.content.decode(), rf'<option value="{retired.pk}" selected>'
        )
        self.assertRedirects(
            self.post(rubro=retired.pk), self.url(), fetch_redirect_response=False
        )

    def test_only_superusers_edit_and_missing_businesses_404(self):
        self.assertEqual(self.browser(self.staff).get(self.url()).status_code, 403)
        self.assertEqual(
            self.post(user=self.staff, notas_internas="cambio").status_code, 403
        )
        self.business.refresh_from_db()
        self.assertEqual(self.business.notas_internas, "Cliente desde 2025")
        self.assertEqual(
            self.browser().get("/admin/tenancy/negocio/999999/change/").status_code, 404
        )
        public = Negocio.objects.get(schema_name=get_public_schema_name())
        self.assertEqual(
            self.browser()
            .get(f"/admin/tenancy/negocio/{public.pk}/change/")
            .status_code,
            404,
        )

    def test_shows_the_national_identifier_of_the_owner(self):
        html = self.browser().get(self.url()).content.decode()
        for label in ("País del titular", "Tipo de identificador nacional", "Identificador nacional"):
            self.assertRegex(html, rf'{label}</span>\s*<span class="readonly-info__value">—</span>')
        Persona.objects.filter(pk=self.owner.pk).update(
            pais="VE", tipo_identificador_nacional="cedula", identificador_nacional="V-12345678"
        )
        html = self.browser().get(self.url()).content.decode()
        for label, value in (
            ("País del titular", "Venezuela"),
            ("Tipo de identificador nacional", "Cédula de identidad"),
            ("Identificador nacional", "V-12345678"),
        ):
            with self.subTest(label=label):
                self.assertRegex(html, rf'{label}</span>\s*<span class="readonly-info__value">{value}</span>')
