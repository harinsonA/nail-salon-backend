import re

from django.contrib.admin.models import ADDITION, LogEntry
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
CONTACT_FIELDS = {
    "email": "email-correo",
    "country_phone_prefix": "phone-codigo_pais",
    "phone": "phone-numero",
    "phone_type": "phone-tipo",
    "has_whatsapp": "phone-tiene_whatsapp",
    "street": "address-calle",
    "number": "address-numero",
    "complement": "address-complemento",
    "postal_code": "address-codigo_postal",
    "commune": "address-comuna",
    "city": "address-ciudad",
    "region": "address-region",
    "country": "address-pais",
    "reference": "address-referencia",
}
CREATE_URL = "/admin/tenancy/persona/add/modal/"


class PersonCreateModalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(
            schema_name=get_public_schema_name(), nombre="Hi Agenda"
        )
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
        cls.superuser = User.objects.create_superuser(username="admin", password="x")
        cls.viewer = User.objects.create_user(
            username="viewer", password="x", is_staff=True
        )
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
            "national_id_country": "CL",
            "national_id_type": "rut",
            "national_id": "12.345.678-5",
            "first_name": "Ana",
            "second_name": "",
            "first_surname": "",
            "second_surname": "",
            "email": "ana@ejemplo.com",
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
        return {
            CONTACT_FIELDS.get(key, key): value
            for key, value in data.items()
            if value is not None
        }

    def post(self, user=None, **changes):
        return self.browser(user or self.superuser).post(
            CREATE_URL, self.payload(**changes), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def errors(self, response):
        self.assertEqual(response.status_code, 400)
        field_ids = {f"id_{name}": f"id_{key}" for key, name in CONTACT_FIELDS.items()}
        return {
            field_ids.get(error["id_element"], error["id_element"]): error["error"]
            for error in response.json()["errors"]
        }

    def test_modal_has_both_tabs(self):
        response = self.browser(self.superuser).get(
            CREATE_URL, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertTemplateUsed(response, "panel/people/person_modal.html")
        html = response.content.decode()
        self.assertIn("Nuevo propietario", html)
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
            phone="912345678",
            has_whatsapp="on",
            notes="Prefiere WhatsApp.",
            street="Av. Providencia",
            number="1234",
            complement="Depto. 502",
            commune="Providencia",
            city="Santiago",
            region="Metropolitana",
            postal_code="7500000",
            reference="Frente a la plaza",
        )
        self.assertEqual(
            response.json()["message"],
            "Propietario Ana María Rojas Pérez creado exitosamente.",
        )
        person = Persona.objects.get(nombres="Ana María")
        self.assertEqual(
            (person.apellidos, person.notas), ("Rojas Pérez", "Prefiere WhatsApp.")
        )
        email = PersonaCorreo.objects.get(persona=person)
        self.assertEqual(
            (email.correo, email.es_principal), ("ana.rojas@ejemplo.com", True)
        )
        phone = PersonaTelefono.objects.get(persona=person)
        self.assertEqual(
            (
                phone.codigo_pais,
                phone.numero,
                phone.tipo,
                phone.tiene_whatsapp,
                phone.es_principal,
            ),
            ("+56", "912345678", "movil", True, True),
        )
        address = PersonaDireccion.objects.get(persona=person)
        self.assertEqual(
            (
                address.calle,
                address.numero,
                address.complemento,
                address.comuna,
                address.ciudad,
                address.region,
            ),
            (
                "Av. Providencia",
                "1234",
                "Depto. 502",
                "Providencia",
                "Santiago",
                "Metropolitana",
            ),
        )
        self.assertEqual(
            (address.pais, address.codigo_postal, address.referencia),
            ("CL", "7500000", "Frente a la plaza"),
        )
        self.assertTrue(address.es_principal)
        self.assertEqual(
            person.history.first().history_change_reason, "Alta desde el panel"
        )
        log = LogEntry.objects.get(
            object_id=str(person.pk), content_type__model="persona"
        )
        self.assertEqual(log.action_flag, ADDITION)

    def test_only_the_identifier_first_name_and_email_are_required(self):
        response = self.post()
        self.assertEqual(response.status_code, 200)
        person = Persona.objects.get(nombres="Ana")
        self.assertEqual((person.apellidos, person.notas), ("", None))
        self.assertEqual(
            list(person.correos.values_list("correo", "es_principal")),
            [("ana@ejemplo.com", True)],
        )
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
                    self.assertEqual(
                        errors["id_first_surname"],
                        "Escribe el primer apellido antes del segundo.",
                    )

    def test_joined_names_cannot_exceed_the_model_length(self):
        errors = self.errors(self.post(first_name="a" * 50, second_name="b" * 50))
        self.assertIn("100", errors["id_second_name"])

    def test_phone_rules(self):
        cases = {
            "9 1234 5678": "solo contener números",
            "9-1234-5678": "solo contener números",
            "+56912345678": "solo contener números",
            "9123a5678": "solo contener números",
            "812345678": "prefijo",
            "91234567": "8 dígitos",
            "1" * 16: "15",
        }
        for phone, message in cases.items():
            with self.subTest(phone=phone):
                self.assertIn(message, self.errors(self.post(phone=phone))["id_phone"])

    def test_landline_skips_the_mobile_rules(self):
        self.assertEqual(
            self.post(phone="223456789", phone_type="fijo").status_code, 200
        )
        phone = PersonaTelefono.objects.get(persona__nombres="Ana")
        self.assertEqual(
            (phone.numero, phone.tipo, phone.tiene_whatsapp),
            ("223456789", "fijo", False),
        )

    def test_invalid_email_and_long_note(self):
        errors = self.errors(self.post(email="ana@", notes="x" * 251))
        self.assertIn("id_email", errors)
        self.assertIn("250", errors["id_notes"])

    def test_address_needs_a_street_when_partially_filled(self):
        errors = self.errors(self.post(commune="Providencia"))
        self.assertEqual(
            errors["id_street"], "Escribe la calle para guardar la dirección."
        )
        self.assertFalse(Persona.objects.filter(nombres="Ana").exists())

    def test_address_field_rules(self):
        cases = {
            ("street", "Calle 5"): "caracteres alfabéticos, espacios y puntos",
            ("street", "Av, Providencia"): "caracteres alfabéticos, espacios y puntos",
            ("commune", "Ñuñoa 2"): "caracteres alfabéticos",
            ("city", "Santiago!"): "caracteres alfabéticos",
            ("region", "Región-Metropolitana"): "caracteres alfabéticos",
            ("city", "Sto. Domingo"): "caracteres alfabéticos y espacios",
            ("complement", "Local #3"): "letras, números, espacios y puntos",
            ("complement", "Of-12"): "letras, números, espacios y puntos",
            ("reference", "Frente al 50%"): "letras, números y espacios",
            ("reference", "Frente a la pza."): "letras, números y espacios",
            ("reference", "Casa $ verde"): "letras, números y espacios",
            ("number", "12A"): "solo contener números",
            ("number", "12 34"): "solo contener números",
            ("postal_code", "750-0000"): "solo contener números",
        }
        for (field, value), message in cases.items():
            with self.subTest(field=field, value=value):
                errors = self.errors(
                    self.post(**{"street": "Avenida Providencia", field: value})
                )
                self.assertIn(message, errors[f"id_{field}"])

    def test_address_accepts_letters_and_numbers_where_allowed(self):
        response = self.post(
            street="Psje. Los Ñandúes",
            number="45",
            complement="Torre B dpto. 1203",
            postal_code="7750000",
            commune="Ñuñoa",
            city="Santiago",
            region="Metropolitana de Santiago",
            reference="Portón verde al lado del 47",
        )
        self.assertEqual(response.status_code, 200)
        address = PersonaDireccion.objects.get(persona__nombres="Ana")
        self.assertEqual(
            (address.calle, address.complemento),
            ("Psje. Los Ñandúes", "Torre B dpto. 1203"),
        )
        self.assertEqual(address.referencia, "Portón verde al lado del 47")

    def test_country_must_be_one_of_the_list(self):
        self.assertIn(
            "id_country", self.errors(self.post(street="Calle Uno", country="ZZ"))
        )

    def test_requires_add_permission_and_session(self):
        self.assertEqual(
            self.browser(self.viewer)
            .get(CREATE_URL, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
            .status_code,
            403,
        )
        self.assertEqual(self.post(user=self.viewer).status_code, 403)
        response = self.browser().post(
            CREATE_URL, self.payload(), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 401)
        self.assertFalse(Persona.objects.filter(nombres="Ana").exists())

    def test_old_add_page_redirects_and_creates_nothing(self):
        browser = self.browser(self.superuser)
        self.assertRedirects(
            browser.get("/admin/tenancy/persona/add/", follow=True), LIST_URL
        )
        browser.post(
            "/admin/tenancy/persona/add/",
            {"nombres": "Ana", "apellidos": "", "notas": ""},
        )
        self.assertFalse(Persona.objects.filter(nombres="Ana").exists())

    def test_identifier_goes_first_contact_has_its_own_tab_and_starts_empty(self):
        html = (
            self.browser(self.superuser)
            .get(CREATE_URL, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
            .content.decode()
        )
        basic, contact = html.split('id="person-pane-contact"')
        self.assertIn('data-bs-target="#person-pane-contact"', html)
        self.assertIn('name="email-correo"', contact)
        self.assertIn('name="phone-numero"', contact)
        self.assertNotIn('name="email-correo"', basic)
        self.assertIn('name="national_id_country"', basic)
        self.assertLess(basic.index('name="national_id_country"'), basic.index('name="first_name"'))
        self.assertLess(basic.index('name="national_id"'), basic.index('name="first_name"'))
        self.assertNotIn("El identificador nacional es opcional", basic)
        country = re.search(r'<select name="national_id_country".*?</select>', html, re.DOTALL)
        self.assertNotIn("selected", country.group(0).replace('value="" selected', ""))
        self.assertIn('data-national-id-types="', country.group(0))
        self.assertRegex(html, r'<select name="national_id_type"[^>]*disabled')

    def test_saves_the_national_identifier_normalized(self):
        self.assertEqual(
            self.post(
                national_id_country="CL",
                national_id_type="rut",
                national_id="12.345.678-5",
            ).status_code,
            200,
        )
        person = Persona.objects.get(nombres="Ana")
        self.assertEqual(
            (person.pais, person.tipo_identificador_nacional, person.identificador_nacional),
            ("CL", "rut", "12345678-5"),
        )

    def test_the_three_identifier_fields_are_mandatory(self):
        empty = self.errors(self.post(national_id_country="", national_id_type="", national_id=""))
        self.assertEqual(empty["id_national_id_country"], "Elige el país del identificador nacional.")
        self.assertEqual(empty["id_national_id_type"], "Elige el tipo de identificador nacional.")
        self.assertEqual(empty["id_national_id"], "Escribe el identificador nacional del tipo elegido.")
        country_only = self.errors(self.post(national_id_country="VE", national_id_type="", national_id=""))
        self.assertNotIn("id_national_id_country", country_only)
        self.assertEqual(set(country_only) & {"id_national_id_type", "id_national_id"}, {"id_national_id_type", "id_national_id"})
        self.assertFalse(Persona.objects.exists())

    def test_type_and_number_go_together(self):
        without_number = self.errors(self.post(national_id_country="CL", national_id_type="rut", national_id=""))
        self.assertEqual(without_number["id_national_id"], "Escribe el identificador nacional del tipo elegido.")
        without_type = self.errors(self.post(national_id_country="", national_id_type="", national_id="12345678-5"))
        self.assertEqual(without_type["id_national_id_type"], "Elige el tipo de identificador nacional.")
        self.assertEqual(without_type["id_national_id_country"], "Elige el país del identificador nacional.")
        self.assertFalse(Persona.objects.exists())

    def test_the_number_follows_the_rules_of_its_country(self):
        errors = self.errors(
            self.post(national_id_country="CL", national_id_type="rut", national_id="12.345.678-9")
        )
        self.assertIn("dígito verificador", errors["id_national_id"])

    def test_the_type_must_belong_to_the_country(self):
        errors = self.errors(
            self.post(national_id_country="CL", national_id_type="curp", national_id="BOXW310820HNERXN09")
        )
        self.assertIn("id_national_id_type", errors)

    def test_the_email_is_mandatory(self):
        for email, message in (("", "Escribe el correo del propietario."), ("ana", "correo")):
            with self.subTest(email=email):
                errors = self.errors(self.post(email=email))
                self.assertIn(message, errors["id_email"])
        self.assertFalse(Persona.objects.exists())
