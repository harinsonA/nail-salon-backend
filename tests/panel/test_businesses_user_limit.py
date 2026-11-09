from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.db import connection
from django.test import Client
from django_tenants.utils import get_public_schema_name

from apps.profiles.models import Perfil
from apps.tenancy.models import Dominio, Negocio, Persona, PersonaCorreo, Rubro
from apps.tenancy.tasks import preparar_negocio
from tests.base import NegocioTestCase

User = get_user_model()

PANEL = "admin.localhost"
ADD_URL = "/admin/tenancy/negocio/add/"
LIST_AJAX_URL = "/admin/tenancy/negocio/list/"


class BusinessUserLimitTests(NegocioTestCase):
    esquema = "cupo"

    @classmethod
    def setUpTestData(cls):
        connection.set_schema_to_public()
        public = Negocio.objects.create(
            schema_name=get_public_schema_name(), nombre="Hi Agenda"
        )
        Dominio.objects.create(domain=PANEL, tenant=public, is_primary=True)
        cls.superuser = User.objects.create_superuser(username="admin", password="x")
        cls.barber = Rubro.objects.get(codigo="barberia")
        cls.owner = Persona.objects.create(nombres="Carlos", apellidos="Rojas")
        PersonaCorreo.objects.create(
            persona=cls.owner, correo="carlos@elcorte.cl", etiqueta="acceso"
        )
        connection.set_tenant(cls.negocio)
        for name, role in (
            ("carla", Perfil.Rol.PROPIETARIO),
            ("ana", Perfil.Rol.ENCARGADO),
            ("bea", Perfil.Rol.COLABORADOR),
        ):
            user = User.objects.create_user(
                username=name, email=f"{name}@correo.cl", password="x"
            )
            Perfil.objects.filter(user=user).update(rol=role)
        connection.set_schema_to_public()

    def setUp(self):
        super().setUp()
        connection.set_schema_to_public()
        self.negocio.refresh_from_db()

    def browser(self):
        browser = Client(HTTP_HOST=PANEL)
        browser.force_login(self.superuser)
        return browser

    def edit_url(self):
        return f"/admin/tenancy/negocio/{self.negocio.pk}/change/"

    def edit(self, **changes):
        data = {
            "rubro": self.barber.pk,
            "pais": "CL",
            "zona_horaria": "America/Santiago",
            "notas_internas": "",
            "direcciones-TOTAL_FORMS": 0,
            "direcciones-INITIAL_FORMS": 0,
            "direcciones-MIN_NUM_FORMS": 0,
            "direcciones-MAX_NUM_FORMS": 1000,
            **changes,
        }
        return self.browser().post(self.edit_url(), data)

    def create(self, **changes):
        data = {
            "nombre": "Barbería El Corte",
            "subdominio": "el-corte",
            "esquema": "el_corte",
            "titular": self.owner.pk,
            "correo": "carlos@elcorte.cl",
            "rubro": self.barber.pk,
            "pais": "CL",
            "zona_horaria": "America/Santiago",
            "notas_internas": "",
            "address-pais": "CL",
            **changes,
        }
        return self.browser().post(ADD_URL, data)

    def history_changes(self):
        rows = (
            self.browser()
            .get(
                f"/admin/tenancy/negocio/{self.negocio.pk}/history/list/",
                {"draw": 1, "start": 0, "length": 10},
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )
            .json()["data"]
        )
        return rows[0]["changes"]

    def list_row(self):
        rows = (
            self.browser()
            .get(
                LIST_AJAX_URL,
                {"draw": 1, "start": 0, "length": 10},
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )
            .json()["data"]
        )
        return next(row for row in rows if row["pk"] == self.negocio.pk)

    def test_new_business_form_starts_with_limit_one(self):
        response = self.browser().get(ADD_URL)
        self.assertContains(response, 'data-bs-target="#business-pane-users"')
        self.assertContains(response, 'name="limite_usuarios" value="1"')
        self.assertNotContains(response, 'name="sin_limite" class="form-check-input" id="id_sin_limite" checked')

    @mock.patch.object(preparar_negocio, "delay")
    def test_new_business_saves_the_limit_or_unlimited(self, enqueue):
        self.create(limite_usuarios="1")
        self.assertEqual(Negocio.objects.get(schema_name="el_corte").limite_usuarios, 1)
        self.create(
            subdominio="la-tijera", esquema="la_tijera", limite_usuarios="", sin_limite="on"
        )
        self.assertIsNone(Negocio.objects.get(schema_name="la_tijera").limite_usuarios)

    @mock.patch.object(preparar_negocio, "delay")
    def test_new_business_validates_the_limit(self, enqueue):
        cases = {
            "": "Escribe el límite de usuarios o marca «Sin límite».",
            "0": "El límite de usuarios debe ser al menos 1.",
            "dos": "debe solo contener números",
            "40000": "El límite de usuarios no puede superar 32.767.",
        }
        for value, message in cases.items():
            with self.subTest(value=value):
                response = self.create(limite_usuarios=value)
                self.assertEqual(response.status_code, 200)
                self.assertIn(message, response.context["form"].errors["limite_usuarios"][0])
                self.assertEqual(response.context["sections_with_errors"], ["users"])
        enqueue.assert_not_called()

    def test_existing_business_without_limit_shows_unlimited_checked(self):
        response = self.browser().get(self.edit_url())
        self.assertEqual(response.context["form"].initial["sin_limite"], True)
        self.assertContains(response, 'name="sin_limite" class="form-check-input" id="id_sin_limite" checked')
        self.assertContains(response, "Cuentas activas")
        self.assertContains(response, 'data-active-count="3"')

    def test_editing_the_limit_goes_to_the_history(self):
        self.edit(limite_usuarios="5")
        self.negocio.refresh_from_db()
        self.assertEqual(self.negocio.limite_usuarios, 5)
        self.assertIn(
            {"field": "Límite de usuarios", "old": "Sin límite", "new": "5"},
            self.history_changes(),
        )
        self.edit(sin_limite="on", limite_usuarios="5")
        self.negocio.refresh_from_db()
        self.assertIsNone(self.negocio.limite_usuarios)
        self.assertIn(
            {"field": "Límite de usuarios", "old": "5", "new": "Sin límite"},
            self.history_changes(),
        )

    def test_saving_below_the_active_accounts_is_allowed_with_a_warning(self):
        response = self.edit(limite_usuarios="1")
        self.assertRedirects(response, self.edit_url(), fetch_redirect_response=False)
        self.negocio.refresh_from_db()
        self.assertEqual(self.negocio.limite_usuarios, 1)
        texts = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertIn(
            "«Negocio cupo» tiene 3 cuentas activas y su límite es 1. "
            "Solo la propietaria podrá entrar hasta que desactive 2 cuentas.",
            texts,
        )

    def test_saving_within_the_limit_has_no_warning(self):
        response = self.edit(limite_usuarios="3")
        texts = [str(message) for message in get_messages(response.wsgi_request)]
        self.assertEqual(texts, ["«Negocio cupo» se actualizó exitosamente."])

    def test_list_shows_accounts_over_limit(self):
        self.assertEqual(
            (self.list_row()["users_label"], self.list_row()["over_limit"]),
            ("3 / sin límite", False),
        )
        Negocio.objects.filter(pk=self.negocio.pk).update(limite_usuarios=2)
        row = self.list_row()
        self.assertEqual((row["users_label"], row["over_limit"]), ("3 / 2", True))

    def test_list_without_schema_shows_a_dash(self):
        pending = Negocio.objects.create(
            schema_name="pendiente",
            nombre="Pendiente",
            titular=Persona.objects.create(nombres="Ana"),
            limite_usuarios=2,
        )
        rows = (
            self.browser()
            .get(LIST_AJAX_URL, {"draw": 1, "start": 0, "length": 10}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
            .json()["data"]
        )
        row = next(row for row in rows if row["pk"] == pending.pk)
        self.assertEqual((row["users_label"], row["over_limit"]), ("—", False))
