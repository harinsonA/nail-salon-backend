from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.test import Client, TestCase
from django_tenants.utils import get_public_schema_name

from apps.tenancy.models import Dominio, Negocio, Persona, PersonaCorreo, PersonaDireccion, PersonaTelefono

User = get_user_model()

PANEL = "admin.localhost"
LIST_URL = "/admin/tenancy/persona/"
CREATE_URL = "/admin/tenancy/persona/add/modal/"


class PersonCreateModalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(schema_name=get_public_schema_name(), nombre="Hi Agenda")
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
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

    def payload(self, **changes):
        data = {
            "first_name": "Ana",
            "second_name": "",
            "first_surname": "",
            "second_surname": "",
            "email": "",
            "country_phone_prefix": "+56",
            "phone": "",
            "phone_type": "movil",
            "notes": "",
            "street": "",
            "number": "",
            "complement": "",
            "postal_code": "",
            "commune": "",
            "city": "",
            "region": "",
            "country": "CL",
            "reference": "",
        }
        data.update(changes)
        return {key: value for key, value in data.items() if value is not None}

    def post(self, user=None, **changes):
        return self.browser(user or self.superuser).post(
            CREATE_URL, self.payload(**changes), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def errors(self, response):
        self.assertEqual(response.status_code, 400)
        return {error["id_element"]: error["error"] for error in response.json()["errors"]}

    def test_modal_has_both_tabs(self):
        response = self.browser(self.superuser).get(CREATE_URL, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertTemplateUsed(response, "panel/people/person_modal.html")
        html = response.content.decode()
        self.assertIn("Nueva persona", html)
        self.assertIn('data-bs-target="#person-pane-basic"', html)
        self.assertIn('data-bs-target="#person-pane-address"', html)
        self.assertRegex(html, r'<option value="\+56" selected>')
        self.assertRegex(html, r'<option value="CL" selected>')

    def test_creates_a_person_with_email_phone_and_address(self):
        response = self.post(
            first_name="  Ana ",
            second_name="María",
            first_surname="Rojas",
            second_surname="Pérez",
            email=" Ana.Rojas@Ejemplo.com ",
            phone="9 1234-5678",
            has_whatsapp="on",
            notes="Prefiere WhatsApp.",
            street="Av. Providencia",
            number="1234",
            complement="Depto 502",
            commune="Providencia",
            city="Santiago",
            region="Metropolitana",
            postal_code="7500000",
            reference="Frente a la plaza",
        )
        self.assertEqual(response.json()["message"], "Persona Ana María Rojas Pérez creada exitosamente.")
        person = Persona.objects.get(nombres="Ana María")
        self.assertEqual((person.apellidos, person.notas), ("Rojas Pérez", "Prefiere WhatsApp."))
        email = PersonaCorreo.objects.get(persona=person)
        self.assertEqual((email.correo, email.es_principal), ("ana.rojas@ejemplo.com", True))
        phone = PersonaTelefono.objects.get(persona=person)
        self.assertEqual(
            (phone.codigo_pais, phone.numero, phone.tipo, phone.tiene_whatsapp, phone.es_principal),
            ("+56", "912345678", "movil", True, True),
        )
        address = PersonaDireccion.objects.get(persona=person)
        self.assertEqual(
            (address.calle, address.numero, address.complemento, address.comuna, address.ciudad, address.region),
            ("Av. Providencia", "1234", "Depto 502", "Providencia", "Santiago", "Metropolitana"),
        )
        self.assertEqual((address.pais, address.codigo_postal, address.referencia), ("CL", "7500000", "Frente a la plaza"))
        self.assertTrue(address.es_principal)
        self.assertEqual(person.history.first().history_change_reason, "Alta desde el panel")
        log = LogEntry.objects.get(object_id=str(person.pk), content_type__model="persona")
        self.assertEqual(log.action_flag, ADDITION)

    def test_only_the_first_name_is_required(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        person = Persona.objects.get(nombres="Ana")
        self.assertEqual((person.apellidos, person.notas), ("", None))
        self.assertFalse(person.correos.exists())
        self.assertFalse(person.telefonos.exists())
        self.assertFalse(person.direcciones.exists())

    def test_name_rules(self):
        cases = {
            ("first_name", ""): "requerido",
            ("first_name", "Ana2"): "caracteres alfabéticos",
            ("second_name", "María!"): "caracteres alfabéticos",
            ("first_surname", "a" * 51): "50",
            ("second_surname", "Pérez"): None,
        }
        for (field, value), message in cases.items():
            with self.subTest(field=field, value=value):
                errors = self.errors(self.post(**{field: value}))
                if message:
                    self.assertIn(message, errors[f"id_{field}"])
                else:
                    self.assertEqual(errors["id_first_surname"], "Escribe el primer apellido antes del segundo.")

    def test_joined_names_cannot_exceed_the_model_length(self):
        errors = self.errors(self.post(first_name="a" * 50, second_name="b" * 50))
        self.assertIn("100", errors["id_second_name"])

    def test_phone_rules(self):
        cases = {
            "9 12a4 5678": "solo debe contener dígitos",
            "8 1234 5678": "prefijo",
            "9 1234 567": "8 dígitos",
            "1" * 16: "15 dígitos",
        }
        for phone, message in cases.items():
            with self.subTest(phone=phone):
                self.assertIn(message, self.errors(self.post(phone=phone))["id_phone"])

    def test_landline_skips_the_mobile_rules(self):
        self.assertEqual(self.post(phone="22 345 6789", phone_type="fijo").status_code, 200)
        phone = PersonaTelefono.objects.get(persona__nombres="Ana")
        self.assertEqual((phone.numero, phone.tipo, phone.tiene_whatsapp), ("223456789", "fijo", False))

    def test_invalid_email_and_long_note(self):
        errors = self.errors(self.post(email="ana@", notes="x" * 251))
        self.assertIn("id_email", errors)
        self.assertIn("250", errors["id_notes"])

    def test_address_needs_a_street_when_partially_filled(self):
        errors = self.errors(self.post(commune="Providencia"))
        self.assertEqual(errors["id_street"], "Escribe la calle para guardar la dirección.")
        self.assertFalse(Persona.objects.filter(nombres="Ana").exists())

    def test_country_must_be_one_of_the_list(self):
        self.assertIn("id_country", self.errors(self.post(street="Calle 1", country="ZZ")))

    def test_requires_add_permission_and_session(self):
        self.assertEqual(self.browser(self.viewer).get(CREATE_URL, HTTP_X_REQUESTED_WITH="XMLHttpRequest").status_code, 403)
        self.assertEqual(self.post(user=self.viewer).status_code, 403)
        response = self.browser().post(CREATE_URL, self.payload(), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 401)
        self.assertFalse(Persona.objects.filter(nombres="Ana").exists())

    def test_old_add_page_redirects_and_creates_nothing(self):
        browser = self.browser(self.superuser)
        self.assertRedirects(browser.get("/admin/tenancy/persona/add/", follow=True), LIST_URL)
        browser.post("/admin/tenancy/persona/add/", {"nombres": "Ana", "apellidos": "", "notas": ""})
        self.assertFalse(Persona.objects.filter(nombres="Ana").exists())
