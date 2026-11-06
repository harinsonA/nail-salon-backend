from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import RequestFactory, SimpleTestCase
from django.utils import timezone

from apps.appointments.models import Cita
from apps.clients.models import Cliente
from apps.common.utils.dates import format_short_date_time
from apps.payments.accounting import PaymentAccount, PaymentExpressions, PaymentLabels
from apps.payments.choices import (
    EstadoDetallePago,
    EstadoPago,
    MetodoPago,
    TipoDetallePago,
    TipoMovimiento,
)
from apps.payments.models import DetallePago, Pago
from apps.payments.views.debtors.debt_detail import PaymentDetailListView
from apps.payments.views.debtors.list import DebtorsListView
from apps.payments.views.payments.list import PaymentsListView
from tests.base import NegocioTestCase


class EtiquetasYFechasTests(SimpleTestCase):
    def test_los_nombres_salen_de_un_solo_lugar(self):
        self.assertEqual(PaymentLabels.kind(None), "Abono")
        self.assertEqual(PaymentLabels.kind(TipoDetallePago.ANTICIPO), "Anticipo")
        self.assertEqual(PaymentLabels.kind(TipoDetallePago.RESERVA_DESCONTABLE), "Reserva")
        self.assertEqual(PaymentLabels.method(MetodoPago.TRANSFERENCIA), "Transferencia")
        self.assertEqual(PaymentLabels.movement(TipoMovimiento.EGRESO), "Egreso")
        self.assertEqual(
            PaymentLabels.refund_choices(),
            [(MetodoPago.EFECTIVO, "Efectivo"), (MetodoPago.TRANSFERENCIA, "Transferencia")],
        )

    def test_las_tablas_muestran_la_hora_de_chile(self):
        utc = datetime(2026, 10, 30, 18, 0, tzinfo=ZoneInfo("UTC"))
        self.assertEqual(format_short_date_time(utc), timezone.localtime(utc).strftime("%d/%m/%Y %H:%M"))
        self.assertNotEqual(format_short_date_time(utc), "30/10/2026 18:00")
        self.assertEqual(format_short_date_time(None), "-- --")


class CuentaDeDeudoresTests(NegocioTestCase):
    esquema = "motor_de_pagos"

    def setUp(self):
        super().setUp()
        cita = Cita.objects.create(
            cliente=Cliente.objects.create(nombre="Paula", apellido="Herrera"),
            fecha_agenda=date(2026, 10, 20),
            hora_agenda=time(10, 0),
            estado=Cita.EstadoChoices.COMPLETADA,
        )
        self.pago = Pago.objects.create(
            cita=cita,
            monto_total_cita=Decimal("10000"),
            estado_pago=EstadoPago.PENDIENTE,
            cliente_nombre="Paula Herrera",
            fecha_cita=timezone.now(),
        )

    def vista(self, cls, **kwargs):
        view = cls()
        view.request = RequestFactory().get("/")
        view.kwargs = kwargs
        return view

    def abonar(self, monto):
        DetallePago.objects.create(
            pago=self.pago, fecha_pago=timezone.now(), monto_pago=Decimal(monto), metodo_pago=MetodoPago.EFECTIVO
        )

    def test_el_saldo_de_deudores_nunca_es_negativo(self):
        self.abonar("12000")
        fila = self.vista(DebtorsListView).get_queryset().values("saldo_pendiente").get()
        self.assertEqual(fila["saldo_pendiente"], Decimal("0"))

    def test_pagado_cuando_lo_abonado_cubre_el_total(self):
        self.abonar("4000")
        self.assertFalse(PaymentAccount(self.pago).is_settled())
        self.abonar("6000")
        self.assertTrue(PaymentAccount(self.pago).is_settled())

    def test_las_tres_listas_muestran_la_hora_de_chile(self):
        utc = datetime(2026, 10, 30, 18, 0, tzinfo=ZoneInfo("UTC"))
        local = timezone.localtime(utc).strftime("%d/%m/%Y %H:%M")
        Pago.objects.filter(pk=self.pago.pk).update(fecha_cita=utc, fecha_pago_completado=utc)
        self.abonar("4000")
        DetallePago.objects.update(fecha_pago=utc)
        deudores = self.vista(DebtorsListView)
        self.assertEqual(deudores.get_values(deudores.get_queryset())[0]["fecha_cita_display"], local)
        detalle = self.vista(PaymentDetailListView, pk=self.pago.pk)
        self.assertEqual(detalle.get_values(detalle.get_queryset())[0]["fecha_pago_display"], local)
        completados = self.vista(PaymentsListView).get_values(
            PaymentExpressions.with_appointment_summary(Pago.objects.filter(pk=self.pago.pk))
        )[0]
        self.assertEqual(
            (completados["fecha_cita_display"], completados["fecha_pago_completado_display"]), (local, local)
        )


