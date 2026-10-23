from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.profiles.models import Perfil
from apps.services.imports.validators import ServiceAsyncImportValidator
from apps.services.models import Categoria, Servicio
from tests.base import NegocioTestCase

User = get_user_model()


class PrecioServicioTests(NegocioTestCase):
    esquema = "precio_servicio"
    dominio = "precio-servicio.localhost"

    def setUp(self):
        super().setUp()
        encargada = User.objects.create_user(username="ana", email="ana@correo.cl", password="x")
        Perfil.objects.filter(user=encargada).update(rol=Perfil.Rol.ENCARGADO, debe_cambiar_clave=False)
        self.navegador = Client(HTTP_HOST=self.dominio)
        self.navegador.force_login(encargada)
        self.categoria = Categoria.objects.create(nombre="Manos")

    def crear(self, precio):
        return self.navegador.post(
            reverse("service_create_modal"),
            {
                "category": self.categoria.pk,
                "name": "Retiro",
                "price": precio,
                "duration": "30",
                "status": "on",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def test_crea_servicio_con_precio_cero(self):
        respuesta = self.crear("0")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Servicio.objects.get().precio, Decimal("0"))

    def test_precio_vacio_se_guarda_como_cero(self):
        respuesta = self.crear("")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Servicio.objects.get().precio, Decimal("0"))

    def test_rechaza_precio_negativo(self):
        respuesta = self.crear("-100")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("El precio no puede ser negativo.", respuesta.content.decode())
        self.assertFalse(Servicio.objects.exists())

    def test_editar_precio_a_cero(self):
        servicio = Servicio.objects.create(nombre="Retiro", precio=Decimal("5000"), categoria=self.categoria)
        respuesta = self.navegador.post(
            reverse("service_detail_modal", kwargs={"pk": servicio.pk}),
            {
                "category": self.categoria.pk,
                "name": "Retiro",
                "price": "",
                "duration": "30",
                "status": "on",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(respuesta.status_code, 200)
        servicio.refresh_from_db()
        self.assertEqual(servicio.precio, Decimal("0"))

    def test_importacion_acepta_cero_y_vacio_y_rechaza_negativo(self):
        validador = ServiceAsyncImportValidator.__new__(ServiceAsyncImportValidator)
        self.assertEqual(validador.clean_precio("").ok_value, Decimal("0"))
        self.assertEqual(validador.clean_precio("0").ok_value, Decimal("0"))
        self.assertEqual(validador.clean_precio("-1").err_value, "El precio no puede ser negativo.")
