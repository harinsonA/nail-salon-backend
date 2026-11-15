from datetime import date, time
from decimal import Decimal

from apps.appointments.engine import (
    AppointmentCompletion,
    AppointmentDraft,
    AppointmentRuleError,
    AppointmentWriter,
)
from apps.appointments.engine.messages import (
    BALANCE_PAYMENT_LABEL,
    COMPLETE_NOT_PENDING,
    FULL_PAYMENT_LABEL,
    NOTHING_TO_CHARGE,
)
from apps.appointments.models import Cita
from apps.payments.choices import EstadoPago, MetodoPago
from tests.appointments.test_crear_cita import CitaBase


class MotorCompletarTests(CitaBase):
    esquema = "motor_completar"

    def cita(self, *anticipos):
        datos = {
            "assigned_to": self.encargada,
            "services": [{"id": self.manicure.pk}],
            "advances": [{"monto": monto, "metodo": MetodoPago.EFECTIVO} for monto in anticipos],
            "reservation": None,
        }
        limpios, errores = AppointmentDraft(self.encargada).validate(datos)
        self.assertEqual(errores, {})
        return AppointmentWriter(self.encargada).create(
            {
                **limpios,
                "client": self.cliente,
                "date": date(2026, 11, 4),
                "time": time(10, 30),
                "observations": "",
            }
        )

    def completar(self, cita, monto):
        return AppointmentCompletion(cita).complete(self.encargada, monto, MetodoPago.EFECTIVO, "", "")

    def test_sin_anticipos_cobra_el_total(self):
        motor = AppointmentCompletion(self.cita())
        self.assertEqual((motor.remaining, motor.full_payment_label()), (Decimal("10000"), FULL_PAYMENT_LABEL))
        self.assertEqual(motor.amount_paid_now(True, None), Decimal("10000"))

    def test_con_anticipo_cobra_el_saldo(self):
        motor = AppointmentCompletion(self.cita(4000))
        self.assertEqual((motor.remaining, motor.full_payment_label()), (Decimal("6000"), BALANCE_PAYMENT_LABEL))
        self.assertEqual(motor.advance_part(), Decimal("4000"))

    def test_un_abono_igual_al_saldo_pide_pagar_el_saldo(self):
        motor = AppointmentCompletion(self.cita(4000))
        with self.assertRaises(AppointmentRuleError) as error:
            motor.clean_amount(False, "6000")
        self.assertEqual(error.exception.message, 'Si paga $6.000 o más, activa "Paga el saldo ahora".')
        self.assertEqual(motor.clean_amount(False, "2000"), Decimal("2000"))

    def test_sin_servicios_por_cobrar_no_hay_saldo(self):
        cita = self.cita()
        cita.detalles.update(precio_acordado=0)
        motor = AppointmentCompletion(cita)
        self.assertEqual((motor.remaining, motor.settled_hint()), (Decimal("0"), NOTHING_TO_CHARGE))
        self.assertEqual(motor.clean_amount(False, "500"), 0)

    def test_completar_deja_la_cita_completada_y_pagada(self):
        cita = self.cita(4000)
        pago = self.completar(cita, Decimal("6000"))
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.EstadoChoices.COMPLETADA)
        self.assertEqual(pago.estado_pago, EstadoPago.COMPLETADO)

    def test_no_completa_una_cita_que_no_esta_pendiente(self):
        cita = self.cita()
        cita.estado = Cita.EstadoChoices.CANCELADA
        cita.save()
        with self.assertRaises(AppointmentRuleError) as error:
            self.completar(cita, Decimal("10000"))
        self.assertEqual(error.exception.message, COMPLETE_NOT_PENDING)
