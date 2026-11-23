from datetime import date, datetime, time
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Cita, DetalleCita
from apps.clients.models import Cliente
from apps.payments.choices import EstadoDetallePago, EstadoPago, MetodoPago, TipoDetallePago
from apps.payments.models import DetallePago, Pago
from apps.profiles.models import Perfil
from tests.apis.base import ApiTestCase

Rol = Perfil.Rol


class PrepaidDecisionTestCase(ApiTestCase):
    def setUp(self):
        super().setUp()
        self.owner = self.log_in_as(Rol.PROPIETARIO)
        self.client_row = Cliente.objects.create(nombre="Paula", apellido="Herrera")

    def appointment(self, assigned=None, estado=Cita.EstadoChoices.PENDIENTE):
        appointment = Cita.objects.create(
            cliente=self.client_row,
            fecha_agenda=date(2030, 1, 7),
            hora_agenda=time(10, 30),
            estado=estado,
            creado_por=self.owner,
            asignado_a=assigned or self.owner,
        )
        DetalleCita.objects.create(
            cita=appointment,
            nombre_servicio="Manicure",
            precio_servicio=Decimal("10000"),
            cantidad_servicios=2,
            descuento=Decimal("2000"),
            precio_acordado=Decimal("18000"),
        )
        return appointment

    def payment_of(self, appointment):
        return Pago.objects.get_or_create(
            cita=appointment,
            defaults={
                "monto_total_cita": Decimal("18000"),
                "estado_pago": EstadoPago.PENDIENTE,
                "cliente_nombre": "Paula Herrera",
                "fecha_cita": timezone.make_aware(datetime(2030, 1, 7, 10, 30)),
            },
        )[0]

    def prepaid(self, appointment, amount, kind=TipoDetallePago.ANTICIPO, estado=None):
        return DetallePago.objects.create(
            pago=self.payment_of(appointment),
            fecha_pago=timezone.now(),
            monto_pago=Decimal(amount),
            metodo_pago=MetodoPago.TRANSFERENCIA,
            tipo_detalle=kind,
            estado_detalle=estado or EstadoDetallePago.VIGENTE,
            registrado_por=self.owner,
        )

    @staticmethod
    def seen(*rows):
        return [{"id": row.pk, "amount": int(row.monto_pago)} for row in rows]

    def open(self, appointment):
        return self.api_client.get(self.url(appointment))

    def send(self, appointment, body, key=None):
        headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        return self.api_client.post(self.url(appointment), body, format="json", **headers)

    @staticmethod
    def status_of(row):
        row.refresh_from_db()
        return row.estado_detalle


class AppointmentCancelApiTests(PrepaidDecisionTestCase):
    esquema = "api_appointment_cancel"
    dominio = "api-appointment-cancel.localhost"

    def url(self, appointment):
        return reverse("api_appointment_cancel", args=[appointment.pk])

    def test_open_brings_the_rows_and_the_web_texts(self):
        appointment = self.appointment()
        reservation = self.prepaid(appointment, 5000, TipoDetallePago.RESERVA)
        advance = self.prepaid(appointment, 10000)
        response = self.open(appointment)
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["title"], "¿Qué hacemos con la reserva y los anticipos?")
        self.assertFalse(body["locked"])
        self.assertIsNone(body["locked_message"])
        self.assertEqual([row["id"] for row in body["rows"]], [reservation.pk, advance.pk])
        self.assertEqual(
            (body["rows"][0]["kind"], body["rows"][0]["reservation"], body["rows"][0]["discounts"]),
            ("Reserva", True, False),
        )
        self.assertEqual(
            [method["value"] for method in body["refund_methods"]],
            [MetodoPago.EFECTIVO, MetodoPago.TRANSFERENCIA],
        )

    def test_open_without_payments_has_no_card(self):
        body = self.open(self.appointment()).json()
        self.assertEqual((body["rows"], body["title"], body["locked"]), ([], None, False))

    def test_refunds_one_and_retains_the_other(self):
        appointment = self.appointment()
        reservation = self.prepaid(appointment, 5000, TipoDetallePago.RESERVA)
        advance = self.prepaid(appointment, 10000)
        refunds = [{"id": advance.pk, "metodo": MetodoPago.TRANSFERENCIA, "referencia": " op-9 "}]
        response = self.send(
            appointment, {"refunds": refunds, "seen": self.seen(reservation, advance)}
        )
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertIn("fue cancelada", body["message"])
        self.assertEqual(body["appointment"]["estado"], Cita.EstadoChoices.CANCELADA)
        self.assertEqual(self.status_of(reservation), EstadoDetallePago.RETENIDO)
        self.assertEqual(self.status_of(advance), EstadoDetallePago.DEVUELTO)
        refund = DetallePago.objects.get(detalle_devuelto=advance)
        self.assertEqual(
            (refund.tipo_detalle, refund.monto_pago, refund.referencia_pago),
            (TipoDetallePago.DEVOLUCION, Decimal("10000"), "op-9"),
        )
        self.assertEqual(Pago.objects.get(cita=appointment).estado_pago, EstadoPago.COMPLETADO)

    def test_cancels_without_payments(self):
        appointment = self.appointment()
        response = self.send(appointment, {"refunds": [], "seen": []})
        self.assertEqual(response.status_code, 200, response.content)
        appointment.refresh_from_db()
        self.assertEqual(appointment.estado, Cita.EstadoChoices.CANCELADA)

    def test_invalid_refund_is_rejected_like_the_web(self):
        appointment = self.appointment()
        advance = self.prepaid(appointment, 10000)
        refunds = [{"id": advance.pk, "metodo": MetodoPago.TARJETA}]
        response = self.send(appointment, {"refunds": refunds, "seen": self.seen(advance)})
        self.assertApiError(response, 400, "invalid_data")
        self.assertIn("refunds", response.json()["fields"])
        appointment.refresh_from_db()
        self.assertEqual(appointment.estado, Cita.EstadoChoices.PENDIENTE)

    def test_payments_changed_elsewhere_is_a_conflict(self):
        appointment = self.appointment()
        advance = self.prepaid(appointment, 10000)
        stale = [{"id": advance.pk, "amount": 8000}]
        self.assertApiError(self.send(appointment, {"refunds": [], "seen": stale}), 409, "conflict")
        self.assertEqual(self.status_of(advance), EstadoDetallePago.VIGENTE)

    def test_not_pending_is_a_conflict(self):
        appointment = self.appointment(estado=Cita.EstadoChoices.COMPLETADA)
        self.assertApiError(self.open(appointment), 409, "conflict")
        self.assertApiError(self.send(appointment, {"refunds": [], "seen": []}), 409, "conflict")

    def test_retry_with_the_same_key_cancels_once(self):
        appointment = self.appointment()
        advance = self.prepaid(appointment, 10000)
        refunds = [{"id": advance.pk, "metodo": MetodoPago.EFECTIVO}]
        body = {"refunds": refunds, "seen": self.seen(advance)}
        first = self.send(appointment, body, key="clave-1")
        second = self.send(appointment, body, key="clave-1")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(DetallePago.objects.filter(detalle_devuelto=advance).count(), 1)

    def test_collaborator_cannot_decide_on_payments(self):
        collaborator = self.make_user(Rol.COLABORADOR)
        with_payments = self.appointment(assigned=collaborator)
        advance = self.prepaid(with_payments, 10000)
        without_payments = self.appointment(assigned=collaborator)
        others = self.appointment()
        self.api_client.force_authenticate(collaborator)
        body = self.open(with_payments).json()
        self.assertTrue(body["locked"])
        self.assertIn("Solo la propietaria o la encargada", body["locked_message"])
        response = self.send(with_payments, {"refunds": [], "seen": self.seen(advance)})
        self.assertApiError(response, 403, "forbidden")
        self.assertEqual(self.status_of(advance), EstadoDetallePago.VIGENTE)
        self.assertApiError(self.open(others), 404, "not_found")
        response = self.send(without_payments, {"refunds": [], "seen": []})
        self.assertEqual(response.status_code, 200, response.content)