Tipo = TipoDetallePago
Estado = EstadoDetallePago

SERVICIOS = Decimal("20000")
RESERVA = "5000"
VIGENTE = (Estado.VIGENTE, False, False)
RETENIDA = (Estado.RETENIDO, True, False)
REEMBOLSADA_AL_CANCELAR = (Estado.DEVUELTO, True, True)
RETENIDA_DEFINITIVA = (Estado.RETENIDO_DEFINITIVO, False, False)
REEMBOLSADA_Y_RESTAURADA = (Estado.DEVUELTO, False, True)

CASOS = {
    Tipo.RESERVA: [
        ("vigente", VIGENTE, [], (20000, 20000, 0, 20000, 5000)),
        ("vigente con anticipo", VIGENTE, [("3000", Tipo.ANTICIPO)], (20000, 20000, 3000, 17000, 8000)),
        ("cancelada y retenida", RETENIDA, [], (0, 0, 0, 0, 5000)),
        ("cancelada y reembolsada", REEMBOLSADA_AL_CANCELAR, [], (0, 0, 0, 0, 0)),
        ("restaurada, retenida definitiva", RETENIDA_DEFINITIVA, [], (20000, 20000, 0, 20000, 5000)),
        ("restaurada tras reembolso", REEMBOLSADA_Y_RESTAURADA, [], (20000, 20000, 0, 20000, 0)),
        ("vigente con abono", VIGENTE, [("20000", Tipo.ABONO)], (20000, 20000, 20000, 0, 25000)),
    ],
    Tipo.RESERVA_DESCONTABLE: [
        ("vigente", VIGENTE, [], (20000, 20000, 5000, 15000, 5000)),
        ("vigente con anticipo", VIGENTE, [("3000", Tipo.ANTICIPO)], (20000, 20000, 8000, 12000, 8000)),
        ("cancelada y retenida", RETENIDA, [], (5000, 0, 0, 0, 5000)),
        ("cancelada y reembolsada", REEMBOLSADA_AL_CANCELAR, [], (0, 0, 0, 0, 0)),
        ("restaurada, retenida definitiva", RETENIDA_DEFINITIVA, [], (25000, 20000, 0, 20000, 5000)),
        ("restaurada tras reembolso", REEMBOLSADA_Y_RESTAURADA, [], (20000, 20000, 0, 20000, 0)),
        ("vigente con abono", VIGENTE, [("15000", Tipo.ABONO)], (20000, 20000, 20000, 0, 20000)),
    ],
}


