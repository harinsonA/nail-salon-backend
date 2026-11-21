from datetime import timedelta
from decimal import Decimal

from django.test import Client as Browser
from django.urls import reverse
from django.utils import timezone

from apis.v1.sync.serializers import ServiceSerializer
from apps.profiles.models import Perfil
from apps.services.models import Categoria, Servicio
from apps.tenancy.models import Negocio
from tests.apis.base import ApiTestCase

Rol = Perfil.Rol


class ServicesApiTests(ApiTestCase):
    esquema = "api_services"
    dominio = "api-services.localhost"

    def setUp(self):
        super().setUp()
        self.category = Categoria.objects.create(nombre="Manos")

    def create(self, **data):
        body = {
            "categoria_id": self.category.pk,
            "nombre": "Esmaltado",
            "precio": 5000,
            "duracion_estimada": 30,
            **data,
        }
        return self.api_client.post(reverse("api_services"), body, format="json")

    def edit(self, service, **data):
        return self.api_client.patch(reverse("api_service", kwargs={"pk": service.pk}), data, format="json")

    def version(self, service):
        service.refresh_from_db()
        return ServiceSerializer(service).data["modified"]

    def service(self, **data):
        return Servicio.objects.create(
            **{"nombre": "Esmaltado", "precio": 5000, "categoria": self.category, "duracion_estimada": timedelta(minutes=30), **data}
        )

    def test_administration_creates_a_service_with_the_web_rules(self):
        for rol in (Rol.PROPIETARIO, Rol.ENCARGADO):
            with self.subTest(rol=rol):
                self.log_in_as(rol)
                response = self.create(nombre=f"Manicure {rol}", precio="15.000", duracion_estimada=60, descripcion="Con limado")
                self.assertEqual(response.status_code, 201, response.content)
                data = response.json()
                self.assertEqual(data["message"], f"Servicio Manicure {rol} creado exitosamente.")
                service = Servicio.objects.get(pk=data["service"]["id"])
                self.assertEqual(service.estado, Servicio.EstadoChoices.ACTIVO)
                self.assertEqual(service.precio, Decimal("15000"))
                self.assertEqual(service.duracion_estimada, timedelta(minutes=60))
                self.assertEqual(service.categoria, self.category)
                self.assertEqual(data["service"]["precio"], 15000)
                self.assertEqual(data["service"]["duracion_estimada"], 60)

    def test_collaborator_cannot_create_or_edit(self):
        service = self.service()
        self.log_in_as(Rol.COLABORADOR)
        self.assertApiError(self.create(), 403, "forbidden")
        self.assertApiError(self.edit(service, nombre="Otro"), 403, "forbidden")

    def test_overdue_business_pauses_the_routes(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=Negocio.Estado.MOROSO)
        self.log_in_as(Rol.ENCARGADO)
        self.assertApiError(self.create(), 402, "payment_pending")

    def test_create_returns_the_form_errors_with_api_names(self):
        self.log_in_as(Rol.PROPIETARIO)
        response = self.create(categoria_id=None, nombre="", precio="100.000.000", duracion_estimada=0)
        self.assertApiError(response, 400, "invalid_data")
        fields = response.json()["fields"]
        self.assertEqual(set(fields), {"categoria_id", "nombre", "precio", "duracion_estimada"})

    def test_edit_changes_only_what_was_sent(self):
        self.log_in_as(Rol.ENCARGADO)
        service = self.service(descripcion="Nota")
        response = self.edit(service, precio=7000, estado="inactivo", version=self.version(service))
        self.assertEqual(response.status_code, 200, response.content)
        service.refresh_from_db()
        self.assertEqual(service.precio, Decimal("7000"))
        self.assertEqual(service.estado, Servicio.EstadoChoices.INACTIVO)
        self.assertEqual(service.nombre, "Esmaltado")
        self.assertEqual(service.descripcion, "Nota")
        self.assertEqual(service.duracion_estimada, timedelta(minutes=30))
        self.assertEqual(response.json()["message"], "Servicio Esmaltado actualizado exitosamente.")

    def test_cannot_activate_a_service_with_an_inactive_category(self):
        self.log_in_as(Rol.PROPIETARIO)
        self.category.estado = Categoria.EstadoChoices.INACTIVO
        self.category.save()
        service = self.service(estado=Servicio.EstadoChoices.INACTIVO)
        response = self.edit(service, estado="activo")
        self.assertApiError(response, 400, "invalid_data")
        self.assertEqual(
            response.json()["fields"]["categoria_id"], ["No puedes activar un servicio con una categoria inactiva."]
        )
        service.refresh_from_db()
        self.assertEqual(service.estado, Servicio.EstadoChoices.INACTIVO)

    def test_edit_with_an_old_version_is_a_conflict(self):
        self.log_in_as(Rol.PROPIETARIO)
        service = self.service()
        old = self.version(service)
        Servicio.objects.filter(pk=service.pk).update(modified=timezone.now() + timedelta(seconds=5))
        self.assertApiError(self.edit(service, nombre="Otro", version=old), 409, "conflict")

    def test_edit_of_a_missing_service_is_not_found(self):
        self.log_in_as(Rol.PROPIETARIO)
        service = self.service()
        service.delete()
        self.assertApiError(self.edit(service, nombre="Otro"), 404, "not_found")

    def test_web_still_blocks_activation_with_an_inactive_category(self):
        user = self.make_user(Rol.PROPIETARIO)
        browser = Browser(HTTP_HOST=self.dominio)
        browser.force_login(user)
        self.category.estado = Categoria.EstadoChoices.INACTIVO
        self.category.save()
        service = self.service(estado=Servicio.EstadoChoices.INACTIVO)
        response = browser.get(reverse("service_detail_modal", kwargs={"pk": service.pk}))
        self.assertContains(response, "Esmaltado")
        data = {"category": self.category.pk, "name": "Esmaltado", "price": "5.000", "duration": "30", "status": "on"}
        response = browser.post(
            reverse("service_detail_modal", kwargs={"pk": service.pk}), data, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("No puedes activar un servicio con una categoria inactiva.", response.content.decode())
