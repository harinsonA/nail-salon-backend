from django.contrib.admin.models import CHANGE, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import (
    Dominio,
    Negocio,
    Persona,
    PersonaCorreo,
    PersonaDireccion,
    PersonaTelefono,
)

User = get_user_model()

PANEL = "admin.localhost"
LIST_URL = "/admin/tenancy/persona/"
EMAIL_FIELDS = ["correo", "es_principal"]
PHONE_FIELDS = ["codigo_pais", "numero", "tipo", "tiene_whatsapp", "es_principal"]
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


def row(item, fields, **changes):
    return {"id": item.pk, **{field: getattr(item, field) for field in fields}, **changes}


def formset_data(prefix, rows):
    data = {
        f"{prefix}-TOTAL_FORMS": len(rows),
        f"{prefix}-INITIAL_FORMS": sum(1 for item in rows if item.get("id")),
        f"{prefix}-MIN_NUM_FORMS": 0,
        f"{prefix}-MAX_NUM_FORMS": 1000,
    }
    for index, item in enumerate(rows):
        for field, value in item.items():
            if value is False or value is None:
                continue
            data[f"{prefix}-{index}-{field}"] = "on" if value is True else value
    return data


class PersonEditModalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
        cls.person = Persona.objects.create(nombres="Carla Andrea", apellidos="Rojas Pérez", notas="Clienta antigua")
        cls.work_email = PersonaCorreo.objects.create(persona=cls.person, correo="carla@trabajo.cl", es_principal=True)
        cls.home_email = PersonaCorreo.objects.create(persona=cls.person, correo="carla@casa.cl")
        cls.mobile = PersonaTelefono.objects.create(
            persona=cls.person, codigo_pais="+56", numero="912345678", es_principal=True
        )
        cls.office = PersonaDireccion.objects.create(persona=cls.person, calle="Av. Providencia", numero="1234", es_principal=True)
        cls.home = PersonaDireccion.objects.create(persona=cls.person, calle="Los Leones", numero="50")
        cls.owner = Persona.objects.create(nombres="Carlos")
        cls.access_email = PersonaCorreo.objects.create(
            persona=cls.owner, correo="carlos@elcorte.cl", etiqueta="acceso", es_principal=True
        )
        cls.superuser = User.objects.create_superuser(username="admin", password="x")
        cls.viewer = User.objects.create_user(username="viewer", password="x", is_staff=True)
        cls.viewer.user_permissions.add(Permission.objects.get(codename="view_persona"))

    def setUp(self):
        connection.set_schema_to_public()

    def browser(self, user=None):
        browser = Client(HTTP_HOST=PANEL)
        if user:
            browser.force_login(user)
        return browser

    def url(self, person=None):
        return f"/admin/tenancy/persona/{(person or self.person).pk}/change/modal/"

    def current_rows(self, person):
        return {
            "emails": [row(item, EMAIL_FIELDS) for item in person.correos.order_by("pk")],
            "phones": [row(item, PHONE_FIELDS) for item in person.telefonos.order_by("pk")],
            "addresses": [row(item, ADDRESS_FIELDS) for item in person.direcciones.order_by("pk")],
        }

    def post(self, person=None, user=None, emails=None, phones=None, addresses=None, **basic):
        person = person or self.person
        rows = self.current_rows(person)
        data = {
            "national_id_country": "CL",
            "national_id_type": "rut",
            "national_id": "12.345.678-5",
            "first_name": "Carla",
            "second_name": "Andrea",
            "first_surname": "Rojas",
            "second_surname": "Pérez",
            "notes": "Clienta antigua",
            **basic,
            **formset_data("correos", rows["emails"] if emails is None else emails),
            **formset_data("telefonos", rows["phones"] if phones is None else phones),
            **formset_data("direcciones", rows["addresses"] if addresses is None else addresses),
        }
        return self.browser(user or self.superuser).post(
            self.url(person), data, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def errors(self, response):
        self.assertEqual(response.status_code, 400)
        return {error["id_element"]: error["error"] for error in response.json()["errors"]}

    def main_of(self, manager):
        return list(manager.filter(es_principal=True).values_list("pk", flat=True))

    def test_modal_loads_names_contacts_and_main_first(self):
        response = self.browser(self.superuser).get(self.url(), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTemplateUsed(response, "panel/people/person_edit_modal.html")
        html = response.content.decode()
        self.assertIn("Editar propietario · Carla Andrea Rojas Pérez", html)
        for name, value in (("first_name", "Carla"), ("second_name", "Andrea"), ("first_surname", "Rojas"), ("second_surname", "Pérez")):
            self.assertRegex(html, rf'name="{name}" value="{value}"')
        self.assertIn("Clienta antigua", html)
        for tab in ("basic", "emails", "phones", "addresses"):
            self.assertIn(f'data-bs-target="#person-pane-{tab}"', html)
        self.assertRegex(html, r'name="correos-0-correo" value="carla@trabajo.cl"')
        self.assertRegex(html, r'name="correos-0-es_principal"[^>]*checked')
        self.assertIn('name="correos-TOTAL_FORMS" value="2"', html)
        self.assertIn("correos-__prefix__-correo", html)
        self.assertIn('name="direcciones-1-calle"', html)

    def test_updates_names_and_note_and_logs_the_change(self):
        response = self.post(second_name="", second_surname="", notes="  Prefiere WhatsApp ")
        self.assertEqual(response.json()["message"], "Propietario Carla Rojas actualizado exitosamente.")
        self.person.refresh_from_db()
        self.assertEqual((self.person.nombres, self.person.apellidos, self.person.notas), ("Carla", "Rojas", "Prefiere WhatsApp"))
        self.assertEqual(self.person.history.first().history_change_reason, "Edición desde el panel")
        log = LogEntry.objects.filter(object_id=str(self.person.pk), content_type__model="persona").latest("action_time")
        self.assertEqual(log.action_flag, CHANGE)
        self.assertIn("Segundo nombre", log.change_message)
        self.assertNotIn("Correos", log.change_message)

    def test_marking_another_email_as_main_unmarks_the_previous_one(self):
        emails = [
            row(self.work_email, EMAIL_FIELDS, es_principal=False),
            row(self.home_email, EMAIL_FIELDS, es_principal=True),
        ]
        self.assertEqual(self.post(emails=emails).status_code, 200)
        self.assertEqual(self.main_of(self.person.correos), [self.home_email.pk])
        log = LogEntry.objects.filter(object_id=str(self.person.pk), content_type__model="persona").latest("action_time")
        self.assertIn("Correos", log.change_message)

    def test_adds_a_new_phone_and_makes_it_the_main_one(self):
        phones = [
            row(self.mobile, PHONE_FIELDS, es_principal=False),
            {"codigo_pais": "+56", "numero": "223456789", "tipo": "fijo", "tiene_whatsapp": False, "es_principal": True},
        ]
        self.assertEqual(self.post(phones=phones).status_code, 200)
        landline = self.person.telefonos.get(numero="223456789")
        self.assertEqual(self.main_of(self.person.telefonos), [landline.pk])
        self.assertEqual(self.person.telefonos.count(), 2)

    def test_adds_a_new_address_as_main(self):
        addresses = [
            row(self.office, ADDRESS_FIELDS, es_principal=False),
            row(self.home, ADDRESS_FIELDS),
            {"calle": "Psje. Los Ñandúes", "numero": "45", "pais": "CL", "es_principal": True},
        ]
        self.assertEqual(self.post(addresses=addresses).status_code, 200)
        new = self.person.direcciones.get(calle="Psje. Los Ñandúes")
        self.assertEqual(self.main_of(self.person.direcciones), [new.pk])

    def test_only_one_main_item_per_section(self):
        emails = [row(self.work_email, EMAIL_FIELDS), row(self.home_email, EMAIL_FIELDS, es_principal=True)]
        errors = self.errors(self.post(emails=emails))
        self.assertEqual(errors["id_correos-errors"], "Solo puede haber un correo principal.")
        self.assertEqual(self.main_of(self.person.correos), [self.work_email.pk])

    def test_a_section_with_items_needs_a_main_one(self):
        phones = [row(self.mobile, PHONE_FIELDS, es_principal=False)]
        addresses = [row(self.office, ADDRESS_FIELDS, es_principal=False), row(self.home, ADDRESS_FIELDS)]
        errors = self.errors(self.post(phones=phones, addresses=addresses))
        self.assertEqual(errors["id_telefonos-errors"], "Marca un teléfono como principal.")
        self.assertEqual(errors["id_direcciones-errors"], "Marca una dirección como principal.")

    def test_removes_items_and_moves_the_main_one(self):
        addresses = [
            row(self.office, ADDRESS_FIELDS, es_principal=False, DELETE=True),
            row(self.home, ADDRESS_FIELDS, es_principal=True),
        ]
        self.assertEqual(self.post(addresses=addresses).status_code, 200)
        self.assertEqual(list(self.person.direcciones.values_list("pk", flat=True)), [self.home.pk])
        self.assertEqual(self.main_of(self.person.direcciones), [self.home.pk])

    def test_removing_every_item_leaves_the_section_empty(self):
        phones = [row(self.mobile, PHONE_FIELDS, DELETE=True)]
        self.assertEqual(self.post(phones=phones).status_code, 200)
        self.assertFalse(self.person.telefonos.exists())

    def test_blank_new_rows_are_ignored(self):
        emails = [*self.current_rows(self.person)["emails"], {"correo": ""}]
        self.assertEqual(self.post(emails=emails).status_code, 200)
        self.assertEqual(self.person.correos.count(), 2)

    def test_rows_apply_the_field_rules(self):
        phones = [row(self.mobile, PHONE_FIELDS, numero="812345678")]
        addresses = [
            row(self.office, ADDRESS_FIELDS, calle="Calle 5"),
            row(self.home, ADDRESS_FIELDS, referencia="Frente al 50%"),
        ]
        emails = [row(self.work_email, EMAIL_FIELDS, correo="carla@"), row(self.home_email, EMAIL_FIELDS)]
        errors = self.errors(self.post(phones=phones, addresses=addresses, emails=emails, first_name="Carla2"))
        self.assertIn("caracteres alfabéticos", errors["id_first_name"])
        self.assertIn("prefijo", errors["id_telefonos-0-numero"])
        self.assertIn("caracteres alfabéticos, espacios y puntos", errors["id_direcciones-0-calle"])
        self.assertIn("letras, números y espacios", errors["id_direcciones-1-referencia"])
        self.assertIn("id_correos-0-correo", errors)
        self.mobile.refresh_from_db()
        self.assertEqual(self.mobile.numero, "912345678")

    def test_duplicated_email_or_phone_is_rejected(self):
        emails = [*self.current_rows(self.person)["emails"], {"correo": "Carla@Casa.cl"}]
        self.assertIn("id_correos-errors", self.errors(self.post(emails=emails)))
        phones = [*self.current_rows(self.person)["phones"], {"codigo_pais": "+56", "numero": "912345678", "tipo": "movil"}]
        self.assertIn("id_telefonos-errors", self.errors(self.post(phones=phones)))
        self.assertEqual(self.person.correos.count(), 2)

    def test_access_email_cannot_be_changed_or_removed(self):
        html = self.browser(self.superuser).get(self.url(self.owner), HTTP_X_REQUESTED_WITH="XMLHttpRequest").content.decode()
        self.assertRegex(html, r'name="correos-0-correo"[^>]*disabled')
        self.assertIn("correo de acceso de su negocio", html)
        self.assertEqual(html.count("formset-remove"), 3)
        changed = [row(self.access_email, EMAIL_FIELDS, correo="otro@correo.cl")]
        self.assertEqual(self.post(self.owner, emails=changed, first_name="Carlos", second_name="", first_surname="", second_surname="").status_code, 200)
        self.access_email.refresh_from_db()
        self.assertEqual(self.access_email.correo, "carlos@elcorte.cl")
        removed = [row(self.access_email, EMAIL_FIELDS, DELETE=True)]
        errors = self.errors(self.post(self.owner, emails=removed, first_name="Carlos", second_name="", first_surname="", second_surname=""))
        self.assertEqual(errors["id_correos-errors"], "El correo de acceso de su negocio no se puede quitar.")
        self.assertTrue(PersonaCorreo.objects.filter(pk=self.access_email.pk).exists())

    def test_requires_change_permission_and_session(self):
        self.assertEqual(self.browser(self.viewer).get(self.url(), HTTP_X_REQUESTED_WITH="XMLHttpRequest").status_code, 403)
        self.assertEqual(self.post(user=self.viewer, first_name="Otra").status_code, 403)
        response = self.browser().post(self.url(), {}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            self.browser(self.superuser).get("/admin/tenancy/persona/999999/change/modal/", HTTP_X_REQUESTED_WITH="XMLHttpRequest").status_code,
            404,
        )
        self.person.refresh_from_db()
        self.assertEqual(self.person.nombres, "Carla Andrea")

    def test_old_django_pages_redirect_and_change_nothing(self):
        browser = self.browser(self.superuser)
        for url in (f"/admin/tenancy/persona/{self.person.pk}/change/", f"/admin/tenancy/persona/{self.person.pk}/delete/"):
            with self.subTest(url=url):
                self.assertRedirects(browser.get(url, follow=True), LIST_URL)
        browser.post(f"/admin/tenancy/persona/{self.person.pk}/change/", {"nombres": "Otra"})
        browser.post(f"/admin/tenancy/persona/{self.person.pk}/delete/", {"post": "yes"})
        self.person.refresh_from_db()
        self.assertEqual(self.person.nombres, "Carla Andrea")

    def test_loads_the_saved_identifier_with_the_types_of_its_country(self):
        Persona.objects.filter(pk=self.person.pk).update(
            pais="MX", tipo_identificador_nacional="curp", identificador_nacional="BOXW310820HNERXN09"
        )
        html = self.browser(self.superuser).get(self.url(), HTTP_X_REQUESTED_WITH="XMLHttpRequest").content.decode()
        self.assertRegex(html, r'<option value="MX" selected>México</option>')
        self.assertRegex(html, r'<option value="curp" selected>CURP</option>')
        self.assertNotRegex(html, r'<select name="national_id_type"[^>]*disabled')
        self.assertRegex(html, r'name="national_id" value="BOXW310820HNERXN09"')

    def test_updates_the_identifier_and_does_not_let_it_be_cleared(self):
        response = self.post(national_id_country="VE", national_id_type="cedula", national_id="v-12.345.678")
        self.assertEqual(response.status_code, 200)
        self.person.refresh_from_db()
        self.assertEqual(
            (self.person.pais, self.person.tipo_identificador_nacional, self.person.identificador_nacional),
            ("VE", "cedula", "V-12345678"),
        )
        errors = self.errors(self.post(national_id_country="", national_id_type="", national_id=""))
        self.assertEqual(
            set(errors) & {"id_national_id_country", "id_national_id_type", "id_national_id"},
            {"id_national_id_country", "id_national_id_type", "id_national_id"},
        )
        self.person.refresh_from_db()
        self.assertEqual(self.person.identificador_nacional, "V-12345678")

    def test_edit_applies_the_same_identifier_rules(self):
        errors = self.errors(self.post(national_id_country="VE", national_id_type="cedula", national_id=""))
        self.assertEqual(errors["id_national_id"], "Escribe el identificador nacional del tipo elegido.")

    def test_at_least_one_email_must_remain(self):
        emails = [row(self.work_email, EMAIL_FIELDS, DELETE=True), row(self.home_email, EMAIL_FIELDS, DELETE=True)]
        errors = self.errors(self.post(emails=emails))
        self.assertEqual(errors["id_correos-errors"], "Debe tener al menos un correo.")
        self.assertEqual(self.person.correos.count(), 2)

    def test_existing_owners_without_identifier_must_complete_it(self):
        errors = self.errors(self.post(person=self.owner, first_name="Carlos", second_name="", first_surname="", second_surname="", national_id_country="", national_id_type="", national_id=""))
        self.assertIn("id_national_id_country", errors)
