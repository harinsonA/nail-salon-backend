from datetime import date, datetime, time
from decimal import Decimal

from django.test import RequestFactory
from django.utils import timezone

from apps.appointments.models import Cita
from apps.clients.models import Cliente
from apps.payments.choices import (
    EstadoDetallePago,
    EstadoPago,
    MetodoPago,
    TipoDetallePago,
)
from apps.payments.models import DetallePago, Pago
from apps.payments.services.account import PaymentAccount, incoming, net_paid
from apps.payments.services.income_by_method import income_by_method
from apps.payments.views.debtors.list import DebtorsListView
from apps.payments.views.incomes.list import IncomesListView
from dashboard.services import metrics
from dashboard.services.periods import between
from tests.base import NegocioTestCase

Tipo = TipoDetallePago
Estado = EstadoDetallePago


class CuentaPagoTests(NegocioTestCase):
    esquema = "cuenta_pago"

    def setUp(self):
        super().setUp()
        self.cliente = Cliente.objects.create(nombre="Paula", apellido="Herrera")

    def pago(
        self,
        total="30000",
        estado_cita=Cita.EstadoChoices.COMPLETADA,
        estado_pago=EstadoPago.PENDIENTE,
        dia=20,
    ):
        cita = Cita.objects.create(
            cliente=self.cliente,
            fecha_agenda=date(2026, 10, dia),
            hora_agenda=time(10, 0),
            estado=estado_cita,
        )
        return Pago.objects.create(
            cita=cita,
            monto_total_cita=Decimal(total),
            estado_pago=estado_pago,
            cliente_nombre="Paula Herrera",
            fecha_cita=timezone.make_aware(datetime(2026, 10, dia, 10, 0)),
        )

    def fila(
        self,
        pago,
        monto,
        tipo=None,
        estado=None,
        devuelve=None,
        metodo=MetodoPago.EFECTIVO,
        dia=20,
    ):
        return DetallePago.objects.create(
            pago=pago,
            fecha_pago=timezone.make_aware(datetime(2026, 10, dia, 12, 0)),
            monto_pago=Decimal(monto),
            metodo_pago=metodo,
            tipo_detalle=tipo,
            estado_detalle=estado,
            detalle_devuelto=devuelve,
        )

    def cuenta(self, pago):
        return PaymentAccount(pago)

    def lista(self, cls):
        view = cls()
        view.request = RequestFactory().get("/")
        view.kwargs = {}
        return view

    def test_las_filas_vacias_cuentan_como_abonos_vigentes(self):
        pago = self.pago()
        self.fila(pago, "12000")
        self.fila(pago, "8000")
        cuenta = self.cuenta(pago)
        self.assertEqual(cuenta.paid(), Decimal("20000"))
        self.assertEqual(cuenta.charges(), Decimal("0"))
        self.assertEqual(cuenta.retained(), Decimal("0"))
        self.assertEqual(cuenta.balance(), Decimal("10000"))

    def test_anticipo_vigente_se_descuenta_al_completar(self):
        pago = self.pago()
        self.fila(pago, "10000", Tipo.ANTICIPO, Estado.VIGENTE)
        self.fila(pago, "20000", Tipo.ABONO, Estado.VIGENTE)
        cuenta = self.cuenta(pago)
        self.assertEqual(cuenta.total(30000), Decimal("30000"))
        self.assertEqual(cuenta.paid(), Decimal("30000"))
        self.assertEqual(cuenta.balance(), Decimal("0"))

    def test_la_reserva_no_se_descuenta_y_suma_al_total(self):
        pago = self.pago(total="35000")
        self.fila(pago, "5000", Tipo.RESERVA, Estado.VIGENTE)
        self.fila(pago, "30000", Tipo.ABONO, Estado.VIGENTE)
        cuenta = self.cuenta(pago)
        self.assertEqual(cuenta.total(30000), Decimal("35000"))
        self.assertEqual(cuenta.paid(), Decimal("35000"))
        self.assertEqual(cuenta.balance(), Decimal("0"))

    def test_cancelada_con_todo_devuelto_queda_en_cero(self):
        pago = self.pago(
            total="0",
            estado_cita=Cita.EstadoChoices.CANCELADA,
            estado_pago=EstadoPago.REEMBOLSADO,
        )
        anticipo = self.fila(pago, "10000", Tipo.ANTICIPO, Estado.DEVUELTO)
        self.fila(pago, "10000", Tipo.DEVOLUCION, devuelve=anticipo)
        cuenta = self.cuenta(pago)
        self.assertEqual(cuenta.total(30000, cancelled=True), Decimal("0"))
        self.assertEqual(cuenta.paid(), Decimal("0"))
        self.assertEqual(cuenta.refundable(anticipo), Decimal("0"))

    def test_devolucion_parcial_retiene_el_resto(self):
        pago = self.pago(
            total="4000",
            estado_cita=Cita.EstadoChoices.CANCELADA,
            estado_pago=EstadoPago.COMPLETADO,
        )
        anticipo = self.fila(pago, "10000", Tipo.ANTICIPO, Estado.RETENIDO)
        self.fila(pago, "6000", Tipo.DEVOLUCION, devuelve=anticipo)
        cuenta = self.cuenta(pago)
        self.assertEqual(cuenta.refunded(anticipo), Decimal("6000"))
        self.assertEqual(cuenta.refundable(anticipo), Decimal("4000"))
        self.assertEqual(cuenta.retained(), Decimal("4000"))
        self.assertEqual(cuenta.total(30000, cancelled=True), Decimal("4000"))
        self.assertEqual(cuenta.paid(), Decimal("4000"))
        self.assertEqual(cuenta.balance(), Decimal("0"))

    def test_cancelada_reteniendo_todo(self):
        pago = self.pago(
            total="10000",
            estado_cita=Cita.EstadoChoices.CANCELADA,
            estado_pago=EstadoPago.COMPLETADO,
        )
        self.fila(pago, "10000", Tipo.ANTICIPO, Estado.RETENIDO)
        cuenta = self.cuenta(pago)
        self.assertEqual(cuenta.total(30000, cancelled=True), Decimal("10000"))
        self.assertEqual(cuenta.paid(), Decimal("10000"))
        self.assertEqual(cuenta.retained(), Decimal("10000"))

    def test_restaurada_con_lo_retenido_que_no_vale_lo_suma_al_total(self):
        pago = self.pago(total="40000", estado_cita=Cita.EstadoChoices.PENDIENTE)
        self.fila(pago, "10000", Tipo.ANTICIPO, Estado.RETENIDO)
        cuenta = self.cuenta(pago)
        self.assertEqual(cuenta.total(30000), Decimal("40000"))
        self.assertEqual(cuenta.paid(), Decimal("10000"))
        self.assertEqual(cuenta.balance(), Decimal("30000"))

    def test_restaurada_con_lo_retenido_que_vuelve_a_valer_lo_descuenta(self):
        pago = self.pago(total="30000", estado_cita=Cita.EstadoChoices.PENDIENTE)
        self.fila(pago, "10000", Tipo.ANTICIPO, Estado.VIGENTE)
        cuenta = self.cuenta(pago)
        self.assertEqual(cuenta.total(30000), Decimal("30000"))
        self.assertEqual(cuenta.balance(), Decimal("20000"))

    def test_una_reserva_devuelta_en_dos_partes(self):
        pago = self.pago()
        reserva = self.fila(pago, "5000", Tipo.RESERVA, Estado.RETENIDO)
        self.fila(pago, "2000", Tipo.DEVOLUCION, devuelve=reserva)
        self.fila(pago, "1000", Tipo.DEVOLUCION, devuelve=reserva)
        cuenta = self.cuenta(pago)
        self.assertEqual(cuenta.refunded(reserva), Decimal("3000"))
        self.assertEqual(cuenta.refundable(reserva), Decimal("2000"))
        self.assertEqual(cuenta.charges(), Decimal("2000"))

    def test_un_abono_no_es_devolvible(self):
        pago = self.pago()
        abono = self.fila(pago, "5000", Tipo.ABONO, Estado.VIGENTE)
        self.assertEqual(self.cuenta(pago).refundable(abono), Decimal("0"))

    def test_las_expresiones_sql_restan_devoluciones_y_leen_las_filas_vacias(self):
        pago = self.pago()
        anticipo = self.fila(pago, "10000", Tipo.ANTICIPO, Estado.RETENIDO)
        self.fila(pago, "3000")
        self.fila(pago, "4000", Tipo.DEVOLUCION, devuelve=anticipo)
        filas = DetallePago.objects.filter(pago=pago)
        self.assertEqual(filas.aggregate(total=net_paid())["total"], Decimal("9000"))
        self.assertEqual(filas.filter(incoming()).count(), 2)
        self.assertEqual(
            Pago.objects.filter(pk=pago.pk)
            .annotate(neto=net_paid("detalles_pago__"))
            .get()
            .neto,
            Decimal("9000"),
        )
        self.assertEqual(
            DetallePago.objects.none().aggregate(total=net_paid())["total"],
            Decimal("0"),
        )

    def test_deudores_solo_muestra_citas_completadas_con_su_saldo_neto(self):
        deuda = self.pago(total="18000")
        anticipo = self.fila(deuda, "8000", Tipo.ANTICIPO, Estado.RETENIDO)
        self.fila(deuda, "3000", Tipo.DEVOLUCION, devuelve=anticipo)
        pendiente = self.pago(estado_cita=Cita.EstadoChoices.PENDIENTE, dia=21)
        self.fila(pendiente, "10000", Tipo.ANTICIPO, Estado.VIGENTE)
        view = self.lista(DebtorsListView)
        filas = list(
            view.get_queryset().values("pk", "total_abonado", "saldo_pendiente")
        )
        self.assertEqual(
            filas,
            [
                {
                    "pk": deuda.pk,
                    "total_abonado": Decimal("5000"),
                    "saldo_pendiente": Decimal("13000"),
                }
            ],
        )

    def test_los_totales_de_deudores_no_se_duplican_con_varios_abonos(self):
        primera = self.pago(total="18000")
        self.fila(primera, "2000")
        self.fila(primera, "3000")
        self.fila(primera, "1000")
        segunda = self.pago(total="10000", dia=21)
        self.fila(segunda, "4000")
        view = self.lista(DebtorsListView)
        totales = view.additional_data(view.get_queryset())
        self.assertEqual(
            totales, {"monto_total_cita": "$ 28,000", "total_abonado": "$ 10,000"}
        )

    def test_ingresos_restan_las_devoluciones_y_no_las_promedian(self):
        pago = self.pago()
        anticipo = self.fila(pago, "10000", Tipo.ANTICIPO, Estado.RETENIDO)
        self.fila(pago, "6000")
        self.fila(pago, "4000", Tipo.DEVOLUCION, devuelve=anticipo)
        view = self.lista(IncomesListView)
        totales = view.additional_data(DetallePago.objects.filter(pago=pago))
        self.assertEqual(
            totales,
            {
                "monto_total": "$ 12,000",
                "monto_promedio": "$ 8,000",
                "cantidad_ingresos": 2,
            },
        )

    def test_el_grafico_por_metodo_resta_la_devolucion_en_su_metodo(self):
        pago = self.pago()
        anticipo = self.fila(
            pago,
            "10000",
            Tipo.ANTICIPO,
            Estado.RETENIDO,
            metodo=MetodoPago.TRANSFERENCIA,
        )
        self.fila(
            pago,
            "4000",
            Tipo.DEVOLUCION,
            devuelve=anticipo,
            metodo=MetodoPago.TRANSFERENCIA,
        )
        self.fila(pago, "2000", metodo=MetodoPago.EFECTIVO)
        grafico = income_by_method({})
        datos = dict(
            zip(grafico["datasets"][0]["keys"], grafico["datasets"][0]["data"])
        )
        self.assertEqual(datos["transferencia"], 6000)
        self.assertEqual(datos["efectivo"], 2000)

    def test_el_dashboard_cobra_neto_y_no_factura_citas_pendientes(self):
        completada = self.pago(total="18000")
        anticipo = self.fila(completada, "10000", Tipo.ANTICIPO, Estado.RETENIDO)
        self.fila(completada, "4000", Tipo.DEVOLUCION, devuelve=anticipo)
        pendiente = self.pago(
            total="25000", estado_cita=Cita.EstadoChoices.PENDIENTE, dia=22
        )
        self.fila(pendiente, "5000", Tipo.ANTICIPO, Estado.VIGENTE)
        periodo = between(date(2026, 10, 1), date(2026, 10, 31))
        series = {
            d["key"]: d["data"]
            for d in metrics.income_billed_vs_collected(periodo)["datasets"]
        }
        self.assertEqual(sum(series["facturado"]), 18000)
        self.assertEqual(sum(series["cobrado"]), 11000)
        metodos = metrics.payment_methods(periodo)["datasets"][0]
        self.assertEqual(dict(zip(metodos["keys"], metodos["data"]))["efectivo"], 11000)
