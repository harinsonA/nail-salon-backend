from datetime import date, time
from decimal import Decimal

from apps.appointments.engine import (
    AppointmentCancellation,
    AppointmentDraft,
    AppointmentLockedError,
    AppointmentRestoration,
    AppointmentRuleError,
    AppointmentWriter,
)
from apps.appointments.engine.messages import (
    CANCEL_NOT_PENDING,
    REFUNDS_INVALID,
    RESTORE_NOT_CANCELLED,
    RESTORED_INVALID,
)
from apps.appointments.models import Cita
from apps.payments.choices import EstadoDetallePago, EstadoPago, MetodoPago
from tests.appointments.test_crear_cita import CitaBase


class MotorCancelarRestaurarTests(CitaBase):
    esquema = "motor_cancelar_restaurar"

    def cita(self, *anticipos, asignada=None):
        datos = {
            "assigned_to": asignada or self.encargada,
            "services": [{"id": self.manicure.pk}],
            "advances": [{"monto": monto, "metodo": MetodoPago.EFECTIVO} for monto in anticipos],
            "reservation": None,
        }
        limpios, errores = AppointmentDraft(self.encargada).validate(datos)
        self.assertEqual(errores, {})
        return AppointmentWriter(self.encargada).create(
            {**limpios, "client": self.cliente, "date": date(2026, 11, 4), "time": time(10, 30), "observations": ""}
        )

    def estados(self, cita):
        return list(cita.pago.detalles_pago.order_by("pk").values_list("estado_detalle", flat=True))

    def test_cancelar_reembolsa_uno_y_retiene_el_otro(self):
        cita = self.cita(2000, 3000)
        motor = AppointmentCancellation(cita, self.encargada)
        primero, segundo = motor.rows
        reembolsos = motor.clean_refunds([{"id": primero.pk, "metodo": MetodoPago.EFECTIVO}])
        motor.cancel(reembolsos)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.EstadoChoices.CANCELADA)
        primero.refresh_from_db()
        segundo.refresh_from_db()
        self.assertEqual(
            (primero.estado_detalle, segundo.estado_detalle),
            (EstadoDetallePago.DEVUELTO, EstadoDetallePago.RETENIDO),
        )
        self.assertEqual(cita.pago.estado_pago, EstadoPago.COMPLETADO)

    def test_reembolsos_invalidos(self):
        motor = AppointmentCancellation(self.cita(2000), self.encargada)
        fila = motor.rows[0]
        casos = [
            {"id": fila.pk},
            [{"id": 999999, "metodo": MetodoPago.EFECTIVO}],
            [{"id": fila.pk, "metodo": MetodoPago.EFECTIVO}] * 2,
            [{"id": fila.pk, "metodo": MetodoPago.EFECTIVO, "referencia": "x" * 101}],
        ]
        for reembolsos in casos:
            with self.subTest(reembolsos=reembolsos), self.assertRaises(AppointmentRuleError) as error:
                motor.clean_refunds(reembolsos)
            self.assertEqual(error.exception.message, REFUNDS_INVALID)

    def test_la_colaboradora_no_cancela_con_anticipos(self):
        cita = self.cita(2000, asignada=self.colaboradora)
        with self.assertRaises(AppointmentLockedError):
            AppointmentCancellation(cita, self.colaboradora).check()
        AppointmentCancellation(self.cita(asignada=self.colaboradora), self.colaboradora).check()

    def test_no_cancela_una_cita_cancelada(self):
        cita = self.cita()
        AppointmentCancellation(cita, self.encargada).cancel({})
        with self.assertRaises(AppointmentRuleError) as error:
            AppointmentCancellation(cita, self.encargada).check()
        self.assertEqual(error.exception.message, CANCEL_NOT_PENDING)

    def test_restaurar_devuelve_lo_elegido_y_lo_demas_queda_definitivo(self):
        cita = self.cita(2000, 3000)
        AppointmentCancellation(cita, self.encargada).cancel({})
        motor = AppointmentRestoration(cita, self.encargada)
        primero = motor.rows[0]
        motor.restore(motor.clean_restored([primero.pk]))
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.EstadoChoices.PENDIENTE)
        self.assertEqual(
            self.estados(cita), [EstadoDetallePago.VIGENTE, EstadoDetallePago.RETENIDO_DEFINITIVO]
        )
        self.assertEqual(cita.pago.estado_pago, EstadoPago.PENDIENTE)
        self.assertEqual(cita.pago.monto_total_cita, Decimal("13000"))

    def test_restaurados_invalidos_y_estado(self):
        cita = self.cita(2000)
        with self.assertRaises(AppointmentRuleError) as error:
            AppointmentRestoration(cita, self.encargada).check()
        self.assertEqual(error.exception.message, RESTORE_NOT_CANCELLED)
        AppointmentCancellation(cita, self.encargada).cancel({})
        motor = AppointmentRestoration(cita, self.encargada)
        for restaurados in ([True], [999999], [motor.rows[0].pk] * 2, "1"):
            with self.subTest(restaurados=restaurados), self.assertRaises(AppointmentRuleError) as error:
                motor.clean_restored(restaurados)
            self.assertEqual(error.exception.message, RESTORED_INVALID)
