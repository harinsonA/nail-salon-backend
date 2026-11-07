import json
from decimal import Decimal

from django.urls import reverse

from apps.appointments.models import Cita
from apps.payments.accounting import AppointmentLedger, AppointmentPaymentService, PaymentAccount
from apps.payments.accounting.constants import ReservationAction
from apps.payments.choices import EstadoDetallePago, EstadoPago, MetodoPago, TipoDetallePago
from apps.payments.models import DetallePago, Pago
from apps.settings.preferences import RESERVATION_ENABLED, RESERVATION_MODULE
from tests.appointments.test_cancelar_cita_anticipos import CitaConAnticiposBase


class ReservaCicloBase(CitaConAnticiposBase):
    def setUp(self):
        super().setUp()
        RESERVATION_MODULE.set(True)
        RESERVATION_ENABLED.set(True)

    def con_reserva(self, descuenta=False, monto=5000, anticipos=()):
        reserva = {
            "action": ReservationAction.CREATE,
            "amount": monto,
            "kind": TipoDetallePago.RESERVA_DESCONTABLE if descuenta else TipoDetallePago.RESERVA,
            "method": MetodoPago.TRANSFERENCIA,
            "reference": "",
        }
        filas = [{"amount": valor, "method": MetodoPago.EFECTIVO, "reference": ""} for valor in anticipos]
        AppointmentPaymentService(self.cita, self.encargada).save_payments(filas, reserva)
        return list(DetallePago.objects.filter(pago__cita=self.cita).order_by("pk"))

    def fila(self, fila):
        return DetallePago.objects.get(pk=fila.pk)

    def url_restaurar(self):
        return reverse("agenda_restore_modal", args=[self.cita.pk])

    def abrir_restaurar(self, usuario=None):
        return self.navegador(usuario).get(self.url_restaurar(), HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def restaurar(self, *filas, usuario=None, datos=None):
        if datos is None:
            datos = {"restored": json.dumps([fila.pk for fila in filas])}
        return self.navegador(usuario).post(self.url_restaurar(), datos, HTTP_X_REQUESTED_WITH="XMLHttpRequest")


class CancelarCitaConReservaTests(ReservaCicloBase):
    esquema = "cancelar_cita_reserva"
    dominio = "cancelar-cita-reserva.localhost"

    def test_el_panel_pregunta_por_la_reserva(self):
        reserva = self.con_reserva()[0]
        respuesta = self.abrir()
        self.assertContains(respuesta, "¿Qué hacemos con la reserva?")
        fila = respuesta.context["cancel_advances"]["config"]["rows"][0]
        self.assertEqual(fila["id"], reserva.pk)
        self.assertEqual((fila["kind"], fila["reservation"], fila["discounts"]), ("Reserva", True, False))

    def test_con_reserva_y_anticipos_pregunta_por_los_dos(self):
        self.con_reserva(descuenta=True, anticipos=[3000])
        respuesta = self.abrir()
        self.assertContains(respuesta, "¿Qué hacemos con la reserva y los anticipos?")
        filas = respuesta.context["cancel_advances"]["config"]["rows"]
        self.assertEqual([fila["kind"] for fila in filas], ["Reserva", "Anticipo"])
        self.assertEqual([fila["discounts"] for fila in filas], [True, True])

    def test_retener_la_reserva_la_deja_retenida(self):
        reserva = self.con_reserva()[0]
        self.assertEqual(self.cancelar([]).status_code, 200)
        self.assertEqual(self.fila(reserva).estado_detalle, EstadoDetallePago.RETENIDO)
        self.assertEqual(Pago.objects.get(cita=self.cita).estado_pago, EstadoPago.COMPLETADO)

    def test_reembolsar_la_reserva_crea_la_devolucion(self):
        reserva = self.con_reserva()[0]
        self.assertEqual(self.cancelar([self.reembolso(reserva, MetodoPago.TRANSFERENCIA, "op-1")]).status_code, 200)
        self.assertEqual(self.fila(reserva).estado_detalle, EstadoDetallePago.DEVUELTO)
        devolucion = DetallePago.objects.get(tipo_detalle=TipoDetallePago.DEVOLUCION)
        self.assertEqual((devolucion.detalle_devuelto_id, devolucion.monto_pago), (reserva.pk, Decimal("5000")))
        self.assertEqual(Pago.objects.get(cita=self.cita).estado_pago, EstadoPago.REEMBOLSADO)

    def test_retiene_la_reserva_y_reembolsa_el_anticipo(self):
        reserva, anticipo = self.con_reserva(descuenta=True, anticipos=[3000])
        self.assertEqual(self.cancelar([self.reembolso(anticipo)]).status_code, 200)
        self.assertEqual(self.fila(reserva).estado_detalle, EstadoDetallePago.RETENIDO)
        self.assertEqual(self.fila(anticipo).estado_detalle, EstadoDetallePago.DEVUELTO)

    def test_la_colaboradora_no_cancela_con_reserva_pagada(self):
        reserva = self.con_reserva()[0]
        aviso = "Esta cita tiene una reserva pagada. Solo la propietaria o la encargada pueden cancelarla."
        respuesta = self.abrir(self.colaboradora)
        self.assertTrue(respuesta.context["cancel_advances"]["locked"])
        self.assertContains(respuesta, aviso)
        respuesta = self.cancelar(usuario=self.colaboradora)
        self.assertEqual((respuesta.status_code, respuesta.json()["message"]), (403, aviso))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.PENDIENTE)
        self.assertEqual(self.fila(reserva).estado_detalle, EstadoDetallePago.VIGENTE)

    def test_con_el_modulo_apagado_igual_pregunta_por_la_reserva(self):
        reserva = self.con_reserva()[0]
        RESERVATION_MODULE.set(False)
        self.assertContains(self.abrir(), "¿Qué hacemos con la reserva?")
        self.assertEqual(self.cancelar([self.reembolso(reserva)]).status_code, 200)
        self.assertEqual(self.fila(reserva).estado_detalle, EstadoDetallePago.DEVUELTO)

    def test_una_reserva_ya_reembolsada_no_se_pregunta(self):
        reserva = self.con_reserva()[0]
        reserva.estado_detalle = EstadoDetallePago.DEVUELTO
        reserva.save()
        self.assertIsNone(self.abrir().context["cancel_advances"])


