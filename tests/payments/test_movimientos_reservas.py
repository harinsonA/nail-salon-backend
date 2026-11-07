from datetime import date, time
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from apps.appointments.models import Cita
from apps.clients.models import Cliente
from apps.payments.choices import (
    EstadoDetallePago,
    MetodoPago,
    TipoDetallePago,
    TipoMovimiento,
)
from apps.payments.models import DetallePago, Pago
from apps.profiles.models import Perfil
from tests.base import NegocioTestCase

User = get_user_model()
Tipo = TipoDetallePago
Estado = EstadoDetallePago


class MovimientosConReservaTests(NegocioTestCase):
    esquema = "movimientos_reserva"
    dominio = "movimientos-reserva.localhost"

    def setUp(self):
        super().setUp()
        encargada = User.objects.create_user(
            username="ana", email="ana@correo.cl", password="x"
        )
        Perfil.objects.filter(user=encargada).update(
            rol=Perfil.Rol.ENCARGADO, debe_cambiar_clave=False
        )
        self.navegador = Client(HTTP_HOST=self.dominio)
        self.navegador.force_login(encargada)
        cita = Cita.objects.create(
            cliente=Cliente.objects.create(nombre="Paula", apellido="Herrera"),
            fecha_agenda=date(2026, 11, 6),
            hora_agenda=time(10, 0),
        )
        self.pago = Pago.objects.create(
            cita=cita,
            monto_total_cita=Decimal("20000"),
            cliente_nombre="Paula Herrera",
            fecha_cita=timezone.now(),
        )
        self.fila("5000", Tipo.RESERVA, Estado.VIGENTE, MetodoPago.TRANSFERENCIA)
        self.fila(
            "4000", Tipo.RESERVA_DESCONTABLE, Estado.RETENIDO, MetodoPago.EFECTIVO
        )
        devuelta = self.fila("3000", Tipo.RESERVA, Estado.DEVUELTO, MetodoPago.TARJETA)
        self.fila(
            "3000",
            Tipo.DEVOLUCION,
            Estado.VIGENTE,
            MetodoPago.TRANSFERENCIA,
            devuelve=devuelta,
        )

    def fila(self, monto, tipo, estado, metodo, devuelve=None):
        return DetallePago.objects.create(
            pago=self.pago,
            fecha_pago=timezone.now(),
            monto_pago=Decimal(monto),
            metodo_pago=metodo,
            tipo_detalle=tipo,
            estado_detalle=estado,
            detalle_devuelto=devuelve,
        )

    def listar(self, **filtros):
        respuesta = self.navegador.get(
            reverse("incomes_list"),
            {"draw": 1, "start": 0, "length": 25, **filtros},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.json()

    def test_la_reserva_es_ingreso_y_su_reembolso_egreso(self):
        filas = {
            fila["monto_movimiento_formatted"]: fila["tipo_movimiento_display"]
            for fila in self.listar()["data"]
        }
        self.assertEqual(
            filas,
            {
                "$5.000": "Ingreso",
                "$4.000": "Ingreso",
                "$3.000": "Ingreso",
                "-$3.000": "Egreso",
            },
        )

    def test_los_totales_cuentan_la_reserva(self):
        datos = self.listar()
        self.assertEqual(
            (datos["total_ingresos"], datos["total_egresos"], datos["total_neto"]),
            ("$12.000", "$3.000", "$9.000"),
        )

    def test_el_filtro_de_egresos_solo_trae_el_reembolso(self):
        datos = self.listar(movement=TipoMovimiento.EGRESO)
        self.assertEqual(
            [fila["monto_movimiento_formatted"] for fila in datos["data"]], ["-$3.000"]
        )

    def test_el_grafico_suma_la_reserva_en_su_metodo(self):
        respuesta = self.navegador.get(
            reverse("incomes_by_method_ajax"), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        dataset = respuesta.json()["datasets"][0]
        datos = dict(zip(dataset["keys"], dataset["data"]))
        self.assertEqual(
            (datos["efectivo"], datos["tarjeta"], datos["transferencia"]),
            (4000, 3000, 5000),
        )

    def test_el_excel_trae_la_reserva_como_ingreso(self):
        respuesta = self.navegador.get(reverse("incomes_export"), {"movement": ""})
        hoja = load_workbook(BytesIO(respuesta.content)).active
        filas = {
            fila[-1]: fila[-2]
            for fila in hoja.iter_rows(min_row=2, values_only=True)
            if fila[-1]
        }
        self.assertEqual(filas["$5.000"], "Ingreso")
        self.assertEqual(filas["-$3.000"], "Egreso")
