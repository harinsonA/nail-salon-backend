import json
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Cita
from apps.payments.choices import EstadoDetallePago, MetodoPago, TipoDetallePago
from apps.payments.models import DetallePago, Pago
from apps.settings.models import Preference
from apps.settings.preferences import Scope
from tests.appointments.test_crear_cita import FECHA, CitaBase


class EditarCitaConAnticiposTests(CitaBase):
    esquema = "editar_cita_anticipos"
    dominio = "editar-cita-anticipos.localhost"

    def encender(self):
        Preference.objects.update_or_create(
            scope=Scope.NEGOCIO, scope_id="", key="advance_module", defaults={"value": True}
        )

    def anticipo(self, monto, metodo=MetodoPago.EFECTIVO, referencia=""):
        return {"monto": monto, "metodo": metodo, "referencia": referencia}

    def cita_con(self, anticipos, asignada=None):
        self.encender()
        datos = {"advances": json.dumps(anticipos)}
        if asignada:
            datos["assigned_to"] = asignada.pk
        respuesta = self.crear(**datos)
        self.assertEqual(respuesta.status_code, 200)
        return Cita.objects.latest("pk")

    def filas(self, cita):
        return list(DetallePago.objects.filter(pago__cita=cita).order_by("pk"))

    def url_editar(self, cita):
        return reverse("agenda_update_modal", args=[cita.pk])

    def abrir(self, cita, usuario=None):
        return self.navegador(usuario or self.encargada).get(self.url_editar(cita), HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def editar(self, cita, anticipos=None, usuario=None, descuento=0, **datos):
        payload = {
            "client": self.cliente.pk,
            "assigned_to": cita.asignado_a_id,
            "date": FECHA,
            "time": "10:30",
            "services": json.dumps([{"detalle": cita.detalles.get().pk, "cantidad": 1, "descuento": descuento}]),
            **datos,
        }
        if anticipos is not None:
            payload["advances"] = json.dumps(anticipos)
        return self.navegador(usuario or self.encargada).post(
            self.url_editar(cita), payload, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def test_sin_interruptor_editar_no_muestra_la_tarjeta(self):
        self.crear()
        respuesta = self.abrir(Cita.objects.get())
        self.assertNotContains(respuesta, "Incluye anticipo")

    def test_el_modal_de_editar_trae_los_anticipos_guardados(self):
        cita = self.cita_con([self.anticipo(4000), self.anticipo(2000, MetodoPago.TRANSFERENCIA, "TRX-1")])
        respuesta = self.abrir(cita)
        self.assertContains(respuesta, "Incluye anticipo")
        configuracion = respuesta.context["appointment_form_config"]["advances"]
        primera, segunda = self.filas(cita)
        self.assertTrue(configuracion["canChangeSaved"])
        self.assertEqual(
            configuracion["rows"],
            [
                {
                    "id": primera.pk,
                    "amount": 4000,
                    "method": MetodoPago.EFECTIVO,
                    "reference": "",
                    "date": configuracion["rows"][0]["date"],
                },
                {
                    "id": segunda.pk,
                    "amount": 2000,
                    "method": MetodoPago.TRANSFERENCIA,
                    "reference": "TRX-1",
                    "date": configuracion["rows"][1]["date"],
                },
            ],
        )
        self.assertRegex(configuracion["rows"][0]["date"], r"^\d{1,2} \w+ \d{4}, \d{2}:\d{2}$")

    def test_agregar_un_anticipo_a_una_cita_sin_pago_crea_el_pago(self):
        self.encender()
        self.crear()
        cita = Cita.objects.get()
        respuesta = self.editar(cita, [self.anticipo(3000)])
        self.assertEqual(respuesta.status_code, 200)
        fila = DetallePago.objects.get()
        self.assertEqual(fila.pago.cita, cita)
        self.assertEqual((fila.monto_pago, fila.tipo_detalle), (Decimal("3000"), TipoDetallePago.ANTICIPO))

    def test_agregar_un_anticipo_usa_el_mismo_pago(self):
        cita = self.cita_con([self.anticipo(4000)])
        respuesta = self.editar(cita, [self.anticipo(1500, MetodoPago.TARJETA)])
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Pago.objects.count(), 1)
        self.assertEqual([fila.monto_pago for fila in self.filas(cita)], [Decimal("4000"), Decimal("1500")])

    def test_los_anticipos_guardados_que_no_llegan_quedan_igual(self):
        cita = self.cita_con([self.anticipo(4000)])
        antes = self.filas(cita)[0]
        respuesta = self.editar(cita, [])
        self.assertEqual(respuesta.status_code, 200)
        despues = self.filas(cita)[0]
        self.assertEqual((despues.pk, despues.monto_pago, despues.history.count()), (antes.pk, Decimal("4000"), 1))

    def test_la_encargada_corrige_un_anticipo_guardado(self):
        cita = self.cita_con([self.anticipo(4000)])
        fila = self.filas(cita)[0]
        fecha = fila.fecha_pago
        respuesta = self.editar(
            cita, [{"id": fila.pk, **self.anticipo(4500, MetodoPago.TRANSFERENCIA, " TRX-9 ")}]
        )
        self.assertEqual(respuesta.status_code, 200)
        fila.refresh_from_db()
        self.assertEqual(
            (fila.monto_pago, fila.metodo_pago, fila.referencia_pago, fila.fecha_pago),
            (Decimal("4500"), MetodoPago.TRANSFERENCIA, "TRX-9", fecha),
        )
        self.assertEqual(fila.estado_detalle, EstadoDetallePago.VIGENTE)
        self.assertEqual(fila.history.count(), 2)

    def test_reenviar_un_anticipo_sin_cambios_no_lo_guarda_de_nuevo(self):
        cita = self.cita_con([self.anticipo(4000)])
        fila = self.filas(cita)[0]
        respuesta = self.editar(cita, [{"id": fila.pk, **self.anticipo(4000)}])
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(fila.history.count(), 1)

    def test_la_encargada_quita_un_anticipo_guardado(self):
        cita = self.cita_con([self.anticipo(4000), self.anticipo(1000)])
        primera, segunda = self.filas(cita)
        respuesta = self.editar(cita, [{"id": primera.pk, "quitar": True}])
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.filas(cita), [segunda])
        self.assertEqual(DetallePago.history.filter(id=primera.pk, history_type="-").count(), 1)
        self.assertTrue(Pago.objects.filter(cita=cita).exists())

    def test_la_colaboradora_ve_los_guardados_bloqueados_y_agrega_nuevos(self):
        cita = self.cita_con([self.anticipo(4000)], asignada=self.colaboradora)
        configuracion = self.abrir(cita, self.colaboradora).context["appointment_form_config"]["advances"]
        self.assertFalse(configuracion["canChangeSaved"])
        respuesta = self.editar(cita, [self.anticipo(1000)], usuario=self.colaboradora)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(len(self.filas(cita)), 2)

    def test_la_colaboradora_no_cambia_ni_quita_anticipos_guardados(self):
        cita = self.cita_con([self.anticipo(4000)], asignada=self.colaboradora)
        fila = self.filas(cita)[0]
        for cambio in ({"id": fila.pk, **self.anticipo(100)}, {"id": fila.pk, "quitar": True}):
            with self.subTest(cambio=cambio):
                respuesta = self.editar(cita, [cambio], usuario=self.colaboradora)
                self.assertIn(
                    "Solo la propietaria o la encargada pueden cambiar anticipos ya registrados.",
                    self.errores(respuesta)["id_advances"],
                )
                fila.refresh_from_db()
                self.assertEqual(fila.monto_pago, Decimal("4000"))

    def test_un_anticipo_con_devolucion_no_aparece_ni_se_puede_tocar(self):
        cita = self.cita_con([self.anticipo(4000), self.anticipo(3000)])
        fila, vigente = self.filas(cita)
        DetallePago.objects.create(
            pago=fila.pago,
            fecha_pago=timezone.now(),
            monto_pago=Decimal("1000"),
            metodo_pago=MetodoPago.EFECTIVO,
            tipo_detalle=TipoDetallePago.DEVOLUCION,
            detalle_devuelto=fila,
        )
        configuracion = self.abrir(cita).context["appointment_form_config"]["advances"]
        self.assertEqual([fila["id"] for fila in configuracion["rows"]], [vigente.pk])
        for cambio in ({"id": fila.pk, **self.anticipo(100)}, {"id": fila.pk, "quitar": True}):
            with self.subTest(cambio=cambio):
                respuesta = self.editar(cita, [cambio])
                self.assertIn("Los anticipos enviados no son válidos.", self.errores(respuesta)["id_advances"])
        self.assertTrue(DetallePago.objects.filter(pk=fila.pk).exists())

    def test_rechaza_ids_ajenos_o_repetidos(self):
        otra = self.cita_con([self.anticipo(1000)])
        cita = self.cita_con([self.anticipo(4000)])
        propia = self.filas(cita)[0]
        ajena = self.filas(otra)[0]
        casos = [
            [{"id": ajena.pk, **self.anticipo(500)}],
            [{"id": "abc", **self.anticipo(500)}],
            [{"id": propia.pk, **self.anticipo(500)}, {"id": propia.pk, "quitar": True}],
        ]
        for anticipos in casos:
            with self.subTest(anticipos=anticipos):
                respuesta = self.editar(cita, anticipos)
                self.assertIn("Los anticipos enviados no son válidos.", self.errores(respuesta)["id_advances"])
        ajena.refresh_from_db()
        self.assertEqual(ajena.monto_pago, Decimal("1000"))

    def test_lo_guardado_mas_lo_nuevo_no_supera_el_total(self):
        cita = self.cita_con([self.anticipo(6000)])
        respuesta = self.editar(cita, [self.anticipo(4001)])
        self.assertIn(
            "Los anticipos suman $10.001 y no pueden superar el total de los servicios ($10.000).",
            self.errores(respuesta)["id_advances"],
        )
        self.assertEqual(len(self.filas(cita)), 1)

    def test_corregir_o_quitar_libera_espacio_para_lo_nuevo(self):
        cita = self.cita_con([self.anticipo(6000), self.anticipo(4000)])
        primera, segunda = self.filas(cita)
        respuesta = self.editar(
            cita,
            [{"id": primera.pk, **self.anticipo(1000)}, {"id": segunda.pk, "quitar": True}, self.anticipo(9000)],
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(sorted(fila.monto_pago for fila in self.filas(cita)), [Decimal("1000"), Decimal("9000")])

    def test_los_servicios_no_bajan_de_lo_ya_pagado(self):
        cita = self.cita_con([self.anticipo(8000)])
        respuesta = self.editar(cita, [], descuento=3000)
        self.assertIn(
            "Los anticipos suman $8.000 y no pueden superar el total de los servicios ($7.000).",
            self.errores(respuesta)["id_advances"],
        )

    def test_sin_interruptor_los_servicios_tampoco_bajan_de_lo_pagado(self):
        cita = self.cita_con([self.anticipo(8000)])
        Preference.objects.filter(key="advance_module").update(value=False)
        respuesta = self.editar(cita, [{"id": self.filas(cita)[0].pk, "quitar": True}], descuento=3000)
        self.assertIn("$8.000", self.errores(respuesta)["id_services"])
        self.assertEqual(len(self.filas(cita)), 1)

    def test_editar_refresca_las_fotos_y_el_total_del_pago(self):
        cita = self.cita_con([self.anticipo(4000)])
        otra = type(self.cliente).objects.create(nombre="Marta", apellido="Soto")
        respuesta = self.editar(cita, [], descuento=2000, client=otra.pk, date="2026-11-09", time="15:45")
        self.assertEqual(respuesta.status_code, 200)
        pago = Pago.objects.get(cita=cita)
        self.assertEqual(pago.cliente_nombre, "Marta Soto")
        self.assertEqual(timezone.localtime(pago.fecha_cita).strftime("%Y-%m-%d %H:%M"), "2026-11-09 15:45")
        self.assertEqual((pago.monto_total_cita, pago.descuento_total), (Decimal("8000"), Decimal("2000")))
