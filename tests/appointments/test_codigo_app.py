import uuid
from datetime import date, time

from django.db import IntegrityError, transaction

from apps.appointments.models import Cita
from apps.clients.models import Cliente
from tests.base import NegocioTestCase


class CodigoAppTests(NegocioTestCase):
    esquema = "codigo_app"

    def nueva_cita(self, cliente, **campos):
        return Cita.objects.create(
            cliente=cliente,
            fecha_agenda=date(2026, 11, 20),
            hora_agenda=time(10, 0),
            **campos,
        )

    def test_queda_vacio_si_no_viene_de_la_app(self):
        cliente = Cliente.objects.create(nombre="Laura")
        cita = self.nueva_cita(cliente)
        otra = self.nueva_cita(cliente)
        self.assertIsNone(cliente.codigo_app)
        self.assertIsNone(cita.codigo_app)
        self.assertIsNone(otra.codigo_app)

    def test_cliente_no_repite_el_codigo(self):
        codigo = uuid.uuid4()
        Cliente.objects.create(nombre="Laura", codigo_app=codigo)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Cliente.objects.create(nombre="Paula", codigo_app=codigo)

    def test_cita_no_repite_el_codigo(self):
        cliente = Cliente.objects.create(nombre="Laura")
        codigo = uuid.uuid4()
        self.nueva_cita(cliente, codigo_app=codigo)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            self.nueva_cita(cliente, codigo_app=codigo)

    def test_el_historial_guarda_el_codigo(self):
        codigo = uuid.uuid4()
        cliente = Cliente.objects.create(nombre="Laura", codigo_app=codigo)
        cita = self.nueva_cita(cliente, codigo_app=codigo)
        self.assertEqual(cliente.history.first().codigo_app, codigo)
        self.assertEqual(cita.history.first().codigo_app, codigo)
