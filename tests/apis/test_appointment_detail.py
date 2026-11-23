from datetime import date, datetime, time
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Cita, DetalleCita
from apps.appointments.panel import AppointmentPanel
from apps.clients.models import Cliente
from apps.payments.choices import EstadoPago, MetodoPago, TipoDetallePago
from apps.payments.models import DetallePago, Pago
from apps.profiles.models import Perfil
from tests.apis.base import ApiTestCase

Rol = Perfil.Rol


class AppointmentDetailApiTests(ApiTestCase):
    esquema = "api_appointment_detail"
    dominio = "api-appointment-detail.localhost"

    def setUp(self):
        super().setUp()
        self.owner = self.log_in_as(Rol.PROPIETARIO)
        self.client_row = Cliente.objects.create(nombre="Paula", apellido="Herrera", telefono="+56911112222")

    def appointment(self, estado=Cita.EstadoChoices.PENDIENTE, assigned=None, day=date(2030, 1, 7)):
        appointment = Cita.objects.create(
            cliente=self.client_row,
            fecha_agenda=day,
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

    def payment(self, appointment):
        payment = Pago.objects.create(
            cita=appointment,
            monto_total_cita=Decimal("18000"),
            estado_pago=EstadoPago.PENDIENTE,
            cliente_nombre="Paula Herrera",
            fecha_cita=timezone.make_aware(datetime(2030, 1, 7, 10, 30)),
            atendido_por=self.owner,
            atendido_por_nombre="Ana Rojas",
        )
        DetallePago.objects.create(
            pago=payment,
            fecha_pago=timezone.make_aware(datetime(2030, 1, 7, 11, 5)),
            monto_pago=Decimal("5000"),
            metodo_pago=MetodoPago.TRANSFERENCIA,
            tipo_detalle=TipoDetallePago.ABONO,
            registrado_por=self.owner,
        )
        return payment

    def detail(self, appointment):
        return self.api_client.get(reverse("api_appointment", args=[appointment.pk]))

    def test_pending_brings_team_estimated_payment_and_creator(self):
        response = self.detail(self.appointment())
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["status"], {"key": "pendiente", "label": "Pendiente"})
        self.assertEqual(body["team"], {"label": "Asignada a", "name": "Ana Rojas (tú)"})
        self.assertIsNone(body["payment"]["badge"])
        self.assertIsNone(body["payment"]["payments"])
        self.assertEqual(
            [(row["label"], row["value"]) for row in body["payment"]["rows"]],
            [("Estado", "Se registra al completar la cita"), ("Monto estimado", "$18.000")],
        )
        self.assertEqual(body["created"]["name"], "Ana Rojas (tú)")
        self.assertTrue(body["created"]["when"])

    def test_overdue_pending_says_unclosed(self):
        body = self.detail(self.appointment(day=date(2020, 1, 6))).json()
        self.assertEqual(body["status"], {"key": "vencida", "label": "Pendiente sin cerrar"})

    def test_completed_brings_its_payments_and_debt_like_the_web(self):
        appointment = self.appointment(estado=Cita.EstadoChoices.COMPLETADA)
        self.payment(appointment)
        payment = self.detail(appointment).json()["payment"]
        self.assertEqual(payment["badge"], {"label": "Pago incompleto", "debt": True})
        self.assertIn({"label": "Saldo pendiente", "value": "$13.000", "debt": True}, payment["rows"])
        self.assertEqual(
            [(line["kind"], line["method"], line["amount"]) for line in payment["payments"]],
            [("Abono", "Transferencia", "$5.000")],
        )
        self.assertTrue(payment["can_pay"])
        web = AppointmentPanel(appointment, self.owner).context()["payment"]
        self.assertEqual(payment["payments"], web["payments"])
        self.assertEqual(payment["first"], web["first"])

    def test_cancelled_without_payment_says_so(self):
        payment = self.detail(self.appointment(estado=Cita.EstadoChoices.CANCELADA)).json()["payment"]
        self.assertEqual(payment["rows"][0]["value"], "Sin pago: la cita fue cancelada")
        self.assertFalse(payment["can_pay"])

    def test_collaborator_only_opens_her_own(self):
        collaborator = self.make_user(Rol.COLABORADOR)
        own = self.appointment(assigned=collaborator)
        others = self.appointment()
        self.api_client.force_authenticate(collaborator)
        self.assertEqual(self.detail(own).status_code, 200)
        self.assertApiError(self.detail(others), 404, "not_found")
