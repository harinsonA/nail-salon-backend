import uuid
from datetime import timedelta

from django.test import Client as Browser
from django.urls import reverse
from django.utils import timezone

from apis.v1.sync.serializers import ClientSerializer
from apps.clients.models import Cliente
from apps.profiles.models import Perfil
from apps.tenancy.models import Negocio
from tests.apis.base import ApiTestCase

Rol = Perfil.Rol


class ClientsApiTests(ApiTestCase):
    esquema = "api_clients"
    dominio = "api-clients.localhost"

    def create(self, key=None, **data):
        headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        body = {"first_name": "Ana", "phone_prefix": "+56", **data}
        return self.api_client.post(reverse("api_clients"), body, format="json", **headers)

    def edit(self, client, key=None, **data):
        headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        url = reverse("api_client", kwargs={"pk": client.pk})
        return self.api_client.patch(url, data, format="json", **headers)

    def version(self, client):
        client.refresh_from_db()
        return ClientSerializer(client).data["modified"]

    def test_every_role_creates_a_client_with_the_web_rules(self):
        for number, rol in enumerate((Rol.PROPIETARIO, Rol.ENCARGADO, Rol.COLABORADOR)):
            with self.subTest(rol=rol):
                self.log_in_as(rol)
                response = self.create(
                    first_name=f"Ana {rol}",
                    first_surname="Rojas",
                    second_surname="Pérez",
                    phone_prefix="+56",
                    phone=f"9 1234 56{number:02d}",
                    email=f"ANA.{rol}@correo.cl",
                    notas="Alérgica",
                )
                self.assertEqual(response.status_code, 201, response.content)
                data = response.json()
                self.assertTrue(data["message"].startswith("Cliente Ana"))
                client = Cliente.objects.get(pk=data["client"]["id"])
                self.assertEqual(client.estado, Cliente.EstadoChoices.ACTIVO)
                self.assertEqual(client.apellido, "Rojas Pérez")
                self.assertTrue(client.telefono.startswith("+569"))
                self.assertEqual(client.email, f"ana.{rol}@correo.cl")
                self.assertEqual(data["client"]["telefono"], client.telefono)

    def test_overdue_business_pauses_clients_for_managers_only(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=Negocio.Estado.MOROSO)
        for rol in (Rol.PROPIETARIO, Rol.ENCARGADO):
            with self.subTest(rol=rol):
                self.log_in_as(rol)
                self.assertApiError(self.create(first_name=f"Ana {rol}"), 402, "payment_pending")
        self.assertFalse(Cliente.objects.exists())
        self.log_in_as(Rol.COLABORADOR)
        self.assertEqual(self.create(first_name="Ana").status_code, 201)

    def test_create_returns_the_form_errors_with_api_names(self):
        self.log_in_as(Rol.COLABORADOR)
        Cliente.objects.create(nombre="Otra", email="ana@correo.cl", telefono="+56912345678")
        response = self.create(
            first_name="",
            second_surname="Pérez",
            phone_prefix="+56",
            phone="9 1234 5678",
            email="ana@correo.cl",
            pais="CL",
            tipo_identificador_nacional="rut",
            identificador_nacional="11.111.111-2",
        )
        self.assertApiError(response, 400, "invalid_data")
        fields = response.json()["fields"]
        self.assertIn("first_name", fields)
        self.assertIn("first_surname", fields)
        self.assertEqual(fields["phone"], ["Ese teléfono ya lo usa otro cliente."])
        self.assertEqual(fields["email"], ["Ese correo ya lo usa otro cliente."])
        self.assertIn("identificador_nacional", fields)

    def test_same_codigo_app_does_not_duplicate(self):
        self.log_in_as(Rol.ENCARGADO)
        codigo = str(uuid.uuid4())
        first = self.create(codigo_app=codigo)
        second = self.create(codigo_app=codigo, first_name="Otra")
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(second.status_code, 200, second.content)
        self.assertEqual(first.json()["client"]["id"], second.json()["client"]["id"])
        self.assertEqual(Cliente.objects.filter(codigo_app=codigo).count(), 1)

    def test_edit_changes_only_what_was_sent_and_can_deactivate(self):
        self.log_in_as(Rol.COLABORADOR)
        client = Cliente.objects.create(
            nombre="Ana María", apellido="Rojas", telefono="+56912345678", email="ana@correo.cl", notas="Nota"
        )
        response = self.edit(client, estado="inactivo", second_surname="Pérez", version=self.version(client))
        self.assertEqual(response.status_code, 200, response.content)
        client.refresh_from_db()
        self.assertEqual(client.estado, Cliente.EstadoChoices.INACTIVO)
        self.assertEqual(client.nombre, "Ana María")
        self.assertEqual(client.apellido, "Rojas Pérez")
        self.assertEqual(client.telefono, "+56912345678")
        self.assertEqual(client.notas, "Nota")
        self.assertEqual(response.json()["client"]["estado"], "inactivo")
        self.assertEqual(response.json()["message"], "Cliente Ana María Rojas Pérez actualizado exitosamente.")

    def test_edit_with_an_old_version_is_a_conflict(self):
        self.log_in_as(Rol.PROPIETARIO)
        client = Cliente.objects.create(nombre="Ana")
        old = self.version(client)
        Cliente.objects.filter(pk=client.pk).update(modified=timezone.now() + timedelta(seconds=5))
        self.assertApiError(self.edit(client, notas="Nueva", version=old), 409, "conflict")
        client.refresh_from_db()
        self.assertIsNone(client.notas)

    def test_a_repeated_idempotency_key_on_edit_answers_the_same_without_conflict(self):
        self.log_in_as(Rol.ENCARGADO)
        client = Cliente.objects.create(nombre="Ana", telefono="+56911112222")
        version = self.version(client)
        first = self.edit(client, key="clave-1", first_name="Anita", version=version)
        second = self.edit(client, key="clave-1", first_name="Anita", version=version)
        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(second.status_code, 200, second.content)
        self.assertEqual(first.json(), second.json())
        third = self.edit(client, key="clave-2", first_name="Anita", version=version)
        self.assertApiError(third, 409, "conflict")

    def test_a_repeated_idempotency_key_on_create_answers_the_same(self):
        self.log_in_as(Rol.COLABORADOR)
        first = self.create(key="clave-1", codigo_app=str(uuid.uuid4()))
        second = self.create(key="clave-1", codigo_app=str(uuid.uuid4()))
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(second.status_code, 201, second.content)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(Cliente.objects.filter(nombre="Ana").count(), 1)

    def test_edit_keeps_its_own_phone_and_email_but_not_others(self):
        self.log_in_as(Rol.ENCARGADO)
        client = Cliente.objects.create(nombre="Ana", telefono="+56912345678", email="ana@correo.cl")
        Cliente.objects.create(nombre="Otra", telefono="+56987654321")
        self.assertEqual(self.edit(client, notas="Hola").status_code, 200)
        response = self.edit(client, phone="987654321")
        self.assertApiError(response, 400, "invalid_data")
        self.assertEqual(response.json()["fields"]["phone"], ["Ese teléfono ya lo usa otro cliente."])

    def test_edit_of_a_missing_client_is_not_found(self):
        self.log_in_as(Rol.PROPIETARIO)
        client = Cliente.objects.create(nombre="Ana")
        client.delete()
        self.assertApiError(self.edit(client, notas="x"), 404, "not_found")

    def test_web_still_creates_and_edits_with_the_shared_form(self):
        user = self.make_user(Rol.PROPIETARIO)
        browser = Browser(HTTP_HOST=self.dominio)
        browser.force_login(user)
        data = {"first_name": "Web", "country_phone_prefix": "+56", "phone": "911112222", "status": "on"}
        response = browser.post(reverse("client_create_modal"), data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200, response.content)
        client = Cliente.objects.get(nombre="Web")
        response = browser.get(reverse("client_detail_modal", kwargs={"pk": client.pk}))
        self.assertContains(response, "911112222")