class RestaurarCitaConReservaTests(ReservaCicloBase):
    esquema = "restaurar_cita_reserva"
    dominio = "restaurar-cita-reserva.localhost"

    def test_el_panel_pregunta_por_la_reserva_retenida(self):
        reserva = self.con_reserva()[0]
        self.cancelar([])
        respuesta = self.abrir_restaurar()
        self.assertContains(respuesta, "¿Restauramos también la reserva retenida?")
        tarjeta = respuesta.context["restore_advances"]
        self.assertEqual(tarjeta["back_label"], "Reserva restaurada")
        self.assertEqual([fila["id"] for fila in tarjeta["config"]["rows"]], [reserva.pk])

    def test_con_reserva_y_anticipos_retenidos_pregunta_por_los_dos(self):
        self.con_reserva(descuenta=True, anticipos=[3000])
        self.cancelar([])
        respuesta = self.abrir_restaurar()
        self.assertContains(respuesta, "¿Restauramos también la reserva y los anticipos retenidos?")
        self.assertEqual(respuesta.context["restore_advances"]["back_label"], "Restaurado")

    def test_restaurar_la_reserva_la_vuelve_vigente(self):
        reserva = self.con_reserva()[0]
        self.cancelar([])
        self.assertEqual(self.restaurar(reserva).status_code, 200)
        self.assertEqual(self.fila(reserva).estado_detalle, EstadoDetallePago.VIGENTE)
        self.assertEqual(AppointmentLedger.for_appointment(self.cita).open_reservation().pk, reserva.pk)

    def test_no_restaurarla_la_deja_retenida_definitiva(self):
        reserva = self.con_reserva()[0]
        self.cancelar([])
        self.assertEqual(self.restaurar().status_code, 200)
        self.assertEqual(self.fila(reserva).estado_detalle, EstadoDetallePago.RETENIDO_DEFINITIVO)
        self.assertIsNone(AppointmentLedger.for_appointment(self.cita).open_reservation())

    def test_la_reserva_vuelve_con_el_modo_con_que_se_cobro(self):
        descontable = self.con_reserva(descuenta=True)[0]
        self.cancelar([])
        RESERVATION_ENABLED.set(False)
        self.assertEqual(self.restaurar(descontable).status_code, 200)
        fila = self.fila(descontable)
        self.assertEqual((fila.tipo_detalle, fila.estado_detalle), (TipoDetallePago.RESERVA_DESCONTABLE, EstadoDetallePago.VIGENTE))
        self.assertEqual(PaymentAccount(Pago.objects.get(cita=self.cita)).credit(), Decimal("5000"))

    def test_la_que_no_descuenta_restaurada_no_cambia_el_restante(self):
        reserva = self.con_reserva()[0]
        self.cancelar([])
        self.assertEqual(self.restaurar(reserva).status_code, 200)
        self.assertEqual(PaymentAccount(Pago.objects.get(cita=self.cita)).credit(), Decimal("0"))

    def test_una_reserva_reembolsada_no_se_pregunta_ni_vuelve(self):
        reserva = self.con_reserva()[0]
        self.cancelar([self.reembolso(reserva)])
        self.assertIsNone(self.abrir_restaurar().context["restore_advances"])
        self.assertEqual(self.restaurar(reserva).status_code, 400)
        self.assertEqual(self.restaurar().status_code, 200)
        self.assertEqual(self.fila(reserva).estado_detalle, EstadoDetallePago.DEVUELTO)

    def test_la_colaboradora_no_restaura_con_reserva_retenida(self):
        reserva = self.con_reserva()[0]
        self.cancelar([])
        aviso = "Esta cita tiene una reserva retenida. Solo la propietaria o la encargada pueden restaurarla."
        self.assertContains(self.abrir_restaurar(self.colaboradora), aviso)
        respuesta = self.restaurar(reserva, usuario=self.colaboradora)
        self.assertEqual((respuesta.status_code, respuesta.json()["message"]), (403, aviso))
        self.assertEqual(self.fila(reserva).estado_detalle, EstadoDetallePago.RETENIDO)

    def test_con_el_modulo_apagado_igual_pregunta_por_la_reserva(self):
        reserva = self.con_reserva()[0]
        self.cancelar([])
        RESERVATION_MODULE.set(False)
        self.assertContains(self.abrir_restaurar(), "¿Restauramos también la reserva retenida?")
        self.assertEqual(self.restaurar(reserva).status_code, 200)
        self.assertEqual(self.fila(reserva).estado_detalle, EstadoDetallePago.VIGENTE)

    def test_rechaza_una_fila_que_no_es_retenida(self):
        reserva = self.con_reserva()[0]
        self.cancelar([])
        respuesta = self.restaurar(datos={"restored": json.dumps([reserva.pk + 999])})
        self.assertEqual((respuesta.status_code, respuesta.json()["message"]), (400, "Los pagos a restaurar no son válidos."))
        self.assertEqual(self.fila(reserva).estado_detalle, EstadoDetallePago.RETENIDO)
