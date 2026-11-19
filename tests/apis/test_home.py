from datetime import datetime, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Cita
from apps.clients.models import Cliente
from apps.home import CalendarMonth
from apps.payments.choices import EstadoPago, MetodoPago, TipoDetallePago
from apps.payments.models import DetallePago, Pago
from apps.payments.views.debtors.list import DebtorsListView
from apps.profiles.models import Perfil
from apps.tenancy.models import Negocio
from dashboard.services import metrics, periods
from tests.apis.base import ApiTestCase

User = get_user_model()
Rol = Perfil.Rol
Estado = Cita.EstadoChoices


class HomeTests(ApiTestCase):
    esquema = "api_home"
    dominio = "api-home.localhost"

    def setUp(self):
        super().setUp()
        self.month = CalendarMonth(timezone.localdate())
        self.client_row = Cliente.objects.create(nombre="Paula", apellido="Soto", telefono="912345678")

    def colleague(self, name):
        user = User.objects.create_user(username=name, email=f"{name}@correo.cl", first_name=name.title())
        Perfil.objects.filter(user=user).update(rol=Rol.COLABORADOR, debe_cambiar_clave=False)
        return user

    def appointment(self, day, estado=Estado.PENDIENTE, assigned=None):
        return Cita.objects.create(
            cliente=self.client_row,
            fecha_agenda=day,
            hora_agenda=time(10, 0),
            estado=estado,
            asignado_a=assigned,
        )

    def moment(self, day):
        return timezone.make_aware(datetime.combine(day, time(12, 0)))

    def payment(self, appointment, estado_pago=EstadoPago.PENDIENTE):
        return Pago.objects.create(
            cita=appointment,
            monto_total_cita=Decimal("20000"),
            cliente_nombre="Paula Soto",
            fecha_cita=self.moment(appointment.fecha_agenda),
            estado_pago=estado_pago,
        )

    def paid(self, payment, day, amount, by, tipo=TipoDetallePago.ABONO):
        return DetallePago.objects.create(
            pago=payment,
            fecha_pago=self.moment(day),
            monto_pago=Decimal(amount),
            metodo_pago=MetodoPago.EFECTIVO,
            tipo_detalle=tipo,
            registrado_por=by,
        )

    def home(self):
        response = self.api_client.get(reverse("api_home"))
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def test_month_counts_completed_and_pending_without_cancelled(self):
        self.log_in_as(Rol.PROPIETARIO)
        start = self.month.start
        self.appointment(start, Estado.COMPLETADA)
        self.appointment(start, Estado.PENDIENTE)
        self.appointment(start, Estado.PENDIENTE)
        self.appointment(start, Estado.CANCELADA)
        self.appointment(self.month.previous.start, Estado.PENDIENTE)
        self.appointment(self.month.end, Estado.PENDIENTE)
        month = self.home()["month"]
        self.assertEqual(month["label"], self.month.label)
        self.assertEqual(month["start"], start.isoformat())
        self.assertEqual((month["appointments"], month["completed"], month["pending"]), (3, 1, 2))

    def test_month_matches_the_web_dashboard(self):
        self.log_in_as(Rol.ENCARGADO)
        for estado in (Estado.COMPLETADA, Estado.COMPLETADA, Estado.PENDIENTE, Estado.CANCELADA):
            self.appointment(self.month.start, estado)
        web = dict(zip(Estado.values, metrics.appointment_status(periods.last_months(1))["datasets"][0]["data"]))
        month = self.home()["month"]
        self.assertEqual(month["completed"], web[Estado.COMPLETADA])
        self.assertEqual(month["pending"], web[Estado.PENDIENTE])

    def test_debtors_and_incomes_match_the_web(self):
        owner = self.log_in_as(Rol.PROPIETARIO)
        previous = self.month.previous.start
        debt = self.payment(self.appointment(previous, Estado.COMPLETADA))
        self.paid(debt, previous, "5000", owner)
        settled = self.payment(self.appointment(self.month.start, Estado.COMPLETADA), EstadoPago.COMPLETADO)
        self.paid(settled, self.month.start, "20000", owner)
        self.paid(settled, self.month.start, "3000", owner, TipoDetallePago.DEVOLUCION)
        self.payment(self.appointment(self.month.start, Estado.PENDIENTE))
        data = self.home()
        web_debtors = DebtorsListView().get_queryset().filter(**DebtorsListView._filters).count()
        self.assertEqual(data["debtors"], web_debtors)
        self.assertEqual(data["debtors"], 1)
        collected = metrics.income_billed_vs_collected(periods.last_months(2))["datasets"][1]["data"]
        self.assertEqual([income["amount"] for income in data["incomes"]], [int(value) for value in collected])
        self.assertEqual(data["incomes"][0]["label"], self.month.previous.short_label)
        self.assertEqual(data["incomes"][1]["amount"], 17000)

    def test_collaborator_sees_only_her_appointments_and_no_money(self):
        collaborator = self.log_in_as(Rol.COLABORADOR)
        other = self.colleague("elena")
        self.appointment(self.month.start, Estado.PENDIENTE, assigned=collaborator)
        self.appointment(self.month.start, Estado.PENDIENTE, assigned=other)
        data = self.home()
        self.assertEqual(data["month"]["appointments"], 1)
        self.assertIsNone(data["debtors"])
        self.assertIsNone(data["incomes"])

    def test_overdue_pauses_the_money_like_the_web(self):
        Negocio.objects.filter(pk=self.negocio.pk).update(estado=Negocio.Estado.MOROSO)
        self.log_in_as(Rol.PROPIETARIO)
        self.appointment(self.month.start)
        data = self.home()
        self.assertEqual(data["month"]["appointments"], 1)
        self.assertIsNone(data["debtors"])
        self.assertIsNone(data["incomes"])

    def test_month_edges(self):
        december = CalendarMonth(timezone.localdate().replace(year=2026, month=12, day=15))
        self.assertEqual(december.end.isoformat(), "2027-01-01")
        self.assertEqual(december.short_label, "dic.")
        january = CalendarMonth(december.end)
        self.assertEqual(january.previous.start.isoformat(), "2026-12-01")
        self.assertEqual(january.previous.end - timedelta(days=1), december.end - timedelta(days=1))
