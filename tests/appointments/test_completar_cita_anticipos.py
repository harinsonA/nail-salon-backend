from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.appointments.models import Cita, DetalleCita
from apps.clients.models import Cliente
from apps.payments.choices import EstadoPago, MetodoPago, TipoDetallePago
from apps.payments.models import Pago
from apps.payments.accounting import AppointmentPaymentService, PaymentAccount
from apps.profiles.models import Perfil
from apps.services.models import Categoria, Servicio
from tests.base import NegocioTestCase

User = get_user_model()


class CompletarCitaConAnticipoTests(NegocioTestCase):
    esquema = "completar_cita_anticipo"
    dominio = "completar-cita-anticipo.localhost"

    def setUp(self):
        super().setUp()
        self.encargada = User.objects.create_user(
            username="ana", email="ana@correo.cl", password="x", first_name="Ana", last_name="Pérez"
        )
        Perfil.objects.filter(user=self.encargada).update(rol=Perfil.Rol.ENCARGADO, debe_cambiar_clave=False)
        self.encargada = User.objects.get(pk=self.encargada.pk)
        categoria = Categoria.objects.create(nombre="Manos")
        servicio = Servicio.objects.create(nombre="Manicure", precio=Decimal("10000"), categoria=categoria)
        self.cliente = Cliente.objects.create(nombre="Clienta")
        self.cita = Cita.objects.create(
            cliente=self.cliente,
            fecha_agenda=date(2026, 10, 20),
            hora_agenda=time(10, 0),
        )
        self.detalle = DetalleCita.objects.create(
            cita=self.cita, servicio=servicio, precio_acordado=Decimal("10000")
        )

    def con_anticipo(self, *montos):
        anticipos = [{"amount": monto, "method": MetodoPago.EFECTIVO, "reference": ""} for monto in montos]
        return AppointmentPaymentService(self.cita, self.encargada).register_advances(anticipos)

    def navegador(self):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(self.encargada)
        return navegador

    def url(self):
        return reverse("agenda_confirmation_modal", args=[self.cita.pk])

    def abrir(self):
        return self.navegador().get(self.url(), HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def completar(self, **datos):
        return self.navegador().post(
            self.url(),
            {"payment_method": MetodoPago.EFECTIVO, "remaining_payment": "0", **datos},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def pago(self):
        return Pago.objects.get(cita=self.cita)

    def test_el_modal_cobra_solo_el_saldo(self):
        self.con_anticipo(4000)
        respuesta = self.abrir()
        self.assertEqual(respuesta.context["total_value"], 6000)
        self.assertEqual(
            respuesta.context["complete_config"],
            {"total": 6000, "prepaid": 4000, "servicesTotal": 10000, "fullLabel": "Paga el saldo ahora"},
        )
        self.assertContains(respuesta, "Saldo a pagar")
        self.assertContains(respuesta, "Paga el saldo ahora")
        self.assertContains(respuesta, "-$4.000")
        self.assertContains(respuesta, "$6.000")

    def test_pagar_el_saldo_usa_el_mismo_pago_y_lo_deja_completado(self):
        self.con_anticipo(4000)
        respuesta = self.completar(full_payment="on")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Pago.objects.count(), 1)
        pago = self.pago()
        filas = list(pago.detalles_pago.order_by("pk").values_list("tipo_detalle", "monto_pago"))
        self.assertEqual(
            filas, [(TipoDetallePago.ANTICIPO, Decimal("4000")), (TipoDetallePago.ABONO, Decimal("6000"))]
        )
        self.assertEqual((pago.estado_pago, pago.monto_total_cita), (EstadoPago.COMPLETADO, Decimal("10000")))
        self.assertIsNotNone(pago.fecha_pago_completado)
        self.assertEqual((pago.atendido_por, pago.atendido_por_nombre), (self.encargada, "Ana Pérez"))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.COMPLETADA)

    def test_un_abono_parcial_deja_el_resto_como_deuda(self):
        self.con_anticipo(4000)
        respuesta = self.completar(down_payment="2000")
        self.assertEqual(respuesta.status_code, 200)
        pago = self.pago()
        self.assertEqual(pago.estado_pago, EstadoPago.PENDIENTE)
        self.assertEqual(PaymentAccount(pago).balance(), Decimal("4000"))

    def test_sin_pagar_hoy_queda_debiendo_el_saldo(self):
        self.con_anticipo(4000)
        respuesta = self.completar(down_payment="0")
        self.assertEqual(respuesta.status_code, 200)
        pago = self.pago()
        self.assertEqual(pago.detalles_pago.count(), 1)
        self.assertEqual(PaymentAccount(pago).balance(), Decimal("6000"))

    def test_un_abono_igual_al_saldo_pide_activar_pagar_el_saldo(self):
        self.con_anticipo(4000)
        respuesta = self.completar(down_payment="6000")
        self.assertEqual(respuesta.status_code, 400)
        errores = {error["id_element"]: error["error"] for error in respuesta.json()["errors"]}
        self.assertEqual(errores["id_down_payment"], 'Si paga $6.000 o más, activa "Paga el saldo ahora".')
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.PENDIENTE)
        self.assertEqual(self.pago().detalles_pago.count(), 1)

    def test_si_el_anticipo_cubre_todo_completa_sin_cobrar(self):
        self.con_anticipo(6000, 4000)
        respuesta = self.abrir()
        self.assertEqual(respuesta.context["total_value"], 0)
        self.assertContains(respuesta, "El anticipo ya cubre el total de la cita.")
        respuesta = self.completar(down_payment="")
        self.assertEqual(respuesta.status_code, 200)
        pago = self.pago()
        self.assertEqual(pago.detalles_pago.count(), 2)
        self.assertEqual(pago.estado_pago, EstadoPago.COMPLETADO)

    def test_completar_refresca_las_fotos_del_pago(self):
        self.con_anticipo(4000)
        self.cliente.apellido = "Nueva"
        self.cliente.save()
        self.completar(full_payment="on")
        self.assertEqual(self.pago().cliente_nombre, "Clienta Nueva")

    def test_si_lo_pagado_supera_los_servicios_pide_editar_la_cita(self):
        self.con_anticipo(8000)
        DetalleCita.objects.filter(pk=self.detalle.pk).update(precio_acordado=Decimal("5000"))
        respuesta = self.completar(full_payment="on")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("supera el total de los servicios ($5.000)", respuesta.content.decode())
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.PENDIENTE)
