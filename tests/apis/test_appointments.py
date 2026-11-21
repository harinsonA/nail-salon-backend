import uuid
from decimal import Decimal

from django.urls import reverse

from apis.v1.sync.serializers import AppointmentSerializer
from apps.appointments.models import Cita
from apps.clients.models import Cliente
from apps.payments.choices import MetodoPago, TipoDetallePago
from apps.payments.models import DetallePago
from apps.profiles.models import Perfil
from apps.services.models import Categoria, Servicio
from apps.settings.preferences import (
    RESERVATION_AMOUNT,
    RESERVATION_DISCOUNTS_TOTAL,
    RESERVATION_ENABLED,
    RESERVATION_PAYMENT_METHOD,
)
from tests.apis.base import ApiTestCase

Rol = Perfil.Rol
DATE = "2026-12-04"


class AppointmentsApiTests(ApiTestCase):
    esquema = "api_appointments"
    dominio = "api-appointments.localhost"

    def setUp(self):
        super().setUp()
        self.client_row = Cliente.objects.create(nombre="Paula", apellido="Herrera")
        category = Categoria.objects.create(nombre="Manos")
        self.manicure = Servicio.objects.create(nombre="Manicure", precio=Decimal("15000"), categoria=category)
        self.design = Servicio.objects.create(nombre="Diseño", precio=Decimal("3000"), categoria=category)

    def turn_on_reservation(self, discounts=True):
        RESERVATION_ENABLED.set(True)
        RESERVATION_AMOUNT.set(5000)
        RESERVATION_DISCOUNTS_TOTAL.set(discounts)
        RESERVATION_PAYMENT_METHOD.set(MetodoPago.TRANSFERENCIA)

    @staticmethod
    def summary(subtotal, discounts=0, reservation=0, advances=0, credit=None):
        total = subtotal - discounts
        credit = reservation if credit is None else credit
        return {
            "subtotal": subtotal,
            "discounts": discounts,
            "total": total,
            "reservation": reservation,
            "advances": advances,
            "balance": max(0, total - credit - advances),
        }

    def payload(self, user, **data):
        return {
            "cliente_id": self.client_row.pk,
            "asignado_a_id": user.pk,
            "fecha_agenda": DATE,
            "hora_agenda": "11:40",
            "observaciones": "Quiere diseño francés.",
            "services": [{"servicio_id": self.manicure.pk, "cantidad_servicios": 1, "descuento": 0, "precio_servicio": 15000}],
            "summary": self.summary(15000),
            **data,
        }

    def create(self, data, key=None):
        headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        return self.api_client.post(reverse("api_appointments"), data, format="json", **headers)

    def edit(self, appointment, data, key=None):
        headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        url = reverse("api_appointment", kwargs={"pk": appointment.pk})
        return self.api_client.put(url, data, format="json", **headers)

    def version(self, appointment):
        appointment.refresh_from_db()
        return AppointmentSerializer(appointment).data["modified"]

    def test_creates_with_services_advance_and_reservation_like_the_web(self):
        self.turn_on_reservation()
        user = self.log_in_as(Rol.ENCARGADO)
        code = uuid.uuid4()
        response = self.create(
            self.payload(
                user,
                codigo_app=str(code),
                services=[
                    {"servicio_id": self.manicure.pk, "precio_servicio": 15000},
                    {"servicio_id": self.design.pk, "cantidad_servicios": 1, "descuento": 1000, "precio_servicio": 3000},
                ],
                advances=[{"monto_pago": 10000, "metodo_pago": MetodoPago.TRANSFERENCIA, "referencia_pago": "OP-1"}],
                reservation={"active": True, "metodo_pago": MetodoPago.TRANSFERENCIA, "referencia_pago": "OP-2"},
                summary=self.summary(18000, discounts=1000, reservation=5000, advances=10000),
            )
        )
        self.assertEqual(response.status_code, 201, response.content)
        data = response.json()
        self.assertTrue(data["message"].startswith("Cita agendada: Paula Herrera"))
        appointment = Cita.objects.get()
        self.assertEqual(appointment.codigo_app, code)
        self.assertEqual(appointment.asignado_a, user)
        self.assertEqual(data["appointment"]["id"], appointment.pk)
        self.assertEqual(data["appointment"]["payment"]["total"], 17000)
        self.assertEqual(data["appointment"]["payment"]["pending"], 2000)
        kinds = sorted(row["tipo_detalle"] for row in data["appointment"]["payment"]["prepaid"])
        self.assertEqual(kinds, sorted([TipoDetallePago.ANTICIPO, TipoDetallePago.RESERVA_DESCONTABLE]))

    def test_summary_that_differs_from_the_server_saves_nothing(self):
        user = self.log_in_as(Rol.PROPIETARIO)
        response = self.create(self.payload(user, summary=self.summary(14000)))
        self.assertApiError(response, 400, "summary_mismatch")
        self.assertEqual(response.json()["differences"], ["subtotal", "total", "balance"])
        self.assertEqual(response.json()["summary"]["total"], 15000)
        self.assertFalse(Cita.objects.exists())

    def test_separate_reservation_does_not_lower_the_balance(self):
        self.turn_on_reservation(discounts=False)
        user = self.log_in_as(Rol.PROPIETARIO)
        response = self.create(
            self.payload(
                user,
                reservation={"active": True, "metodo_pago": MetodoPago.EFECTIVO},
                summary=self.summary(15000, reservation=5000, credit=0),
            )
        )
        self.assertEqual(response.status_code, 201, response.content)

    def test_keeps_the_price_the_app_showed_when_it_went_up(self):
        user = self.log_in_as(Rol.PROPIETARIO)
        Servicio.objects.filter(pk=self.manicure.pk).update(precio=Decimal("18000"))
        response = self.create(self.payload(user))
        self.assertEqual(response.status_code, 201, response.content)
        detail = Cita.objects.get().detalles.get()
        self.assertEqual(detail.precio_servicio, Decimal("15000"))
        self.assertEqual(detail.precio_acordado, Decimal("15000"))

    def test_a_lower_price_is_reported_and_nothing_is_saved(self):
        user = self.log_in_as(Rol.PROPIETARIO)
        Servicio.objects.filter(pk=self.manicure.pk).update(precio=Decimal("12000"))
        response = self.create(self.payload(user))
        self.assertApiError(response, 400, "prices_lowered")
        self.assertEqual(
            response.json()["services"],
            [{"servicio_id": self.manicure.pk, "nombre_servicio": "Manicure", "precio_servicio": 12000}],
        )
        self.assertFalse(Cita.objects.exists())

    def test_repeated_codigo_app_returns_the_same_appointment(self):
        user = self.log_in_as(Rol.PROPIETARIO)
        data = self.payload(user, codigo_app=str(uuid.uuid4()))
        first = self.create(data)
        second = self.create(data)
        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(second.status_code, 200, second.content)
        self.assertEqual(Cita.objects.count(), 1)

    def test_form_errors_come_with_api_names(self):
        self.log_in_as(Rol.PROPIETARIO)
        response = self.create({"services": [], "summary": self.summary(0)})
        self.assertApiError(response, 400, "invalid_data")
        fields = response.json()["fields"]
        for field in ("cliente_id", "fecha_agenda", "hora_agenda", "services"):
            self.assertIn(field, fields)

    def test_collaborator_is_always_assigned_to_herself(self):
        other = self.make_user(Rol.ENCARGADO)
        collaborator = self.log_in_as(Rol.COLABORADOR)
        response = self.create(self.payload(other))
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(Cita.objects.get().asignado_a, collaborator)

    def created(self, user, **data):
        response = self.create(self.payload(user, **data))
        self.assertEqual(response.status_code, 201, response.content)
        return Cita.objects.get(pk=response.json()["appointment"]["id"])

    def test_edits_keeping_saved_lines_and_advances(self):
        user = self.log_in_as(Rol.PROPIETARIO)
        appointment = self.created(
            user,
            advances=[{"monto_pago": 5000, "metodo_pago": MetodoPago.EFECTIVO}],
            summary=self.summary(15000, advances=5000),
        )
        Servicio.objects.filter(pk=self.manicure.pk).update(precio=Decimal("20000"))
        detail = appointment.detalles.get()
        advance = DetallePago.objects.get()
        response = self.edit(
            appointment,
            self.payload(
                user,
                hora_agenda="12:30",
                version=self.version(appointment),
                services=[
                    {"detalle_id": detail.pk, "cantidad_servicios": 1, "descuento": 0},
                    {"servicio_id": self.design.pk, "precio_servicio": 3000},
                ],
                advances=[{"id": advance.pk, "monto_pago": 6000, "metodo_pago": MetodoPago.EFECTIVO}],
                summary=self.summary(18000, advances=6000),
            ),
        )
        self.assertEqual(response.status_code, 200, response.content)
        self.assertTrue(response.json()["message"].startswith("Cita actualizada"))
        appointment.refresh_from_db()
        self.assertEqual(appointment.hora_agenda.strftime("%H:%M"), "12:30")
        self.assertEqual(appointment.detalles.count(), 2)
        advance.refresh_from_db()
        self.assertEqual(advance.monto_pago, Decimal("6000"))

    def test_edit_with_an_old_version_is_a_conflict(self):
        user = self.log_in_as(Rol.PROPIETARIO)
        appointment = self.created(user)
        old = self.version(appointment)
        Cita.objects.filter(pk=appointment.pk).update(observaciones="Cambio en la web")
        appointment.save()
        response = self.edit(appointment, self.payload(user, version=old))
        self.assertApiError(response, 409, "conflict")

    def test_only_pending_appointments_can_be_edited(self):
        user = self.log_in_as(Rol.PROPIETARIO)
        appointment = self.created(user)
        Cita.objects.filter(pk=appointment.pk).update(estado=Cita.EstadoChoices.CANCELADA)
        response = self.edit(appointment, self.payload(user))
        self.assertApiError(response, 409, "conflict")

    def test_collaborator_cannot_edit_someone_elses_appointment(self):
        owner = self.log_in_as(Rol.PROPIETARIO)
        appointment = self.created(owner)
        self.log_in_as(Rol.COLABORADOR)
        response = self.edit(appointment, self.payload(owner))
        self.assertApiError(response, 404, "not_found")

    def test_a_repeated_idempotency_key_answers_the_same_without_conflict(self):
        user = self.log_in_as(Rol.PROPIETARIO)
        appointment = self.created(user)
        data = self.payload(user, hora_agenda="13:00", version=self.version(appointment))
        first = self.edit(appointment, data, key="clave-1")
        second = self.edit(appointment, data, key="clave-1")
        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(second.status_code, 200, second.content)
        self.assertEqual(first.json(), second.json())
        third = self.edit(appointment, data, key="clave-2")
        self.assertApiError(third, 409, "conflict")

    def test_sync_brings_the_open_advances_and_reservation(self):
        self.turn_on_reservation()
        user = self.log_in_as(Rol.PROPIETARIO)
        self.created(
            user,
            advances=[{"monto_pago": 4000, "metodo_pago": MetodoPago.EFECTIVO}],
            reservation={"active": True, "metodo_pago": MetodoPago.EFECTIVO},
            summary=self.summary(15000, reservation=5000, advances=4000),
        )
        response = self.api_client.get(reverse("api_sync_changes"))
        prepaid = response.json()["appointments"][0]["payment"]["prepaid"]
        self.assertEqual([row["monto_pago"] for row in prepaid], [5000, 4000])
