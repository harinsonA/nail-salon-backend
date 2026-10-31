import json
from decimal import Decimal

from django.urls import reverse

from apps.appointments.models import Cita
from apps.payments.choices import EstadoDetallePago, EstadoPago, MetodoPago
from apps.payments.models import DetallePago, Pago
from apps.payments.accounting import AppointmentPaymentService, PaymentExpressions
from apps.settings.models import Preference
from apps.settings.preferences import Scope
from tests.appointments.test_cancelar_cita_anticipos import CitaConAnticiposBase


class RestaurarCitaConAnticiposTests(CitaConAnticiposBase):
    esquema = "restaurar_cita_anticipos"
    dominio = "restaurar-cita-anticipos.localhost"

    def setUp(self):
        super().setUp()
        Preference.objects.update_or_create(
            scope=Scope.NEGOCIO, scope_id="", key="advance_module", defaults={"value": True}
        )

    def url_restaurar(self):
        return reverse("agenda_restore_modal", args=[self.cita.pk])

    def abrir_restaurar(self, usuario=None):
        return self.navegador(usuario).get(self.url_restaurar(), HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def restaurar(self, *filas, usuario=None, datos=None):
        if datos is None:
            datos = {"restored": json.dumps([fila.pk for fila in filas])}
        return self.navegador(usuario).post(self.url_restaurar(), datos, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def restaurada(self, *filas):
        self.assertEqual(self.restaurar(*filas).status_code, 200)
        self.cita.refresh_from_db()
        return Pago.objects.get(cita=self.cita)

    def anticipos_en_editar(self):
        respuesta = self.navegador().get(
            reverse("agenda_update_modal", args=[self.cita.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        return [fila["id"] for fila in respuesta.context["appointment_form_config"]["advances"]["rows"]]

    def abrir_completar(self):
        return self.navegador().get(
            reverse("agenda_confirmation_modal", args=[self.cita.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def completar(self):
        return self.navegador().post(
            reverse("agenda_confirmation_modal", args=[self.cita.pk]),
            {"payment_method": MetodoPago.EFECTIVO, "remaining_payment": "0", "full_payment": "on"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def agregar_anticipo(self, monto):
        cambio = {"row": None, "remove": False, "amount": monto, "method": MetodoPago.EFECTIVO, "reference": ""}
        AppointmentPaymentService(self.cita, self.encargada).sync_advances([cambio])
        return DetallePago.objects.filter(pago__cita=self.cita).latest("pk")

    def test_sin_anticipos_restaura_como_hoy(self):
        self.cancelar()
        respuesta = self.abrir_restaurar()
        self.assertNotContains(respuesta, "¿Restauramos también los anticipos retenidos?")
        self.assertIsNone(respuesta.context["restore_advances"])
        self.assertEqual(self.navegador().post(self.url_restaurar(), HTTP_X_REQUESTED_WITH="XMLHttpRequest").status_code, 200)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.PENDIENTE)
        self.assertFalse(Pago.objects.exists())

    def test_el_panel_lista_solo_los_retenidos(self):
        primera, segunda = self.con_anticipos((6000, MetodoPago.TARJETA), (4000, MetodoPago.TRANSFERENCIA))
        self.cancelar([self.reembolso(segunda, MetodoPago.TRANSFERENCIA)])
        respuesta = self.abrir_restaurar()
        self.assertContains(respuesta, "¿Restauramos también los anticipos retenidos?")
        self.assertContains(respuesta, 'name="restored"')
        decision = respuesta.context["restore_advances"]
        self.assertFalse(decision["locked"])
        self.assertEqual([fila["id"] for fila in decision["config"]["rows"]], [primera.pk])
        self.assertEqual((decision["config"]["servicesTotal"], decision["config"]["prepaid"]), (20000, 0))

    def test_solo_reembolsado_no_muestra_la_tarjeta(self):
        fila = self.con_anticipos((5000, MetodoPago.EFECTIVO))[0]
        self.cancelar([self.reembolso(fila)])
        self.assertIsNone(self.abrir_restaurar().context["restore_advances"])
        pago = self.restaurada()
        self.assertEqual((pago.estado_pago, pago.monto_total_cita), (EstadoPago.PENDIENTE, Decimal("20000")))

    def test_sin_restaurar_el_retenido_pasa_a_definitivo(self):
        self.con_anticipos((7000, MetodoPago.EFECTIVO))
        self.cancelar([])
        pago = self.restaurada()
        self.assertEqual(self.estados(), [EstadoDetallePago.RETENIDO_DEFINITIVO])
        self.assertEqual(
            (pago.estado_pago, pago.fecha_pago_completado, pago.monto_total_cita),
            (EstadoPago.PENDIENTE, None, Decimal("27000")),
        )
        self.assertEqual(self.anticipos_en_editar(), [])
        configuracion = self.abrir_completar().context["complete_config"]
        self.assertEqual((configuracion["total"], configuracion["prepaid"]), (20000, 0))
        self.assertEqual(self.completar().status_code, 200)
        pago.refresh_from_db()
        self.assertEqual((pago.estado_pago, pago.monto_total_cita), (EstadoPago.COMPLETADO, Decimal("27000")))
        self.assertEqual(DetallePago.objects.aggregate(total=PaymentExpressions.net_paid())["total"], Decimal("27000"))

    def test_restaurar_el_anticipo_lo_deja_vigente_y_descuenta(self):
        primera, segunda = self.con_anticipos((6000, MetodoPago.TARJETA), (3000, MetodoPago.EFECTIVO))
        self.cancelar([])
        pago = self.restaurada(primera)
        self.assertEqual(self.estados(), [EstadoDetallePago.VIGENTE, EstadoDetallePago.RETENIDO_DEFINITIVO])
        self.assertEqual(pago.monto_total_cita, Decimal("23000"))
        self.assertEqual(self.anticipos_en_editar(), [primera.pk])
        respuesta = self.navegador().get(
            reverse("agenda_see_modal", args=[self.cita.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        filas = {fila["label"]: fila["value"] for fila in respuesta.context["payment"]["rows"]}
        self.assertEqual((filas["Anticipo"], filas["Restante por pagar"]), ("$6.000", "$14.000"))
        configuracion = self.abrir_completar().context["complete_config"]
        self.assertEqual((configuracion["total"], configuracion["prepaid"]), (14000, 6000))
        self.assertEqual(self.completar().status_code, 200)
        pago.refresh_from_db()
        self.assertEqual((pago.estado_pago, pago.monto_total_cita), (EstadoPago.COMPLETADO, Decimal("23000")))

    def test_lo_reembolsado_no_vuelve(self):
        fila = self.con_anticipos((5000, MetodoPago.TRANSFERENCIA))[0]
        self.cancelar([self.reembolso(fila, MetodoPago.TRANSFERENCIA)])
        self.restaurada()
        self.assertEqual(self.estados(), [EstadoDetallePago.DEVUELTO])
        self.assertEqual(self.anticipos_en_editar(), [])
        self.assertEqual(self.abrir_completar().context["complete_config"]["total"], 20000)

    def test_el_definitivo_no_se_vuelve_a_preguntar(self):
        vieja = self.con_anticipos((7000, MetodoPago.EFECTIVO))[0]
        self.cancelar([])
        self.restaurada()
        nueva = self.agregar_anticipo(3000)
        self.cancelar([])
        self.assertEqual(self.estados(), [EstadoDetallePago.RETENIDO_DEFINITIVO, EstadoDetallePago.RETENIDO])
        decision = self.abrir_restaurar().context["restore_advances"]
        self.assertEqual([fila["id"] for fila in decision["config"]["rows"]], [nueva.pk])
        self.assertEqual(self.restaurar(vieja).status_code, 400)
        detalle = self.navegador().get(
            reverse("agenda_see_modal", args=[self.cita.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        filas = {fila["label"]: fila["value"] for fila in detalle.context["payment"]["rows"]}
        self.assertEqual(filas["Retenido"], "$10.000")

    def test_volver_a_cancelar_un_anticipo_restaurado_permite_reembolsarlo(self):
        fila = self.con_anticipos((7000, MetodoPago.EFECTIVO))[0]
        self.cancelar([])
        self.restaurada(fila)
        self.assertEqual(self.cancelar([self.reembolso(fila)]).status_code, 200)
        self.assertEqual(self.estados(), [EstadoDetallePago.DEVUELTO])
        pago = Pago.objects.get()
        self.assertEqual((pago.estado_pago, pago.monto_total_cita), (EstadoPago.REEMBOLSADO, Decimal("0")))

    def test_rechaza_datos_mal_formados_sin_restaurar(self):
        fila = self.con_anticipos((6000, MetodoPago.EFECTIVO))[0]
        self.cancelar([])
        casos = ["no es json", json.dumps({"id": fila.pk}), json.dumps(["1"]), json.dumps([True]), json.dumps([fila.pk, fila.pk]), json.dumps([fila.pk + 999])]
        for restaurados in casos:
            with self.subTest(restaurados=restaurados):
                respuesta = self.restaurar(datos={"restored": restaurados})
                self.assertEqual(respuesta.status_code, 400)
                self.assertEqual(respuesta.json()["message"], "Los anticipos a restaurar no son válidos.")
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.CANCELADA)
        self.assertEqual(self.estados(), [EstadoDetallePago.RETENIDO])

    def test_la_colaboradora_no_restaura_una_cita_con_retenidos(self):
        self.con_anticipos((6000, MetodoPago.EFECTIVO))
        self.cancelar([])
        respuesta = self.abrir_restaurar(self.colaboradora)
        self.assertTrue(respuesta.context["restore_advances"]["locked"])
        self.assertContains(respuesta, "Solo la propietaria o la encargada pueden restaurarla.")
        self.assertNotContains(respuesta, 'name="restored"')
        self.assertEqual(self.restaurar(usuario=self.colaboradora).status_code, 403)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.CANCELADA)
        self.assertEqual(self.estados(), [EstadoDetallePago.RETENIDO])

    def test_la_colaboradora_restaura_si_todo_se_reembolso(self):
        fila = self.con_anticipos((6000, MetodoPago.EFECTIVO))[0]
        self.cancelar([self.reembolso(fila)])
        self.assertEqual(self.restaurar(usuario=self.colaboradora).status_code, 200)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.PENDIENTE)

    def test_los_cambios_de_estado_quedan_en_el_historial(self):
        fila = self.con_anticipos((6000, MetodoPago.EFECTIVO))[0]
        self.cancelar([])
        self.restaurada()
        self.assertEqual(
            list(fila.history.order_by("history_date").values_list("estado_detalle", flat=True)),
            [EstadoDetallePago.VIGENTE, EstadoDetallePago.RETENIDO, EstadoDetallePago.RETENIDO_DEFINITIVO],
        )
