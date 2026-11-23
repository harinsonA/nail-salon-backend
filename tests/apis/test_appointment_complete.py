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


class AppointmentCompleteApiTests(ApiTestCase):
    esquema = "api_appointment_complete"
    dominio = "api-appointment-complete.localhost"

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

    def advance(self, appointment, amount):
        payment = Pago.objects.create(
            cita=appointment,
            monto_total_cita=Decimal("18000"),
            estado_pago=EstadoPago.PENDIENTE,
            cliente_nombre="Paula Herrera",
            fecha_cita=timezone.make_aware(datetime(2030, 1, 7, 10, 30)),
        )
        DetallePago.objects.create(
            pago=payment,
            fecha_pago=timezone.now(),
            monto_pago=Decimal(amount),
            metodo_pago=MetodoPago.TRANSFERENCIA,
            tipo_detalle=TipoDetallePago.ANTICIPO,
            estado_detalle=EstadoDetallePago.VIGENTE,
            registrado_por=self.owner,
        )
        return payment

    def url(self, appointment):
        return reverse("api_appointment_complete", args=[appointment.pk])

    def open(self, appointment):
        return self.api_client.get(self.url(appointment))

    def confirm(self, appointment, key=None, **body):
        data = {"full_payment": True, "metodo_pago": MetodoPago.EFECTIVO, "remaining": 18000, **body}
        headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        return self.api_client.post(self.url(appointment), data, format="json", **headers)

    def installments(self, appointment):
        return list(
            DetallePago.objects.filter(pago__cita=appointment, tipo_detalle=TipoDetallePago.ABONO)
        )

    def test_open_brings_total_prepaid_and_balance(self):
        appointment = self.appointment()
        self.advance(appointment, 5000)
        response = self.open(appointment)
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(
            (body["services_total"], body["prepaid"], body["remaining"]), (18000, 5000, 13000)
        )
        self.assertEqual(body["credit"], [{"label": "Anticipo", "amount": 5000}])
        self.assertEqual(body["full_payment_label"], "Pago completo")
        self.assertIsNone(body["settled_hint"])
        self.assertIsNone(body["blocked"])
        self.assertIsNone(body["reservation"])
        self.assertEqual(body["attended_by"], "Ana Rojas (tú)")

    def test_open_settled_says_there_is_nothing_to_charge(self):
        appointment = self.appointment()
        self.advance(appointment, 18000)
        body = self.open(appointment).json()
        self.assertEqual(body["remaining"], 0)
        self.assertIn("hoy no hay nada que cobrar", body["settled_hint"])

    def test_full_payment_completes_and_settles(self):
        appointment = self.appointment()
        response = self.confirm(appointment, referencia_pago="ignorada")
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertIn("fue completada", body["message"])
        self.assertEqual(body["appointment"]["estado"], Cita.EstadoChoices.COMPLETADA)
        appointment.refresh_from_db()
        self.assertEqual(appointment.estado, Cita.EstadoChoices.COMPLETADA)
        payment = Pago.objects.get(cita=appointment)
        self.assertEqual(payment.estado_pago, EstadoPago.COMPLETADO)
        [row] = self.installments(appointment)
        self.assertEqual((row.monto_pago, row.referencia_pago), (Decimal("18000"), None))

    def test_partial_payment_keeps_the_debt(self):
        appointment = self.appointment()
        self.advance(appointment, 5000)
        response = self.confirm(
            appointment,
            full_payment=False,
            monto_pago=3000,
            metodo_pago=MetodoPago.TRANSFERENCIA,
            referencia_pago="op-1",
            notas_detalle="Paga el resto el lunes",
            remaining=13000,
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Pago.objects.get(cita=appointment).estado_pago, EstadoPago.PENDIENTE)
        [row] = self.installments(appointment)
        self.assertEqual(
            (row.monto_pago, row.metodo_pago, row.referencia_pago, row.notas_detalle),
            (Decimal("3000"), MetodoPago.TRANSFERENCIA, "op-1", "Paga el resto el lunes"),
        )

    def test_zero_completes_without_a_payment_row(self):
        appointment = self.appointment()
        response = self.confirm(appointment, full_payment=False, monto_pago=0)
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.installments(appointment), [])
        self.assertEqual(Pago.objects.get(cita=appointment).estado_pago, EstadoPago.PENDIENTE)

    def test_partial_equal_to_the_balance_is_rejected_like_the_web(self):
        appointment = self.appointment()
        response = self.confirm(appointment, full_payment=False, monto_pago=18000)
        self.assertApiError(response, 400, "invalid_data")
        self.assertIn("monto_pago", response.json()["fields"])
        appointment.refresh_from_db()
        self.assertEqual(appointment.estado, Cita.EstadoChoices.PENDIENTE)

    def test_balance_changed_elsewhere_is_a_conflict(self):
        appointment = self.appointment()
        self.advance(appointment, 5000)
        self.assertApiError(self.confirm(appointment, remaining=18000), 409, "conflict")
        self.assertEqual(self.installments(appointment), [])

    def test_not_pending_is_a_conflict(self):
        appointment = self.appointment(estado=Cita.EstadoChoices.COMPLETADA)
        self.assertApiError(self.open(appointment), 409, "conflict")
        self.assertApiError(self.confirm(appointment), 409, "conflict")

    def test_retry_with_the_same_key_completes_once(self):
        appointment = self.appointment()
        first = self.confirm(appointment, key="clave-1")
        second = self.confirm(appointment, key="clave-1")
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.json(), second.json())
        self.assertEqual(len(self.installments(appointment)), 1)

    def test_collaborator_only_completes_her_own(self):
        collaborator = self.make_user(Rol.COLABORADOR)
        own = self.appointment(assigned=collaborator)
        others = self.appointment()
        self.api_client.force_authenticate(collaborator)
        self.assertEqual(self.open(own).status_code, 200)
        self.assertApiError(self.open(others), 404, "not_found")
        self.assertEqual(self.confirm(own).status_code, 200)
