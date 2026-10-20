from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import ProtectedError
from django.utils import timezone

from apps.appointments.models import Cita
from apps.clients.models import Cliente
from apps.payments.choices import MetodoPago
from apps.payments.models import DetallePago, Pago
from tests.base import NegocioTestCase

User = get_user_model()


class ColumnasDeEquipoTests(NegocioTestCase):
    def setUp(self):
        super().setUp()
        self.cliente = Cliente.objects.create(nombre="Clienta")

    def crear_usuario(self, username):
        return User.objects.create_user(
            username=username,
            email=f"{username}@correo.cl",
            first_name=username.title(),
        )

    def crear_cita(self, **datos):
        return Cita.objects.create(
            cliente=self.cliente,
            fecha_agenda=date(2026, 10, 20),
            hora_agenda=time(10, 0),
            **datos,
        )

    def crear_pago(self, cita, **datos):
        return Pago.objects.create(
            cita=cita,
            monto_total_cita=Decimal("10000"),
            cliente_nombre="Clienta",
            fecha_cita=timezone.now(),
            **datos,
        )

    def crear_abono(self, pago, **datos):
        return DetallePago.objects.create(
            pago=pago,
            fecha_pago=timezone.now(),
            monto_pago=Decimal("5000"),
            metodo_pago=MetodoPago.EFECTIVO,
            **datos,
        )

    def test_cita_pago_y_abono_se_guardan_sin_los_campos_nuevos(self):
        cita = self.crear_cita()
        pago = self.crear_pago(cita)
        abono = self.crear_abono(pago)
        cita.refresh_from_db()
        pago.refresh_from_db()
        abono.refresh_from_db()
        self.assertIsNone(cita.creado_por)
        self.assertIsNone(cita.asignado_a)
        self.assertIsNone(pago.atendido_por)
        self.assertIsNone(pago.atendido_por_nombre)
        self.assertIsNone(abono.registrado_por)

    def test_las_relaciones_quedan_desde_cada_usuario(self):
        encargada = self.crear_usuario("encargada")
        camila = self.crear_usuario("camila")
        cita = self.crear_cita(creado_por=encargada, asignado_a=camila)
        pago = self.crear_pago(cita, atendido_por=camila, atendido_por_nombre="Camila")
        abono = self.crear_abono(pago, registrado_por=encargada)
        self.assertEqual(list(encargada.citas_creadas.all()), [cita])
        self.assertEqual(list(camila.citas_asignadas.all()), [cita])
        self.assertEqual(list(camila.pagos_atendidos.all()), [pago])
        self.assertEqual(list(encargada.abonos_registrados.all()), [abono])

    def test_reasignar_queda_en_el_historial(self):
        encargada = self.crear_usuario("encargada")
        camila = self.crear_usuario("camila")
        cita = self.crear_cita(creado_por=encargada, asignado_a=encargada)
        cita.asignado_a = camila
        cita.save()
        self.assertEqual(
            list(cita.history.values_list("asignado_a_id", flat=True)),
            [camila.pk, encargada.pk],
        )

    def test_no_se_borra_un_usuario_con_citas_asignadas(self):
        camila = self.crear_usuario("camila")
        self.crear_cita(asignado_a=camila)
        with self.assertRaises(ProtectedError):
            camila.delete()

    def test_no_se_borra_un_usuario_con_pagos_atendidos(self):
        camila = self.crear_usuario("camila")
        self.crear_pago(self.crear_cita(), atendido_por=camila)
        with self.assertRaises(ProtectedError):
            camila.delete()

    def test_borrar_al_creador_o_a_quien_registro_deja_la_columna_vacia(self):
        encargada = self.crear_usuario("encargada")
        cita = self.crear_cita(creado_por=encargada)
        abono = self.crear_abono(self.crear_pago(cita), registrado_por=encargada)
        encargada.delete()
        cita.refresh_from_db()
        abono.refresh_from_db()
        self.assertIsNone(cita.creado_por)
        self.assertIsNone(abono.registrado_por)
