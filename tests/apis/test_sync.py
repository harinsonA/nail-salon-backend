from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Cita, DetalleCita
from apps.clients.models import Cliente
from apps.payments.choices import MetodoPago
from apps.payments.models import DetallePago, Pago
from apps.profiles.models import Perfil
from apps.services.models import Categoria, Servicio
from apps.services.views.categories.categoria import CategoryDetailModalView
from apps.sync import SyncWindow
from tests.apis.base import ApiTestCase

User = get_user_model()
Rol = Perfil.Rol


class SyncChangesTests(ApiTestCase):
    esquema = "api_sync"
    dominio = "api-sync.localhost"

    def setUp(self):
        super().setUp()
        self.today = timezone.localdate()
        self.category = Categoria.objects.create(nombre="Manos")
        self.service = Servicio.objects.create(
            nombre="Esmaltado", precio=Decimal("15000"), categoria=self.category
        )
        self.client_row = Cliente.objects.create(nombre="Paula", apellido="Soto", telefono="912345678")

    def colleague(self, rol, name):
        user = User.objects.create_user(username=name, email=f"{name}@correo.cl", first_name=name.title())
        Perfil.objects.filter(user=user).update(rol=rol, debe_cambiar_clave=False)
        return user

    def appointment(self, days, assigned=None, with_service=True):
        appointment = Cita.objects.create(
            cliente=self.client_row,
            fecha_agenda=self.today + timedelta(days=days),
            hora_agenda=time(10, 0),
            asignado_a=assigned,
        )
        if with_service:
            DetalleCita.objects.create(cita=appointment, servicio=self.service, cantidad_servicios=1)
        return appointment

    def age(self, *querysets):
        past = timezone.now() - timedelta(days=5)
        for queryset in querysets:
            queryset.update(modified=past)

    def age_everything(self):
        self.age(
            Cita.all_objects.all(),
            DetalleCita.objects.all(),
            Pago.all_objects.all(),
            DetallePago.objects.all(),
            Cliente.all_objects.all(),
            Categoria.all_objects.all(),
            Servicio.all_objects.all(),
        )

    def sync(self, since=None):
        params = {"since": since} if since else {}
        response = self.api_client.get(reverse("api_sync_changes"), params)
        self.assertEqual(response.status_code, 200, response.content)
        return response.json()

    def ids(self, data, name):
        return [item["id"] for item in data[name]]

    def test_full_sync_brings_the_window_and_the_catalogs(self):
        self.log_in_as(Rol.PROPIETARIO)
        inside = self.appointment(5)
        self.appointment(-SyncWindow.DAYS_BEFORE - 1)
        self.appointment(SyncWindow.DAYS_AFTER + 1)
        data = self.sync()
        self.assertTrue(data["full"])
        self.assertTrue(data["mark"])
        today = date.fromisoformat(data["window"]["start"]) + timedelta(days=SyncWindow.DAYS_BEFORE)
        self.assertEqual(data["window"]["end"], (today + timedelta(days=SyncWindow.DAYS_AFTER)).isoformat())
        self.assertEqual(self.ids(data, "appointments"), [inside.pk])
        line = data["appointments"][0]["services"][0]
        self.assertEqual(line["servicio_id"], self.service.pk)
        self.assertEqual(line["precio_servicio"], 15000)
        self.assertEqual(line["duracion_estimada_servicio"], 30)
        self.assertIsNone(data["appointments"][0]["payment"])
        self.assertEqual(self.ids(data, "clients"), [self.client_row.pk])
        self.assertEqual(self.ids(data, "categories"), [self.category.pk])
        self.assertEqual(data["services"][0]["precio"], 15000)
        self.assertEqual(data["services"][0]["categoria_id"], self.category.pk)
        self.assertEqual(data["removed"], {"appointments": [], "clients": [], "categories": [], "services": []})

    def test_payment_totals_travel_with_the_appointment(self):
        owner = self.log_in_as(Rol.PROPIETARIO)
        appointment = self.appointment(-1)
        payment = Pago.objects.create(
            cita=appointment,
            monto_total_cita=Decimal("15000"),
            cliente_nombre="Paula Soto",
            fecha_cita=timezone.now(),
        )
        DetallePago.objects.create(
            pago=payment,
            fecha_pago=timezone.now(),
            monto_pago=Decimal("5000"),
            metodo_pago=MetodoPago.EFECTIVO,
            registrado_por=owner,
        )
        payment_data = self.sync()["appointments"][0]["payment"]
        self.assertEqual(payment_data["id"], payment.pk)
        self.assertEqual(payment_data["paid"], 5000)
        self.assertEqual(payment_data["total"], 15000)
        self.assertEqual(payment_data["pending"], 10000)

    def test_collaborator_only_gets_her_appointments(self):
        collaborator = self.log_in_as(Rol.COLABORADOR)
        other = self.colleague(Rol.ENCARGADO, "elena")
        mine = self.appointment(1, assigned=collaborator)
        self.appointment(1, assigned=other)
        data = self.sync()
        self.assertEqual(self.ids(data, "appointments"), [mine.pk])
        self.assertEqual(self.ids(data, "clients"), [self.client_row.pk])
        self.assertEqual(self.ids(data, "services"), [self.service.pk])

    def test_manager_gets_every_appointment(self):
        self.log_in_as(Rol.ENCARGADO)
        other = self.colleague(Rol.COLABORADOR, "carla")
        first = self.appointment(1, assigned=other)
        second = self.appointment(2)
        self.assertEqual(self.ids(self.sync(), "appointments"), [first.pk, second.pk])

    def test_nothing_changed_returns_nothing(self):
        self.log_in_as(Rol.PROPIETARIO)
        self.appointment(1)
        self.age_everything()
        data = self.sync(self.sync()["mark"])
        self.assertFalse(data["full"])
        for name in ("appointments", "clients", "categories", "services"):
            self.assertEqual(data[name], [])
            self.assertEqual(data["removed"][name], [])

    def test_only_what_changed_after_the_mark(self):
        self.log_in_as(Rol.PROPIETARIO)
        edited = self.appointment(1)
        self.appointment(2)
        other_client = Cliente.objects.create(nombre="Rosa")
        self.age_everything()
        mark = self.sync()["mark"]
        edited.hora_agenda = time(12, 0)
        edited.save()
        other_client.nombre = "Rosa María"
        other_client.save()
        data = self.sync(mark)
        self.assertEqual(self.ids(data, "appointments"), [edited.pk])
        self.assertEqual(data["appointments"][0]["hora_agenda"], "12:00:00")
        self.assertEqual(self.ids(data, "clients"), [other_client.pk])

    def test_a_new_payment_marks_the_appointment_as_changed(self):
        owner = self.log_in_as(Rol.PROPIETARIO)
        appointment = self.appointment(-1)
        payment = Pago.objects.create(
            cita=appointment,
            monto_total_cita=Decimal("15000"),
            cliente_nombre="Paula Soto",
            fecha_cita=timezone.now(),
        )
        self.age_everything()
        mark = self.sync()["mark"]
        DetallePago.objects.create(
            pago=payment,
            fecha_pago=timezone.now(),
            monto_pago=Decimal("15000"),
            metodo_pago=MetodoPago.EFECTIVO,
            registrado_por=owner,
        )
        data = self.sync(mark)
        self.assertEqual(self.ids(data, "appointments"), [appointment.pk])
        self.assertEqual(data["appointments"][0]["payment"]["pending"], 0)

    def test_removed_rows_are_reported(self):
        self.log_in_as(Rol.PROPIETARIO)
        appointment = self.appointment(1)
        client = Cliente.objects.create(nombre="Rosa")
        service = Servicio.objects.create(nombre="Retiro", precio=Decimal("5000"))
        self.age_everything()
        mark = self.sync()["mark"]
        appointment.delete()
        client.delete()
        service.delete()
        removed = self.sync(mark)["removed"]
        self.assertEqual(removed["appointments"], [appointment.pk])
        self.assertEqual(removed["clients"], [client.pk])
        self.assertEqual(removed["services"], [service.pk])

    def test_appointment_moved_out_of_the_window_is_removed(self):
        self.log_in_as(Rol.PROPIETARIO)
        appointment = self.appointment(1)
        self.age_everything()
        mark = self.sync()["mark"]
        appointment.fecha_agenda = self.today + timedelta(days=SyncWindow.DAYS_AFTER + 10)
        appointment.save()
        data = self.sync(mark)
        self.assertEqual(data["appointments"], [])
        self.assertEqual(data["removed"]["appointments"], [appointment.pk])

    def test_appointment_reassigned_away_from_the_collaborator_is_removed(self):
        collaborator = self.log_in_as(Rol.COLABORADOR)
        other = self.colleague(Rol.ENCARGADO, "elena")
        appointment = self.appointment(1, assigned=collaborator)
        self.age_everything()
        mark = self.sync()["mark"]
        appointment.asignado_a = other
        appointment.save()
        self.assertEqual(self.sync(mark)["removed"]["appointments"], [appointment.pk])

    def test_days_entering_the_window_come_complete(self):
        self.log_in_as(Rol.PROPIETARIO)
        entering = self.appointment(SyncWindow.DAYS_AFTER - 1)
        self.appointment(SyncWindow.DAYS_AFTER - 10)
        self.age_everything()
        since = (timezone.now() - timedelta(days=3)).isoformat()
        data = self.sync(since)
        self.assertFalse(data["full"])
        self.assertEqual(self.ids(data, "appointments"), [entering.pk])

    def test_old_or_invalid_marks_get_everything(self):
        self.log_in_as(Rol.PROPIETARIO)
        appointment = self.appointment(1)
        self.age_everything()
        for since in ((timezone.now() - timedelta(days=31)).isoformat(), "ayer", "2026-01-01T10:00:00"):
            data = self.sync(since)
            self.assertTrue(data["full"], since)
            self.assertEqual(self.ids(data, "appointments"), [appointment.pk])

    def test_inactivating_a_category_marks_its_services_as_changed(self):
        self.log_in_as(Rol.PROPIETARIO)
        self.age_everything()
        mark = self.sync()["mark"]
        self.category.estado = Categoria.EstadoChoices.INACTIVO
        self.category.save()
        CategoryDetailModalView.set_services_to_inactive_when_category_is_inactivated(
            self.category, Categoria.EstadoChoices.ACTIVO, Categoria.EstadoChoices.INACTIVO
        )
        data = self.sync(mark)
        self.assertEqual(self.ids(data, "services"), [self.service.pk])
        self.assertEqual(data["services"][0]["estado"], Servicio.EstadoChoices.INACTIVO)