class AppointmentRestoreApiTests(PrepaidDecisionTestCase):
    esquema = "api_appointment_restore"
    dominio = "api-appointment-restore.localhost"

    def url(self, appointment):
        return reverse("api_appointment_restore", args=[appointment.pk])

    def cancelled(self, assigned=None):
        appointment = self.appointment(assigned=assigned, estado=Cita.EstadoChoices.CANCELADA)
        reservation = self.prepaid(
            appointment, 5000, TipoDetallePago.RESERVA, EstadoDetallePago.RETENIDO
        )
        advance = self.prepaid(appointment, 8000, estado=EstadoDetallePago.RETENIDO)
        return appointment, reservation, advance

    def test_open_brings_retained_rows_and_totals(self):
        appointment, reservation, advance = self.cancelled()
        response = self.open(appointment)
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(
            body["title"], "¿Restauramos también la reserva y los anticipos retenidos?"
        )
        self.assertEqual(body["back_label"], "Restaurado")
        self.assertEqual([row["id"] for row in body["rows"]], [reservation.pk, advance.pk])
        self.assertEqual((body["services_total"], body["prepaid"]), (18000, 0))

    def test_restores_the_chosen_and_keeps_the_rest_for_good(self):
        appointment, reservation, advance = self.cancelled()
        body = {"restored": [advance.pk], "seen": self.seen(reservation, advance)}
        response = self.send(appointment, body)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn("fue restaurada a Pendiente", response.json()["message"])
        appointment.refresh_from_db()
        self.assertEqual(appointment.estado, Cita.EstadoChoices.PENDIENTE)
        self.assertEqual(self.status_of(advance), EstadoDetallePago.VIGENTE)
        self.assertEqual(self.status_of(reservation), EstadoDetallePago.RETENIDO_DEFINITIVO)
        self.assertEqual(Pago.objects.get(cita=appointment).estado_pago, EstadoPago.PENDIENTE)

    def test_invalid_restored_is_rejected_like_the_web(self):
        appointment, reservation, advance = self.cancelled()
        body = {"restored": [advance.pk, advance.pk], "seen": self.seen(reservation, advance)}
        response = self.send(appointment, body)
        self.assertApiError(response, 400, "invalid_data")
        self.assertIn("restored", response.json()["fields"])

    def test_payments_changed_elsewhere_is_a_conflict(self):
        appointment, reservation, _ = self.cancelled()
        response = self.send(appointment, {"restored": [], "seen": self.seen(reservation)})
        self.assertApiError(response, 409, "conflict")

    def test_not_cancelled_is_a_conflict(self):
        appointment = self.appointment()
        self.assertApiError(self.open(appointment), 409, "conflict")

    def test_collaborator_cannot_decide_on_retained_payments(self):
        collaborator = self.make_user(Rol.COLABORADOR)
        appointment, reservation, advance = self.cancelled(assigned=collaborator)
        self.api_client.force_authenticate(collaborator)
        self.assertTrue(self.open(appointment).json()["locked"])
        response = self.send(appointment, {"restored": [], "seen": self.seen(reservation, advance)})
        self.assertApiError(response, 403, "forbidden")
