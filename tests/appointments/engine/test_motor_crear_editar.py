from datetime import date, time
from decimal import Decimal

from apps.appointments.engine import AppointmentDraft, AppointmentWriter
from apps.appointments.engine.messages import (
    ADVANCE_LOCKED_ROLE,
    SERVICE_REPEATED,
    SERVICE_UNAVAILABLE,
    SERVICES_INVALID,
    SERVICES_REQUIRED,
)
from apps.appointments.models import Cita
from apps.payments.choices import MetodoPago, TipoDetallePago
from apps.settings.preferences import (
    RESERVATION_AMOUNT,
    RESERVATION_DISCOUNTS_TOTAL,
    RESERVATION_ENABLED,
    RESERVATION_PAYMENT_METHOD,
)
from tests.appointments.test_crear_cita import CitaBase


class MotorCrearEditarTests(CitaBase):
    esquema = "motor_crear_editar"

    def linea(self, servicio=None, cantidad=1, descuento=0):
        return {"id": (servicio or self.manicure).pk, "cantidad": cantidad, "descuento": descuento}

    def anticipo(self, monto, **extra):
        return {"monto": monto, "metodo": MetodoPago.EFECTIVO, "referencia": "", **extra}

    def datos(self, **extra):
        return {
            "assigned_to": self.encargada,
            "services": [self.linea()],
            "advances": [],
            "reservation": None,
            **extra,
        }

    def validar(self, usuario=None, cita=None, **extra):
        return AppointmentDraft(usuario or self.encargada, cita).validate(self.datos(**extra))

    def guardar(self, usuario=None, **extra):
        usuario = usuario or self.encargada
        limpios, errores = self.validar(usuario, **extra)
        self.assertEqual(errores, {})
        return AppointmentWriter(usuario).create(
            {
                **limpios,
                "client": self.cliente,
                "date": date(2026, 11, 4),
                "time": time(10, 30),
                "observations": "",
            }
        )

    def configurar_reserva(self, monto=5000, descuenta=False):
        RESERVATION_ENABLED.set(True)
        RESERVATION_AMOUNT.set(monto)
        RESERVATION_DISCOUNTS_TOTAL.set(descuenta)
        RESERVATION_PAYMENT_METHOD.set(MetodoPago.EFECTIVO)

    def test_calcula_el_total_de_cada_linea(self):
        limpios, errores = self.validar(
            services=[self.linea(descuento=2000), self.linea(self.diseno, cantidad=2)]
        )
        self.assertEqual(errores, {})
        self.assertEqual([linea["total"] for linea in limpios["services"]], [Decimal("8000"), Decimal("6000")])

    def test_errores_de_servicios_sin_formularios(self):
        casos = [
            ([], SERVICES_REQUIRED),
            ({"id": 1}, SERVICES_INVALID),
            ([self.linea(), self.linea()], SERVICE_REPEATED),
            ([{"id": 999999}], SERVICE_UNAVAILABLE),
        ]
        for servicios, mensaje in casos:
            with self.subTest(mensaje=mensaje):
                _, errores = self.validar(services=servicios)
                self.assertEqual(errores, {"services": [mensaje]})

    def test_la_colaboradora_queda_asignada_a_si_misma(self):
        limpios, _ = self.validar(self.colaboradora, assigned_to=self.encargada)
        self.assertEqual(limpios["assigned_to"], self.colaboradora)

    def test_el_tope_cae_en_anticipos(self):
        _, errores = self.validar(advances=[self.anticipo(12000)])
        self.assertEqual(
            errores,
            {"advances": ["Los anticipos suman $12.000 y no pueden superar el total de los servicios ($10.000)."]},
        )

    def test_el_tope_cae_en_la_reserva_si_no_hay_anticipos(self):
        self.configurar_reserva(monto=12000, descuenta=True)
        _, errores = self.validar(reservation={"activa": True, "metodo": MetodoPago.EFECTIVO})
        self.assertEqual(list(errores), ["reservation"])

    def test_crea_la_cita_con_reserva_y_anticipo(self):
        self.configurar_reserva(descuenta=True)
        cita = self.guardar(
            advances=[self.anticipo(2000)],
            reservation={"activa": True, "metodo": MetodoPago.EFECTIVO},
        )
        self.assertEqual(cita.estado, Cita.EstadoChoices.PENDIENTE)
        self.assertEqual(cita.detalles.get().precio_acordado, Decimal("10000"))
        self.assertEqual(
            list(cita.pago.detalles_pago.order_by("pk").values_list("tipo_detalle", "monto_pago")),
            [(TipoDetallePago.RESERVA_DESCONTABLE, Decimal("5000")), (TipoDetallePago.ANTICIPO, Decimal("2000"))],
        )

    def test_la_colaboradora_no_cambia_anticipos_guardados(self):
        cita = self.guardar(advances=[self.anticipo(2000)])
        fila = cita.pago.detalles_pago.get()
        _, errores = self.validar(
            self.colaboradora,
            cita,
            services=[{"detalle": cita.detalles.get().pk}],
            advances=[{"id": fila.pk, "quitar": True}],
        )
        self.assertEqual(errores, {"advances": [ADVANCE_LOCKED_ROLE]})

    def test_editar_actualiza_la_linea_guardada(self):
        cita = self.guardar()
        limpios, errores = self.validar(
            cita=cita, services=[{"detalle": cita.detalles.get().pk, "cantidad": 2, "descuento": 1000}]
        )
        self.assertEqual(errores, {})
        AppointmentWriter(self.encargada).update(
            cita,
            {**limpios, "client": self.cliente, "date": cita.fecha_agenda, "time": cita.hora_agenda, "observations": ""},
        )
        detalle = cita.detalles.get()
        self.assertEqual((detalle.cantidad_servicios, detalle.precio_acordado), (2, Decimal("19000")))
