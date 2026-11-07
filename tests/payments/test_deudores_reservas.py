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
from apps.payments.choices import EstadoDetallePago, EstadoPago, MetodoPago, TipoDetallePago
from apps.payments.models import DetallePago, Pago
from apps.profiles.models import Perfil
from tests.base import NegocioTestCase

User = get_user_model()
Tipo = TipoDetallePago


class DeudoresConReservaTests(NegocioTestCase):
    esquema = "deudores_reserva"
    dominio = "deudores-reserva.localhost"

    def setUp(self):
        super().setUp()
        encargada = User.objects.create_user(username="ana", email="ana@correo.cl", password="x")
        Perfil.objects.filter(user=encargada).update(rol=Perfil.Rol.ENCARGADO, debe_cambiar_clave=False)
        self.navegador = Client(HTTP_HOST=self.dominio)
        self.navegador.force_login(encargada)

    def deuda(self, tipo_reserva):
        pago = Pago.objects.create(
            cita=Cita.objects.create(
                cliente=Cliente.objects.create(nombre="Paula", apellido="Herrera"),
                fecha_agenda=date(2026, 11, 6),
                hora_agenda=time(10, 0),
                estado=Cita.EstadoChoices.COMPLETADA,
            ),
            monto_total_cita=Decimal("20000"),
            estado_pago=EstadoPago.PENDIENTE,
            cliente_nombre="Paula Herrera",
            fecha_cita=timezone.now(),
        )
        for monto, tipo in (("5000", tipo_reserva), ("5000", Tipo.ABONO)):
            DetallePago.objects.create(
                pago=pago,
                fecha_pago=timezone.now(),
                monto_pago=Decimal(monto),
                metodo_pago=MetodoPago.EFECTIVO,
                tipo_detalle=tipo,
                estado_detalle=EstadoDetallePago.VIGENTE,
            )
        return pago

    def ajax(self, nombre, datos=None, **kwargs):
        respuesta = self.navegador.get(
            reverse(nombre, kwargs=kwargs or None), datos or {}, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(respuesta.status_code, 200)
        return respuesta

    def cifras(self, pago):
        lista = self.ajax("debtors_list", {"draw": 1, "start": 0, "length": 10}).json()
        fila = lista["data"][0]
        detalle = self.ajax("debt_detail_modal", pk=pago.pk).context
        abono = self.ajax("add_payment_modal", pk=pago.pk).context
        hoja = load_workbook(BytesIO(self.navegador.get(reverse("debtors_export")).content)).active
        return {
            "lista": (fila["total_cita_formatted"], fila["total_abonado_formatted"], fila["saldo_pendiente_formatted"]),
            "tarjetas": (lista["total_abonado"], lista["total_pendiente"]),
            "detalle": (detalle["total_cita"], detalle["total_pagado"], detalle["total_pendiente"]),
            "abono": (abono["total"], abono["pagado"], abono["saldo"]),
            "excel": tuple(list(next(hoja.iter_rows(min_row=2, values_only=True)))[2:]),
        }

    def pagos_del_detalle(self, pago):
        datos = self.ajax("payment_detail_list", {"draw": 1}, pk=pago.pk).json()
        return sorted((fila["tipo_detalle_display"], fila["monto_pago_formatted"]) for fila in datos["data"])

    def test_la_que_no_descuenta_no_cuenta_como_abonado(self):
        pago = self.deuda(Tipo.RESERVA)
        cuenta = ("$20.000", "$5.000", "$15.000")
        self.assertEqual(
            self.cifras(pago),
            {
                "lista": cuenta,
                "tarjetas": ("$5.000", "$15.000"),
                "detalle": cuenta,
                "abono": cuenta,
                "excel": cuenta,
            },
        )
        self.assertEqual(self.pagos_del_detalle(pago), [("Abono", "$5.000")])

    def test_la_que_descuenta_cuenta_como_abonado(self):
        pago = self.deuda(Tipo.RESERVA_DESCONTABLE)
        cuenta = ("$20.000", "$10.000", "$10.000")
        self.assertEqual(
            self.cifras(pago),
            {
                "lista": cuenta,
                "tarjetas": ("$10.000", "$10.000"),
                "detalle": cuenta,
                "abono": cuenta,
                "excel": cuenta,
            },
        )
        self.assertEqual(self.pagos_del_detalle(pago), [("Abono", "$5.000"), ("Reserva", "$5.000")])
