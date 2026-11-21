from datetime import timedelta

from django.test import Client as Browser
from django.urls import reverse
from django.utils import timezone

from apis.v1.sync.serializers import CategorySerializer
from apps.profiles.models import Perfil
from apps.services.models import Categoria, Servicio
from apps.tenancy.models import Negocio
from tests.apis.base import ApiTestCase

Rol = Perfil.Rol


class CategoriesApiTests(ApiTestCase):
    esquema = "api_categories"
    dominio = "api-categories.localhost"

    def create(self, **data):
        return self.api_client.post(reverse("api_categories"), {"nombre": "Manos", **data}, format="json")

    def edit(self, category, **data):
        return self.api_client.patch(reverse("api_category", kwargs={"pk": category.pk}), data, format="json")

    def version(self, category):
        category.refresh_from_db()
        return CategorySerializer(category).data["modified"]

    def test_administration_creates_a_category_with_the_web_rules(self):
        for rol in (Rol.PROPIETARIO, Rol.ENCARGADO):
            with self.subTest(rol=rol):
                self.log_in_as(rol)
                response = self.create(nombre=f"Manos {rol}", descripcion="Uñas")
                self.assertEqual(response.status_code, 201, response.content)
                data = response.json()
                self.assertEqual(data["message"], f"Categoria Manos {rol} creada exitosamente.")
                category = Categoria.objects.get(pk=data["category"]["id"])
                self.assertEqual(category.estado, Categoria.EstadoChoices.ACTIVO)
                self.assertEqual(category.descripcion, "Uñas")
                self.assertEqual(data["category"], CategorySerializer(category).data)

    def test_collaborator_cannot_create_or_edit(self):
        category = Categoria.objects.create(nombre="Manos")
        self.log_in_as(Rol.COLABORADOR)
        self.assertApiError(self.create(), 403, "forbidden")
        self.assertApiError(self.edit(category, nombre="Pies"), 403, "forbidden")

    def test_overdue_business_pauses_the_routes(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=Negocio.Estado.MOROSO)
        self.log_in_as(Rol.PROPIETARIO)
        self.assertApiError(self.create(), 402, "payment_pending")
        self.assertFalse(Categoria.objects.exists())

    def test_create_returns_the_form_errors_with_api_names(self):
        self.log_in_as(Rol.PROPIETARIO)
        response = self.create(nombre="")
        self.assertApiError(response, 400, "invalid_data")
        self.assertIn("nombre", response.json()["fields"])

    def test_inactivating_a_category_inactivates_its_services(self):
        self.log_in_as(Rol.ENCARGADO)
        category = Categoria.objects.create(nombre="Manos", descripcion="Uñas")
        service = Servicio.objects.create(nombre="Esmaltado", precio=5000, categoria=category)
        response = self.edit(category, estado="inactivo", version=self.version(category))
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()["category"]["estado"], "inactivo")
        self.assertEqual(response.json()["message"], "Categoria Manos actualizada exitosamente.")
        category.refresh_from_db()
        service.refresh_from_db()
        self.assertEqual(category.nombre, "Manos")
        self.assertEqual(category.descripcion, "Uñas")
        self.assertEqual(service.estado, Servicio.EstadoChoices.INACTIVO)

    def test_edit_with_an_old_version_is_a_conflict(self):
        self.log_in_as(Rol.PROPIETARIO)
        category = Categoria.objects.create(nombre="Manos")
        old = self.version(category)
        Categoria.objects.filter(pk=category.pk).update(modified=timezone.now() + timedelta(seconds=5))
        self.assertApiError(self.edit(category, nombre="Pies", version=old), 409, "conflict")
        category.refresh_from_db()
        self.assertEqual(category.nombre, "Manos")

    def test_edit_of_a_missing_category_is_not_found(self):
        self.log_in_as(Rol.PROPIETARIO)
        category = Categoria.objects.create(nombre="Manos")
        category.delete()
        self.assertApiError(self.edit(category, nombre="Pies"), 404, "not_found")

    def test_web_still_creates_and_edits_with_the_shared_form(self):
        user = self.make_user(Rol.PROPIETARIO)
        browser = Browser(HTTP_HOST=self.dominio)
        browser.force_login(user)
        data = {"name": "Web", "status": "on"}
        response = browser.post(reverse("category_create_modal"), data, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(response.status_code, 200, response.content)
        category = Categoria.objects.get(nombre="Web")
        Servicio.objects.create(nombre="Esmaltado", precio=5000, categoria=category)
        response = browser.post(
            reverse("category_detail_modal", kwargs={"pk": category.pk}),
            {"name": "Web"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Servicio.objects.get().estado, Servicio.EstadoChoices.INACTIVO)
