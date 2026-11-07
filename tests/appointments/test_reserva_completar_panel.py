from decimal import Decimal

from django.urls import reverse

from apps.payments.choices import EstadoPago, MetodoPago, TipoDetallePago
from apps.payments.models import DetallePago, Pago
from tests.appointments.test_reserva_cancelar_restaurar import ReservaCicloBase


class ReservaPanelBase(ReservaCicloBase):
    def abrir_completar(self):
        return self.navegador().get(
            reverse("agenda_confirmation_modal", args=[self.cita.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def completar(self, pago_total=True):
        datos = {"payment_method": MetodoPago.EFECTIVO, "down_payment": "0"}
        if pago_total:
            datos["full_payment"] = "on"
        respuesta = self.navegador().post(
            reverse("agenda_confirmation_modal", args=[self.cita.pk]), datos, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(respuesta.status_code, 200)
        return Pago.objects.get(cita=self.cita)

    def abrir_detalle(self):
        return self.navegador().get(
            reverse("agenda_see_modal", args=[self.cita.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def pago_del_panel(self):
        return self.abrir_detalle().context["payment"]

    def filas_del_panel(self):
        return {fila["label"]: fila["value"] for fila in self.pago_del_panel()["rows"]}


class CompletarCitaConReservaTests(ReservaPanelBase):
    esquema = "completar_cita_reserva"
    dominio = "completar-cita-reserva.localhost"

    def test_la_que_no_descuenta_sale_en_verde_y_no_resta(self):
        self.con_reserva()
        respuesta = self.abrir_completar()
        self.assertEqual(
            respuesta.context["reservation"],
            {"label": "No descuenta del total", "amount": "$5.000", "discounts": False},
        )
        self.assertContains(respuesta, '<strong class="is-separate">$5.000</strong>', html=True)
        self.assertEqual(respuesta.context["advance"], "")
        self.assertEqual(respuesta.context["total_value"], 20000)
        pago = self.completar()
        self.assertEqual(pago.estado_pago, EstadoPago.COMPLETADO)
        abono = DetallePago.objects.get(tipo_detalle=TipoDetallePago.ABONO)
        self.assertEqual(abono.monto_pago, Decimal("20000"))

    def test_la_descontable_sale_en_rojo_y_resta(self):
        self.con_reserva(descuenta=True)
        respuesta = self.abrir_completar()
        self.assertEqual(
            respuesta.context["reservation"],
            {"label": "Descuenta del total", "amount": "-$5.000", "discounts": True},
        )
        self.assertContains(respuesta, '<strong class="is-discount">-$5.000</strong>', html=True)
        self.assertEqual(respuesta.context["total_value"], 15000)

    def test_sin_reserva_no_aparece_la_seccion(self):
        self.con_anticipos((3000, MetodoPago.EFECTIVO))
        respuesta = self.abrir_completar()
        self.assertIsNone(respuesta.context["reservation"])
        self.assertEqual(respuesta.context["advance"], "-$3.000")

    def test_una_reserva_retenida_definitiva_no_aparece(self):
        reserva = self.con_reserva(descuenta=True)[0]
        reserva.estado_detalle = "RETENIDO_DEFINITIVO"
        reserva.save()
        self.assertIsNone(self.abrir_completar().context["reservation"])

    def test_reserva_y_anticipo_salen_separados(self):
        self.con_reserva(descuenta=True, anticipos=[3000])
        respuesta = self.abrir_completar()
        self.assertEqual(respuesta.context["reservation"]["amount"], "-$5.000")
        self.assertEqual(respuesta.context["advance"], "-$3.000")
        self.assertEqual(respuesta.context["total_value"], 12000)

    def test_la_reserva_que_cubre_el_total_lo_dice(self):
        self.con_reserva(descuenta=True, monto=20000)
        respuesta = self.abrir_completar()
        self.assertContains(respuesta, "La reserva ya cubre el total de la cita.")
        self.assertEqual(self.completar().estado_pago, EstadoPago.COMPLETADO)

    def test_reserva_y_anticipo_que_cubren_el_total_lo_dicen(self):
        self.con_reserva(descuenta=True, anticipos=[15000])
        self.assertContains(self.abrir_completar(), "La reserva y el anticipo ya cubren el total de la cita.")

    def test_servicios_en_cero_con_reserva_que_no_descuenta(self):
        self.cita.detalles.update(precio_acordado=Decimal("0"))
        self.con_reserva()
        respuesta = self.abrir_completar()
        self.assertContains(respuesta, "La cita no tiene monto por cobrar.")
        self.assertNotContains(respuesta, "ya cubre el total")
        pago = self.completar()
        self.assertEqual(pago.estado_pago, EstadoPago.COMPLETADO)
        self.assertFalse(DetallePago.objects.filter(tipo_detalle=TipoDetallePago.ABONO).exists())


class PanelYDeudasConReservaTests(ReservaPanelBase):
    esquema = "panel_deudas_reserva"
    dominio = "panel-deudas-reserva.localhost"

    def test_pendiente_separa_reserva_y_anticipo(self):
        self.con_reserva(descuenta=True, anticipos=[3000])
        filas = self.filas_del_panel()
        self.assertEqual(
            (filas["Reserva"], filas["Anticipo"], filas["Restante por pagar"]),
            ("$5.000", "$3.000", "$12.000"),
        )

    def test_pendiente_con_la_que_no_descuenta_va_aparte(self):
        self.con_reserva()
        respuesta = self.abrir_detalle()
        filas = {fila["label"] for fila in respuesta.context["payment"]["rows"]}
        self.assertFalse({"Reserva", "Anticipo", "Restante por pagar"} & filas)
        self.assertContains(respuesta, "Reserva $5.000 · Pagada")

    def test_completada_la_que_no_descuenta_sale_de_la_lista(self):
        self.con_reserva()
        self.completar()
        respuesta = self.abrir_detalle()
        pago = respuesta.context["payment"]
        self.assertEqual([fila["kind"] for fila in pago["payments"]], ["Abono"])
        self.assertContains(respuesta, "Reserva $5.000 · Pagada")

    def test_completada_la_descontable_queda_en_la_lista(self):
        self.con_reserva(descuenta=True)
        self.completar()
        pago = self.pago_del_panel()
        self.assertEqual([fila["kind"] for fila in pago["payments"]], ["Reserva", "Abono"])
        self.assertEqual(pago["reservations"], [])

    def test_cancelada_muestra_la_reserva_retenida(self):
        self.con_reserva()
        self.cancelar([])
        self.assertContains(self.abrir_detalle(), "Reserva $5.000 · Retenida")
        self.assertEqual(self.filas_del_panel()["Reembolsado"], "$0")

    def test_cancelada_separa_reserva_y_anticipos_reembolsados(self):
        reserva, anticipo = self.con_reserva(descuenta=True, anticipos=[3000])
        self.cancelar([self.reembolso(reserva), self.reembolso(anticipo)])
        respuesta = self.abrir_detalle()
        filas = {fila["label"]: fila["value"] for fila in respuesta.context["payment"]["rows"]}
        self.assertEqual(
            filas,
            {
                "Estado": "Cita cancelada",
                "Retenido": "$0",
                "Reserva reembolsada": "$5.000",
                "Anticipos reembolsados": "$3.000",
            },
        )
        self.assertNotContains(respuesta, "· Reembolsada")

    def test_cancelada_con_la_reserva_que_no_descuenta_reembolsada(self):
        reserva = self.con_reserva()[0]
        self.cancelar([self.reembolso(reserva)])
        filas = self.filas_del_panel()
        self.assertEqual(filas["Reserva reembolsada"], "$5.000")
        self.assertNotIn("Anticipos reembolsados", filas)

    def test_deudas_muestra_la_reserva_aparte(self):
        self.con_reserva()
        pago = self.completar(pago_total=False)
        detalle = self.navegador().get(reverse("debt_detail_modal", args=[pago.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertContains(detalle, "Reserva $5.000 · Pagada")
        abono = self.navegador().get(reverse("add_payment_modal", args=[pago.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertContains(abono, "Reserva $5.000 · Pagada")
        self.assertEqual(abono.context["abonos"], [])
        self.assertEqual(abono.context["saldo"], "$20.000")

    def con_reserva_antigua(self, estado="RETENIDO_DEFINITIVO"):
        antigua = self.con_reserva(monto=3000)[0]
        antigua.estado_detalle = estado
        antigua.save()
        return antigua

    def test_pendiente_solo_muestra_la_reserva_pagada(self):
        self.con_reserva_antigua()
        self.con_reserva()
        respuesta = self.abrir_detalle()
        self.assertEqual(respuesta.context["payment"]["reservations"], [{"amount": "$5.000", "status": "Pagada"}])
        self.assertNotContains(respuesta, "Retenida")

    def test_completada_solo_muestra_la_reserva_pagada(self):
        self.con_reserva_antigua("DEVUELTO")
        self.con_reserva()
        pago = self.completar(pago_total=False)
        self.assertEqual(self.pago_del_panel()["reservations"], [{"amount": "$5.000", "status": "Pagada"}])
        abono = self.navegador().get(reverse("add_payment_modal", args=[pago.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(abono.context["reservas"], [{"amount": "$5.000", "status": "Pagada"}])

    def test_cancelada_no_muestra_las_retenidas_definitivas_anteriores(self):
        self.con_reserva_antigua()
        self.con_reserva()
        self.cancelar([])
        self.assertEqual(self.pago_del_panel()["reservations"], [{"amount": "$5.000", "status": "Retenida"}])
