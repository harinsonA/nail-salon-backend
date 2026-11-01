import json
from decimal import Decimal

from django.urls import reverse

from apps.appointments.models import Cita
from apps.payments.choices import EstadoDetallePago, EstadoPago, MetodoPago, TipoDetallePago
from apps.payments.models import DetallePago, Pago
from tests.appointments.test_crear_cita import CitaBase


class CrearCitaConAnticiposTests(CitaBase):
    esquema = "crear_cita_anticipos"
    dominio = "crear-cita-anticipos.localhost"

    def abrir(self, usuario=None):
        return self.navegador(usuario or self.encargada).get(self.url(), HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def con_anticipos(self, anticipos, usuario=None, servicios=None):
        return self.crear(usuario=usuario, servicios=servicios, advances=json.dumps(anticipos))

    def anticipo(self, monto, metodo=MetodoPago.EFECTIVO, referencia=""):
        return {"monto": monto, "metodo": metodo, "referencia": referencia}

    def assertNoSeCrea(self, respuesta, mensaje):
        self.assertIn(mensaje, self.errores(respuesta)["id_advances"])
        self.assertFalse(Cita.objects.exists())
        self.assertFalse(Pago.objects.exists())

    def test_el_modal_muestra_la_tarjeta_de_anticipo(self):
        respuesta = self.abrir()
        self.assertContains(respuesta, "Incluye anticipo")
        self.assertContains(respuesta, "Añadir anticipo")
        self.assertContains(respuesta, 'id="id_advances"')
        configuracion = respuesta.context["appointment_form_config"]["advances"]
        self.assertEqual(configuracion["cash"], MetodoPago.EFECTIVO)

    def test_sin_anticipos_no_crea_pago(self):
        respuesta = self.crear()
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Pago.objects.exists())

    def test_un_anticipo_crea_el_pago_de_la_cita_y_su_fila(self):
        respuesta = self.con_anticipos([self.anticipo(4000)])
        self.assertEqual(respuesta.status_code, 200)
        cita = Cita.objects.get()
        pago = cita.pago
        self.assertEqual(pago.monto_total_cita, Decimal("10000"))
        self.assertEqual(pago.estado_pago, EstadoPago.PENDIENTE)
        self.assertEqual(pago.cliente_nombre, "Paula Herrera")
        self.assertEqual(pago.fecha_cita.date().isoformat(), "2026-11-02")
        self.assertIsNone(pago.atendido_por)
        fila = pago.detalles_pago.get()
        self.assertEqual(fila.monto_pago, Decimal("4000"))
        self.assertEqual(fila.metodo_pago, MetodoPago.EFECTIVO)
        self.assertEqual((fila.tipo_detalle, fila.estado_detalle), (TipoDetallePago.ANTICIPO, EstadoDetallePago.VIGENTE))
        self.assertEqual(fila.registrado_por, self.encargada)
        self.assertEqual(fila.history.count(), 1)

    def test_varios_anticipos_van_en_el_mismo_pago_con_su_referencia(self):
        respuesta = self.con_anticipos(
            [
                self.anticipo(5000, referencia="no se guarda"),
                self.anticipo(3000, MetodoPago.TRANSFERENCIA, "  TRX-48213  "),
            ]
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Pago.objects.count(), 1)
        filas = list(DetallePago.objects.order_by("monto_pago").values_list("monto_pago", "metodo_pago", "referencia_pago"))
        self.assertEqual(
            filas,
            [
                (Decimal("3000"), MetodoPago.TRANSFERENCIA, "TRX-48213"),
                (Decimal("5000"), MetodoPago.EFECTIVO, None),
            ],
        )

    def test_el_anticipo_puede_cubrir_el_total_con_descuento(self):
        servicios = [{"id": self.manicure.pk, "cantidad": 1, "descuento": 1000}]
        respuesta = self.con_anticipos([self.anticipo(9000)], servicios=servicios)
        self.assertEqual(respuesta.status_code, 200)
        pago = Pago.objects.get()
        self.assertEqual((pago.monto_total_cita, pago.descuento_total), (Decimal("9000"), Decimal("1000")))

    def test_los_anticipos_no_pueden_superar_el_total_de_los_servicios(self):
        respuesta = self.con_anticipos([self.anticipo(6000), self.anticipo(4001, MetodoPago.TARJETA)])
        self.assertNoSeCrea(respuesta, "Los anticipos suman $10.001 y no pueden superar el total de los servicios ($10.000).")

    def test_el_monto_no_puede_ir_vacio_ni_en_cero(self):
        for monto in (0, None, ""):
            with self.subTest(monto=monto):
                self.assertNoSeCrea(self.con_anticipos([self.anticipo(monto)]), "Ingresa el monto de cada anticipo.")

    def test_rechaza_anticipos_mal_formados(self):
        casos = [
            "no es json",
            json.dumps({"monto": 1000}),
            json.dumps(["texto"]),
            json.dumps([self.anticipo(-500)]),
            json.dumps([self.anticipo(1000.5)]),
            json.dumps([self.anticipo("1000")]),
            json.dumps([self.anticipo(1000, "CRIPTOMONEDA")]),
            json.dumps([self.anticipo(1000, MetodoPago.TARJETA, "x" * 101)]),
        ]
        for anticipos in casos:
            with self.subTest(anticipos=anticipos):
                respuesta = self.crear(advances=anticipos)
                self.assertNoSeCrea(respuesta, "Los anticipos enviados no son válidos.")

    def test_la_colaboradora_tambien_registra_anticipos(self):
        respuesta = self.con_anticipos([self.anticipo(2000)], usuario=self.colaboradora)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(DetallePago.objects.get().registrado_por, self.colaboradora)

    def test_el_detalle_de_la_cita_pendiente_muestra_el_anticipo(self):
        self.con_anticipos([self.anticipo(4000)])
        cita = Cita.objects.get()
        respuesta = self.navegador(self.encargada).get(
            reverse("agenda_see_modal", args=[cita.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        filas = {fila["label"]: fila["value"] for fila in respuesta.context["payment"]["rows"]}
        self.assertEqual(filas["Monto estimado"], "$10.000")
        self.assertEqual(filas["Anticipo"], "$4.000")
        self.assertEqual(filas["Restante por pagar"], "$6.000")
