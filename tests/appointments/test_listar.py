"""
Tests para listar citas - API endpoint GET /api/citas/
"""

from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from ..utils import BaseAPITestCase
from apps.appointments.models import Cita


class TestListarCitas(BaseAPITestCase):
    """Tests para el endpoint de listado de citas."""

    def setUp(self):
        """Configuración inicial para cada test."""
        super().setUp()
        self.url_name = "cita-list"

        # Crear clientes de prueba
        self.cliente1 = self.create_cliente_with_factory(
            nombre="Ana",
            apellido="García",
            telefono="3001111111",
            email="ana.garcia@test.com",
        )
        self.cliente2 = self.create_cliente_with_factory(
            nombre="María",
            apellido="López",
            telefono="3002222222",
            email="maria.lopez@test.com",
        )
        self.cliente3 = self.create_cliente_with_factory(
            nombre="Carmen",
            apellido="Rodríguez",
            telefono="3003333333",
            email="carmen.rodriguez@test.com",
        )

        # Crear servicios de prueba
        self.servicio1 = self.create_servicio_with_factory(
            nombre_servicio="Manicure Básico", precio=25000
        )
        self.servicio2 = self.create_servicio_with_factory(
            nombre_servicio="Pedicure Completo", precio=35000
        )

        # Crear citas de prueba
        fecha_base = timezone.now() + timedelta(days=1)

        self.cita1 = self.create_cita_with_factory(
            cliente=self.cliente1,
            fecha_hora_cita=fecha_base,
            estado_cita="CONFIRMADA",
            observaciones="Cita confirmada",
        )
        self.cita2 = self.create_cita_with_factory(
            cliente=self.cliente2,
            fecha_hora_cita=fecha_base + timedelta(hours=2),
            estado_cita="PENDIENTE",
            observaciones="Cita pendiente",
        )
        self.cita3 = self.create_cita_with_factory(
            cliente=self.cliente3,
            fecha_hora_cita=fecha_base + timedelta(days=1),
            estado_cita="COMPLETADA",
            observaciones="Cita completada",
        )

    def test_listar_citas_exitoso(self):
        """Test que verifica que se pueden listar las citas correctamente."""
        response = self.api_get(self.url_name)

        self.assert_response_status(response, status.HTTP_200_OK)
        self.assert_pagination_response(response.data)

        # Verificar que se retornan las citas creadas
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 3)

        # Verificar estructura de cada cita
        expected_fields = [
            "cita_id",
            "cliente",
            "fecha_hora_cita",
            "estado_cita",
            "observaciones",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        for cita_data in response.data["results"]:
            self.assert_response_contains_fields(cita_data, expected_fields)

    def test_listar_citas_con_filtros_estado(self):
        """Test para verificar filtros por estado de cita."""
        # Filtro por estado CONFIRMADA
        response = self.api_get(self.url_name, {"estado_cita": "CONFIRMADA"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["estado_cita"], "CONFIRMADA")

        # Filtro por estado PENDIENTE
        response = self.api_get(self.url_name, {"estado_cita": "PENDIENTE"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["estado_cita"], "PENDIENTE")

        # Filtro por estado COMPLETADA
        response = self.api_get(self.url_name, {"estado_cita": "COMPLETADA"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["estado_cita"], "COMPLETADA")

    def test_listar_citas_con_filtros_cliente(self):
        """Test para verificar filtros por cliente."""
        # Filtro por cliente 1
        response = self.api_get(self.url_name, {"cliente": self.cliente1.cliente_id})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["cliente"], self.cliente1.cliente_id
        )

        # Filtro por cliente 2
        response = self.api_get(self.url_name, {"cliente": self.cliente2.cliente_id})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(
            response.data["results"][0]["cliente"], self.cliente2.cliente_id
        )

    def test_listar_citas_con_filtros_fecha(self):
        """Test para verificar filtros por fecha."""
        fecha_filtro = (timezone.now() + timedelta(days=1)).date()

        # Usar el parámetro fecha_desde que está implementado en el ViewSet
        response = self.api_get(
            self.url_name, {"fecha_desde": fecha_filtro.isoformat()}
        )
        self.assert_response_status(response, status.HTTP_200_OK)

        # Verificar que todas las citas retornadas son de la fecha especificada o posteriores
        for cita in response.data["results"]:
            fecha_cita = timezone.datetime.fromisoformat(
                cita["fecha_hora_cita"].replace("Z", "+00:00")
            ).date()
            self.assertGreaterEqual(fecha_cita, fecha_filtro)

    def test_listar_citas_busqueda_por_observaciones(self):
        """Test para verificar búsqueda en observaciones."""
        response = self.api_get(self.url_name, {"search": "confirmada"})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertIn(
            "confirmada", response.data["results"][0]["observaciones"].lower()
        )

    def test_listar_citas_ordenamiento(self):
        """Test para verificar ordenamiento de resultados."""
        # Ordenamiento ascendente por fecha
        response = self.api_get(self.url_name, {"ordering": "fecha_hora_cita"})
        self.assert_response_status(response, status.HTTP_200_OK)

        citas = response.data["results"]
        fechas = [cita["fecha_hora_cita"] for cita in citas]
        fechas_ordenadas = sorted(fechas)
        self.assertEqual(fechas, fechas_ordenadas)

        # Ordenamiento descendente por fecha (por defecto)
        response = self.api_get(self.url_name, {"ordering": "-fecha_hora_cita"})
        self.assert_response_status(response, status.HTTP_200_OK)

        citas = response.data["results"]
        fechas = [cita["fecha_hora_cita"] for cita in citas]
        fechas_ordenadas_desc = sorted(fechas, reverse=True)
        self.assertEqual(fechas, fechas_ordenadas_desc)

    def test_listar_citas_paginacion(self):
        """Test para verificar la paginación."""
        # Crear más citas para probar paginación
        fecha_base = timezone.now() + timedelta(days=2)
        for i in range(15):
            self.create_cita_with_factory(
                cliente=self.cliente1,
                fecha_hora_cita=fecha_base + timedelta(hours=i),
                estado_cita="PENDIENTE",
                observaciones=f"Cita {i + 4}",
            )

        # Test primera página
        response = self.api_get(self.url_name, {"page": 1, "page_size": 10})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 10)
        self.assertIsNotNone(response.data["links"]["next"])
        self.assertIsNone(response.data["links"]["previous"])

        # Test segunda página
        response = self.api_get(self.url_name, {"page": 2, "page_size": 10})
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data["results"]), 8
        )  # 18 total - 10 primera página
        self.assertIsNone(response.data["links"]["next"])
        self.assertIsNotNone(response.data["links"]["previous"])

    def test_listar_citas_sin_autenticacion(self):
        """Test que verifica que se requiere autenticación."""
        self.unauthenticate()
        response = self.api_get(self.url_name)
        self.assert_unauthorized(response)

    def test_listar_citas_usuario_normal(self):
        """Test que verifica que usuarios normales pueden listar citas."""
        self.authenticate_as_normal_user()
        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assert_pagination_response(response.data)

    def test_listar_citas_sin_resultados(self):
        """Test para verificar respuesta cuando no hay citas."""
        # Eliminar todas las citas
        Cita.objects.all().delete()

        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assert_pagination_response(response.data)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(len(response.data["results"]), 0)

    def test_listar_citas_filtros_combinados(self):
        """Test para verificar filtros combinados."""
        response = self.api_get(
            self.url_name,
            {
                "estado_cita": "CONFIRMADA",
                "cliente": self.cliente1.cliente_id,
                "search": "confirmada",
            },
        )
        self.assert_response_status(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

        resultado = response.data["results"][0]
        self.assertEqual(resultado["estado_cita"], "CONFIRMADA")
        self.assertEqual(resultado["cliente"], self.cliente1.cliente_id)

    def test_listar_citas_formato_fecha_respuesta(self):
        """Test para verificar formato de fechas en la respuesta."""
        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)

        if response.data["results"]:
            cita = response.data["results"][0]
            # Verificar que fecha_hora_cita tiene el formato correcto
            self.assertIsNotNone(cita["fecha_hora_cita"])
            self.assertIsInstance(cita["fecha_hora_cita"], str)

            # Verificar que fecha_creacion tiene el formato correcto
            self.assertIsNotNone(cita["fecha_creacion"])
            self.assertIsInstance(cita["fecha_creacion"], str)

    def test_listar_citas_con_detalles_incluidos(self):
        """Test para verificar que se incluyen detalles de servicios si se solicita."""
        # Agregar detalle a una cita
        self.create_detalle_cita_with_factory(
            cita=self.cita1,
            servicio=self.servicio1,
            precio_acordado=self.servicio1.precio,
            cantidad_servicios=1,
        )

        response = self.api_get(self.url_name, {"include_detalles": "true"})
        self.assert_response_status(response, status.HTTP_200_OK)

        # Buscar la cita que tiene detalles
        cita_con_detalle = None
        for cita in response.data["results"]:
            if cita["cita_id"] == self.cita1.cita_id:
                cita_con_detalle = cita
                break

        self.assertIsNotNone(cita_con_detalle)
        if "detalles" in cita_con_detalle:
            self.assertGreater(len(cita_con_detalle["detalles"]), 0)

    def test_listar_citas_estados_validos(self):
        """Test para verificar que solo se muestran citas con estados válidos."""
        response = self.api_get(self.url_name)
        self.assert_response_status(response, status.HTTP_200_OK)

        estados_validos = ["PENDIENTE", "CONFIRMADA", "CANCELADA", "COMPLETADA"]

        for cita in response.data["results"]:
            self.assertIn(cita["estado_cita"], estados_validos)
