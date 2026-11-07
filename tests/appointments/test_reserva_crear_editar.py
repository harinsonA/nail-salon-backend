import json
from decimal import Decimal

from django.urls import reverse

from apps.appointments.models import Cita
from apps.payments.choices import EstadoDetallePago, MetodoPago, TipoDetallePago
from apps.payments.models import DetallePago, Pago
from apps.settings.preferences import (
    RESERVATION_AMOUNT,
    RESERVATION_DISCOUNTS_TOTAL,
    RESERVATION_ENABLED,
    RESERVATION_MODULE,
    RESERVATION_PAYMENT_METHOD,
)
from tests.appointments.test_crear_cita import FECHA, CitaBase


class ReservaBase(CitaBase):
    def setUp(self):
        super().setUp()
        RESERVATION_MODULE.set(True)
        self.configurar()

    def configurar(self, habilitada=True, monto=5000, descuenta=False, metodo=MetodoPago.EFECTIVO):
        RESERVATION_ENABLED.set(habilitada)
        RESERVATION_AMOUNT.set(monto)
        RESERVATION_DISCOUNTS_TOTAL.set(descuenta)
        RESERVATION_PAYMENT_METHOD.set(metodo)

    def reserva(self, activa=True, metodo=MetodoPago.EFECTIVO, referencia="", **extra):
        return json.dumps({"activa": activa, "metodo": metodo, "referencia": referencia, **extra})

    def abrir_crear(self, usuario=None):
        return self.navegador(usuario or self.encargada).get(self.url(), HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def filas(self, cita=None):
        filtro = {"pago__cita": cita} if cita else {}
        return list(DetallePago.objects.filter(**filtro).order_by("pk"))

    def cita_con_reserva(self, usuario=None, **datos):
        respuesta = self.crear(usuario=usuario, reservation=self.reserva(**datos))
        self.assertEqual(respuesta.status_code, 200)
        return Cita.objects.latest("pk")

    def url_editar(self, cita):
        return reverse("agenda_update_modal", args=[cita.pk])

    def abrir_editar(self, cita, usuario=None):
        return self.navegador(usuario or self.encargada).get(
            self.url_editar(cita), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def editar(self, cita, usuario=None, **datos):
        payload = {
            "client": self.cliente.pk,
            "assigned_to": cita.asignado_a_id,
            "date": FECHA,
            "time": "10:30",
            "services": json.dumps([{"detalle": cita.detalles.get().pk, "cantidad": 1, "descuento": 0}]),
            **datos,
        }
        return self.navegador(usuario or self.encargada).post(
            self.url_editar(cita), payload, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def configuracion(self, respuesta):
        return respuesta.context["appointment_form_config"]["reservation"]


class CrearCitaConReservaTests(ReservaBase):
    esquema = "crear_cita_reserva"
    dominio = "crear-cita-reserva.localhost"

    def test_con_el_modulo_apagado_no_aparece_ni_se_crea(self):
        RESERVATION_MODULE.set(False)
        respuesta = self.abrir_crear()
        self.assertNotContains(respuesta, "data-reservation-switch")
        self.assertIsNone(self.configuracion(respuesta))
        self.assertEqual(self.crear(reservation=self.reserva()).status_code, 200)
        self.assertFalse(Pago.objects.exists())

    def test_con_incluir_reserva_apagada_no_aparece_ni_se_crea(self):
        self.configurar(habilitada=False)
        self.assertIsNone(self.configuracion(self.abrir_crear()))
        self.assertEqual(self.crear(reservation=self.reserva()).status_code, 200)
        self.assertFalse(Pago.objects.exists())

    def test_el_modal_trae_la_seccion_con_el_switch_encendido(self):
        self.configurar(metodo=MetodoPago.TRANSFERENCIA)
        respuesta = self.abrir_crear()
        self.assertContains(respuesta, "Pagada")
        self.assertContains(respuesta, "No descuenta del total")
        self.assertContains(respuesta, 'id="id_reservation"')
        self.assertEqual(
            self.configuracion(respuesta),
            {
                "amount": 5000,
                "discounts": False,
                "modeLabel": "No descuenta del total",
                "on": True,
                "method": MetodoPago.TRANSFERENCIA,
                "reference": "",
                "date": "",
                "saved": False,
                "locked": False,
            },
        )

    def test_el_modal_indica_si_descuenta_del_total(self):
        self.configurar(descuenta=True)
        respuesta = self.abrir_crear()
        self.assertContains(respuesta, "Descuenta del total")
        self.assertTrue(self.configuracion(respuesta)["discounts"])

    def test_pagada_que_no_descuenta_crea_la_reserva_fuera_del_total(self):
        cita = self.cita_con_reserva(metodo=MetodoPago.TRANSFERENCIA, referencia=" TRX-9 ")
        pago = Pago.objects.get(cita=cita)
        (fila,) = self.filas(cita)
        self.assertEqual(fila.tipo_detalle, TipoDetallePago.RESERVA)
        self.assertEqual(fila.estado_detalle, EstadoDetallePago.VIGENTE)
        self.assertEqual(fila.monto_pago, Decimal("5000"))
        self.assertEqual(fila.metodo_pago, MetodoPago.TRANSFERENCIA)
        self.assertEqual(fila.referencia_pago, "TRX-9")
        self.assertEqual(fila.registrado_por, self.encargada)
        self.assertEqual(pago.monto_total_cita, Decimal("10000"))

    def test_pagada_que_descuenta_crea_la_reserva_descontable(self):
        self.configurar(descuenta=True)
        cita = self.cita_con_reserva()
        (fila,) = self.filas(cita)
        self.assertEqual(fila.tipo_detalle, TipoDetallePago.RESERVA_DESCONTABLE)
        self.assertEqual(Pago.objects.get(cita=cita).monto_total_cita, Decimal("10000"))

    def test_sin_pagar_no_crea_pago(self):
        respuesta = self.crear(reservation=self.reserva(activa=False))
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Pago.objects.exists())

    def test_el_monto_lo_pone_el_servidor(self):
        cita = self.cita_con_reserva(monto=1)
        self.assertEqual(self.filas(cita)[0].monto_pago, Decimal("5000"))

    def test_en_efectivo_se_descarta_la_referencia(self):
        cita = self.cita_con_reserva(referencia="TRX-1")
        self.assertIsNone(self.filas(cita)[0].referencia_pago)

    def test_un_metodo_o_una_referencia_invalidos_no_crean_nada(self):
        for reserva in (
            self.reserva(metodo="BITCOIN"),
            self.reserva(referencia="x" * 101, metodo=MetodoPago.TARJETA),
            json.dumps({"activa": "si"}),
            "{",
        ):
            with self.subTest(reserva=reserva):
                errores = self.errores(self.crear(reservation=reserva))
                self.assertEqual(errores["id_reservation"], "La reserva enviada no es válida.")
        self.assertFalse(Cita.objects.exists())

    def test_reserva_y_anticipos_van_en_un_solo_pago(self):
        anticipos = json.dumps([{"monto": 2000, "metodo": MetodoPago.EFECTIVO, "referencia": ""}])
        respuesta = self.crear(reservation=self.reserva(), advances=anticipos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Pago.objects.count(), 1)
        self.assertEqual(
            [fila.tipo_detalle for fila in self.filas()],
            [TipoDetallePago.RESERVA, TipoDetallePago.ANTICIPO],
        )

    def test_la_descontable_con_anticipos_no_supera_el_total(self):
        self.configurar(descuenta=True)
        anticipos = json.dumps([{"monto": 6000, "metodo": MetodoPago.EFECTIVO, "referencia": ""}])
        errores = self.errores(self.crear(reservation=self.reserva(), advances=anticipos))
        self.assertEqual(
            errores["id_advances"],
            "La reserva o los anticipos suman $11.000 y no pueden superar el total de los servicios ($10.000).",
        )
        self.assertFalse(Cita.objects.exists())

    def test_la_descontable_sola_no_supera_el_total(self):
        self.configurar(descuenta=True)
        servicios = [{"id": self.diseno.pk, "cantidad": 1, "descuento": 0}]
        errores = self.errores(self.crear(servicios=servicios, reservation=self.reserva()))
        self.assertEqual(
            errores["id_reservation"],
            "La reserva o los anticipos suman $5.000 y no pueden superar el total de los servicios ($3.000).",
        )

    def test_la_que_no_descuenta_no_cuenta_para_el_tope(self):
        servicios = [{"id": self.diseno.pk, "cantidad": 1, "descuento": 0}]
        anticipos = json.dumps([{"monto": 3000, "metodo": MetodoPago.EFECTIVO, "referencia": ""}])
        respuesta = self.crear(servicios=servicios, reservation=self.reserva(), advances=anticipos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(self.filas()), 2)

    def test_la_colaboradora_tambien_crea_con_reserva(self):
        cita = self.cita_con_reserva(usuario=self.colaboradora)
        self.assertEqual(self.filas(cita)[0].registrado_por, self.colaboradora)


class EditarCitaConReservaTests(ReservaBase):
    esquema = "editar_cita_reserva"
    dominio = "editar-cita-reserva.localhost"

    def test_la_reserva_guardada_conserva_sus_valores(self):
        cita = self.cita_con_reserva(metodo=MetodoPago.TRANSFERENCIA, referencia="TRX-1")
        self.configurar(monto=8000, descuenta=True, metodo=MetodoPago.TARJETA)
        respuesta = self.abrir_editar(cita)
        configuracion = self.configuracion(respuesta)
        self.assertEqual(configuracion["amount"], 5000)
        self.assertFalse(configuracion["discounts"])
        self.assertEqual(configuracion["modeLabel"], "No descuenta del total")
        self.assertTrue(configuracion["on"])
        self.assertTrue(configuracion["saved"])
        self.assertEqual(configuracion["method"], MetodoPago.TRANSFERENCIA)
        self.assertEqual(configuracion["reference"], "TRX-1")
        self.assertTrue(configuracion["date"])
        self.assertContains(respuesta, "Fecha")

    def test_la_reserva_guardada_aparece_aunque_se_apague_incluir_reserva(self):
        cita = self.cita_con_reserva()
        self.configurar(habilitada=False)
        self.assertTrue(self.configuracion(self.abrir_editar(cita))["saved"])

    def test_apagar_y_guardar_elimina_la_fila(self):
        self.configurar(descuenta=True)
        cita = self.cita_con_reserva()
        respuesta = self.editar(cita, reservation=self.reserva(activa=False))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.filas(cita), [])
        self.assertEqual(Pago.objects.get(cita=cita).monto_total_cita, Decimal("10000"))

    def test_sin_cambios_la_fila_no_se_toca(self):
        cita = self.cita_con_reserva()
        fila = self.filas(cita)[0]
        self.assertEqual(self.editar(cita, reservation=self.reserva()).status_code, 200)
        self.assertEqual(self.filas(cita)[0].modified, fila.modified)

    def test_la_encargada_cambia_metodo_y_referencia_pero_no_el_monto(self):
        cita = self.cita_con_reserva()
        self.configurar(monto=9000)
        reserva = self.reserva(metodo=MetodoPago.TRANSFERENCIA, referencia="TRX-2", monto=1)
        self.assertEqual(self.editar(cita, reservation=reserva).status_code, 200)
        (fila,) = self.filas(cita)
        self.assertEqual(fila.metodo_pago, MetodoPago.TRANSFERENCIA)
        self.assertEqual(fila.referencia_pago, "TRX-2")
        self.assertEqual(fila.monto_pago, Decimal("5000"))

    def test_la_colaboradora_ve_la_reserva_bloqueada(self):
        cita = self.cita_con_reserva(usuario=self.colaboradora)
        respuesta = self.abrir_editar(cita, usuario=self.colaboradora)
        self.assertTrue(self.configuracion(respuesta)["locked"])
        self.assertContains(respuesta, "Solo la propietaria o la encargada pueden cambiar o quitar")
        for reserva in (self.reserva(activa=False), self.reserva(metodo=MetodoPago.TARJETA)):
            with self.subTest(reserva=reserva):
                errores = self.errores(self.editar(cita, usuario=self.colaboradora, reservation=reserva))
                self.assertIn("Solo la propietaria o la encargada", errores["id_reservation"])
        self.assertEqual(self.editar(cita, usuario=self.colaboradora, reservation="").status_code, 200)
        self.assertEqual(len(self.filas(cita)), 1)

    def test_sin_reserva_el_switch_sale_apagado_y_usa_la_configuracion_actual(self):
        cita = self.cita_con_reserva(activa=False)
        self.configurar(monto=7000, descuenta=True, metodo=MetodoPago.TARJETA)
        configuracion = self.configuracion(self.abrir_editar(cita))
        self.assertFalse(configuracion["on"])
        self.assertFalse(configuracion["saved"])
        self.assertEqual(configuracion["amount"], 7000)
        self.assertEqual(configuracion["method"], MetodoPago.TARJETA)
        respuesta = self.editar(cita, reservation=self.reserva(metodo=MetodoPago.TARJETA))
        self.assertEqual(respuesta.status_code, 200)
        (fila,) = self.filas(cita)
        self.assertEqual(fila.tipo_detalle, TipoDetallePago.RESERVA_DESCONTABLE)
        self.assertEqual(fila.monto_pago, Decimal("7000"))

    def test_la_colaboradora_puede_agregar_una_reserva_nueva(self):
        cita = self.cita_con_reserva(usuario=self.colaboradora, activa=False)
        respuesta = self.editar(cita, usuario=self.colaboradora, reservation=self.reserva())
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(self.filas(cita)), 1)

    def test_sin_reserva_y_con_incluir_reserva_apagada_no_aparece(self):
        cita = self.cita_con_reserva(activa=False)
        self.configurar(habilitada=False)
        self.assertIsNone(self.configuracion(self.abrir_editar(cita)))
        self.assertEqual(self.editar(cita, reservation=self.reserva()).status_code, 200)
        self.assertFalse(Pago.objects.exists())

    def test_con_el_modulo_apagado_lo_guardado_no_se_toca(self):
        cita = self.cita_con_reserva()
        RESERVATION_MODULE.set(False)
        self.assertIsNone(self.configuracion(self.abrir_editar(cita)))
        self.assertEqual(self.editar(cita, reservation=self.reserva(activa=False)).status_code, 200)
        self.assertEqual(len(self.filas(cita)), 1)

    def test_una_reserva_retenida_definitiva_no_se_toca(self):
        cita = self.cita_con_reserva()
        anterior = self.filas(cita)[0]
        DetallePago.objects.filter(pk=anterior.pk).update(estado_detalle=EstadoDetallePago.RETENIDO_DEFINITIVO)
        self.configurar(monto=10000)
        configuracion = self.configuracion(self.abrir_editar(cita))
        self.assertFalse(configuracion["on"])
        self.assertFalse(configuracion["saved"])
        self.assertEqual(configuracion["amount"], 10000)
        self.assertEqual(self.editar(cita, reservation=self.reserva()).status_code, 200)
        primera, nueva = self.filas(cita)
        self.assertEqual(primera.estado_detalle, EstadoDetallePago.RETENIDO_DEFINITIVO)
        self.assertEqual(primera.monto_pago, Decimal("5000"))
        self.assertEqual(nueva.monto_pago, Decimal("10000"))
        self.assertEqual(nueva.estado_detalle, EstadoDetallePago.VIGENTE)

    def test_la_descontable_guardada_cuenta_para_el_tope(self):
        self.configurar(descuenta=True)
        cita = self.cita_con_reserva()
        anticipos = json.dumps([{"monto": 6000, "metodo": MetodoPago.EFECTIVO, "referencia": ""}])
        errores = self.errores(self.editar(cita, reservation=self.reserva(), advances=anticipos))
        self.assertIn("La reserva o los anticipos suman $11.000", errores["id_advances"])
        respuesta = self.editar(cita, reservation=self.reserva(activa=False), advances=anticipos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual([fila.tipo_detalle for fila in self.filas(cita)], [TipoDetallePago.ANTICIPO])
