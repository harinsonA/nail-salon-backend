from datetime import date, datetime, time
from decimal import Decimal

from django.utils import timezone

from apps.appointments.models import Cita
from apps.clients.models import Cliente
from apps.payments.choices import EstadoDetallePago, EstadoPago, MetodoPago, TipoDetallePago
from apps.payments.models import DetallePago, Pago
from dashboard.services import metrics
from dashboard.services.periods import between
from tests.base import NegocioTestCase

Tipo = TipoDetallePago
Estado = EstadoDetallePago


class DashboardConReservaTests(NegocioTestCase):
    esquema = "dashboard_reserva"

    def setUp(self):
        super().setUp()
        self.cliente = Cliente.objects.create(nombre="Paula", apellido="Herrera")
        self.periodo = between(date(2026, 10, 1), date(2026, 10, 31))

    def cita_saldada(self, tipo_reserva, abono, total="20000"):
        pago = Pago.objects.create(
            cita=Cita.objects.create(
                cliente=self.cliente,
                fecha_agenda=date(2026, 10, 20),
                hora_agenda=time(10, 0),
                estado=Cita.EstadoChoices.COMPLETADA,
            ),
            monto_total_cita=Decimal(total),
            estado_pago=EstadoPago.COMPLETADO,
            cliente_nombre="Paula Herrera",
            fecha_cita=timezone.make_aware(datetime(2026, 10, 20, 10, 0)),
        )
        for monto, tipo, metodo in (
            ("5000", tipo_reserva, MetodoPago.TRANSFERENCIA),
            (abono, Tipo.ABONO, MetodoPago.EFECTIVO),
        ):
            DetallePago.objects.create(
                pago=pago,
                fecha_pago=timezone.make_aware(datetime(2026, 10, 20, 12, 0)),
                monto_pago=Decimal(monto),
                metodo_pago=metodo,
                tipo_detalle=tipo,
                estado_detalle=Estado.VIGENTE,
            )
        return pago

    def cifras(self):
        series = {
            serie["key"]: sum(serie["data"])
            for serie in metrics.income_billed_vs_collected(self.periodo)["datasets"]
        }
        metodos = metrics.payment_methods(self.periodo)["datasets"][0]
        por_metodo = dict(zip(metodos["keys"], metodos["data"]))
        return series["facturado"], series["cobrado"], por_metodo["transferencia"], por_metodo["efectivo"]

    def test_la_que_no_descuenta_se_cobra_aparte(self):
        self.cita_saldada(Tipo.RESERVA, "20000")
        self.assertEqual(self.cifras(), (20000, 25000, 5000, 20000))

    def test_la_que_descuenta_es_parte_del_total(self):
        self.cita_saldada(Tipo.RESERVA_DESCONTABLE, "15000")
        self.assertEqual(self.cifras(), (20000, 20000, 5000, 15000))
