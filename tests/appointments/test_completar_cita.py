from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.appointments.models import Cita, DetalleCita
from apps.clients.models import Cliente
from apps.payments.models import Pago
from apps.profiles.models import Perfil
from apps.services.models import Categoria, Servicio
from tests.base import NegocioTestCase

User = get_user_model()


class CompletarCitaTests(NegocioTestCase):
    esquema = "completar_cita"
    dominio = "completar-cita.localhost"

    def setUp(self):
        super().setUp()
        self.encargada = User.objects.create_user(username="ana", email="ana@correo.cl", password="x")
        Perfil.objects.filter(user=self.encargada).update(rol=Perfil.Rol.ENCARGADO, debe_cambiar_clave=False)
        categoria = Categoria.objects.create(nombre="Manos")
        servicio = Servicio.objects.create(nombre="Manicure", precio=Decimal("10000"), categoria=categoria)
        self.cita = Cita.objects.create(
            cliente=Cliente.objects.create(nombre="Clienta"),
            fecha_agenda=date(2026, 10, 20),
            hora_agenda=time(10, 0),
        )
        DetalleCita.objects.create(cita=self.cita, servicio=servicio, precio_acordado=Decimal("10000"))

    def completar(self, **datos):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(self.encargada)
        return navegador.post(
            reverse("agenda_confirmation_modal", args=[self.cita.pk]),
            {"payment_method": "EFECTIVO", "remaining_payment": "0", **datos},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def assertNoSeCompleta(self, respuesta):
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("down_payment", str(respuesta.json()["errors"]))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.PENDIENTE)
        self.assertFalse(Pago.objects.filter(cita=self.cita).exists())

    def test_sin_pago_completo_el_monto_abonado_vacio_es_requerido(self):
        respuesta = self.completar(down_payment="")
        self.assertNoSeCompleta(respuesta)
        self.assertIn("El monto abonado es requerido.", str(respuesta.json()["errors"]))

    def test_sin_pago_completo_el_monto_abonado_no_puede_ser_negativo(self):
        self.assertNoSeCompleta(self.completar(down_payment="-500"))

    def test_sin_pago_completo_acepta_monto_abonado_cero(self):
        respuesta = self.completar(down_payment="0")
        self.assertEqual(respuesta.status_code, 200)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.COMPLETADA)
        self.assertFalse(self.cita.pago.detalles_pago.exists())

    def test_con_pago_completo_el_monto_abonado_vacio_no_importa(self):
        respuesta = self.completar(full_payment="on", down_payment="")
        self.assertEqual(respuesta.status_code, 200)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.COMPLETADA)
        self.assertEqual(self.cita.pago.detalles_pago.get().monto_pago, Decimal("10000"))
