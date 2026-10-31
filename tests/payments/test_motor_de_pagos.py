from datetime import date, datetime, time
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.test import RequestFactory, SimpleTestCase
from django.utils import timezone

from apps.appointments.models import Cita
from apps.clients.models import Cliente
from apps.common.utils.dates import format_short_date_time
from apps.payments.accounting import PaymentAccount, PaymentExpressions, PaymentLabels
from apps.payments.choices import EstadoPago, MetodoPago, TipoDetallePago, TipoMovimiento
from apps.payments.models import DetallePago, Pago
from apps.payments.views.debtors.debt_detail import PaymentDetailListView
from apps.payments.views.debtors.list import DebtorsListView
from apps.payments.views.payments.list import PaymentsListView
from tests.base import NegocioTestCase


class EtiquetasYFechasTests(SimpleTestCase):
    def test_los_nombres_salen_de_un_solo_lugar(self):
        self.assertEqual(PaymentLabels.kind(None), "Abono")
        self.assertEqual(PaymentLabels.kind(TipoDetallePago.ANTICIPO), "Anticipo")
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