class ReservaEnElMotorTests(NegocioTestCase):
    esquema = "motor_reserva"

    def setUp(self):
        super().setUp()
        self.cliente = Cliente.objects.create(nombre="Paula", apellido="Herrera")

    def cita_con_pago(self, tipo, estado, cancelada, reembolsada, otras):
        cita = Cita.objects.create(
            cliente=self.cliente,
            fecha_agenda=date(2026, 10, 20),
            hora_agenda=time(10, 0),
            estado=Cita.EstadoChoices.CANCELADA if cancelada else Cita.EstadoChoices.PENDIENTE,
        )
        pago = Pago.objects.create(
            cita=cita,
            monto_total_cita=Decimal("0"),
            estado_pago=EstadoPago.PENDIENTE,
            cliente_nombre="Paula Herrera",
            fecha_cita=timezone.now(),
        )
        if tipo:
            reserva = self.fila(pago, RESERVA, tipo, estado)
            if reembolsada:
                self.fila(pago, RESERVA, Tipo.DEVOLUCION, Estado.VIGENTE, devuelve=reserva)
        for monto, otro_tipo in otras:
            self.fila(pago, monto, otro_tipo, Estado.VIGENTE if otro_tipo else None)
        pago.monto_total_cita = PaymentAccount(pago).total(SERVICIOS, cancelled=cancelada)
        pago.save()
        return pago

    def fila(self, pago, monto, tipo, estado, devuelve=None):
        return DetallePago.objects.create(
            pago=pago,
            fecha_pago=timezone.now(),
            monto_pago=Decimal(monto),
            metodo_pago=MetodoPago.EFECTIVO,
            tipo_detalle=tipo,
            estado_detalle=estado,
            detalle_devuelto=devuelve,
        )

    def cifras_python(self, pago):
        cuenta = PaymentAccount(pago)
        return (
            pago.monto_total_cita,
            cuenta.appointment_total(),
            cuenta.appointment_paid(),
            cuenta.balance(),
            cuenta.paid(),
        )

    def cifras_sql(self, pago):
        fila = PaymentExpressions.with_appointment_summary(Pago.objects.filter(pk=pago.pk)).get()
        return (
            fila.monto_total_cita,
            fila.total_cita,
            fila.total_abonado,
            fila.saldo_pendiente,
            fila.total_pagado,
        )

    def comprobar(self, tipo):
        for nombre, (estado, cancelada, reembolsada), otras, esperado in CASOS[tipo]:
            with self.subTest(caso=nombre):
                pago = self.cita_con_pago(tipo, estado, cancelada, reembolsada, otras)
                esperado = tuple(Decimal(valor) for valor in esperado)
                self.assertEqual(self.cifras_python(pago), esperado)
                self.assertEqual(self.cifras_sql(pago), esperado)
                self.assertEqual(PaymentAccount(pago).is_settled(), esperado[3] == 0)

    def test_la_reserva_que_suma_da_las_cifras_acordadas(self):
        self.comprobar(Tipo.RESERVA)

    def test_la_reserva_que_descuenta_da_las_cifras_acordadas(self):
        self.comprobar(Tipo.RESERVA_DESCONTABLE)

    def test_sin_reserva_y_con_filas_antiguas_da_lo_mismo_que_antes(self):
        casos = [
            ("solo filas antiguas", None, [("8000", None)], (20000, 20000, 8000, 12000, 8000)),
            ("anticipo y fila antigua", None, [("3000", Tipo.ANTICIPO), ("8000", None)], (20000, 20000, 11000, 9000, 11000)),
            ("reserva que suma y fila antigua", Tipo.RESERVA, [("8000", None)], (20000, 20000, 8000, 12000, 13000)),
            ("reserva que descuenta y fila antigua", Tipo.RESERVA_DESCONTABLE, [("8000", None)], (20000, 20000, 13000, 7000, 13000)),
        ]
        for nombre, tipo, otras, esperado in casos:
            with self.subTest(caso=nombre):
                pago = self.cita_con_pago(tipo, Estado.VIGENTE, False, False, otras)
                esperado = tuple(Decimal(valor) for valor in esperado)
                self.assertEqual(self.cifras_python(pago), esperado)
                self.assertEqual(self.cifras_sql(pago), esperado)

    def test_la_lista_de_pagos_deja_fuera_solo_la_reserva_que_suma(self):
        for tipo, esperados in (
            (Tipo.RESERVA, [Decimal("3000"), Decimal("8000")]),
            (Tipo.RESERVA_DESCONTABLE, [Decimal("3000"), Decimal("5000"), Decimal("8000")]),
        ):
            with self.subTest(tipo=tipo):
                pago = self.cita_con_pago(tipo, Estado.VIGENTE, False, False, [("3000", Tipo.ANTICIPO), ("8000", None)])
                python = sorted(fila.monto_pago for fila in PaymentAccount(pago).appointment_payments())
                sql = sorted(
                    DetallePago.objects.filter(pago=pago)
                    .filter(PaymentExpressions.appointment_payment_filter())
                    .values_list("monto_pago", flat=True)
                )
                self.assertEqual(python, esperados)
                self.assertEqual(sql, esperados)

    def test_la_reserva_que_suma_se_separa_de_lo_que_se_abona_al_servicio(self):
        pago = self.cita_con_pago(Tipo.RESERVA, Estado.VIGENTE, False, False, [("3000", Tipo.ANTICIPO)])
        cuenta = PaymentAccount(pago)
        self.assertEqual(
            (cuenta.paid(), cuenta.reservation(), cuenta.applied(), cuenta.charges(), cuenta.credit()),
            (Decimal("8000"), Decimal("5000"), Decimal("3000"), Decimal("0"), Decimal("3000")),
        )

    def test_retenida_la_reserva_que_suma_sigue_en_el_retenido_del_panel(self):
        pago = self.cita_con_pago(Tipo.RESERVA, Estado.RETENIDO, True, False, [])
        cuenta = PaymentAccount(pago)
        self.assertEqual((cuenta.retained(), cuenta.service_retained()), (Decimal("5000"), Decimal("0")))
