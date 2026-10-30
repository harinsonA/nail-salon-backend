import json
from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.appointments.models import Cita, DetalleCita
from apps.clients.models import Cliente
from apps.payments.choices import EstadoDetallePago, EstadoPago, MetodoPago, TipoDetallePago
from apps.payments.models import DetallePago, Pago
from apps.payments.services.account import net_paid
from apps.payments.services.advances import register_advances
from apps.profiles.models import Perfil
from apps.services.models import Categoria, Servicio
from tests.base import NegocioTestCase

User = get_user_model()
Rol = Perfil.Rol


class CitaConAnticiposBase(NegocioTestCase):
    def setUp(self):
        super().setUp()
        self.encargada = self.miembro(Rol.ENCARGADO, "ana")
        self.colaboradora = self.miembro(Rol.COLABORADOR, "camila")
        categoria = Categoria.objects.create(nombre="Manos")
        self.servicio = Servicio.objects.create(nombre="Manicure", precio=Decimal("20000"), categoria=categoria)
        self.cita = self.nueva_cita(self.colaboradora)

    def miembro(self, rol, usuario):
        user = User.objects.create_user(username=usuario, email=f"{usuario}@correo.cl", password="x")
        Perfil.objects.filter(user=user).update(rol=rol, debe_cambiar_clave=False)
        return User.objects.get(pk=user.pk)

    def nueva_cita(self, asignada):
        cita = Cita.objects.create(
            cliente=Cliente.objects.create(nombre="Paula", apellido="Herrera"),
            fecha_agenda=date(2026, 11, 2),
            hora_agenda=time(10, 0),
            asignado_a=asignada,
        )
        DetalleCita.objects.create(cita=cita, servicio=self.servicio, precio_acordado=Decimal("20000"))
        return cita

    def con_anticipos(self, *anticipos, cita=None):
        filas = [{"amount": monto, "method": metodo, "reference": ""} for monto, metodo in anticipos]
        register_advances(cita or self.cita, filas, self.encargada)
        return list(DetallePago.objects.filter(pago__cita=cita or self.cita).order_by("pk"))

    def navegador(self, usuario=None):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario or self.encargada)
        return navegador

    def url(self, cita=None):
        return reverse("agenda_cancel_modal", args=[(cita or self.cita).pk])

    def abrir(self, usuario=None, cita=None):
        return self.navegador(usuario).get(self.url(cita), HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def cancelar(self, reembolsos=None, usuario=None, cita=None):
        datos = {} if reembolsos is None else {"refunds": json.dumps(reembolsos)}
        return self.navegador(usuario).post(self.url(cita), datos, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def reembolso(self, fila, metodo=MetodoPago.EFECTIVO, referencia=""):
        return {"id": fila.pk, "metodo": metodo, "referencia": referencia}

    def estados(self):
        return [fila.estado_detalle for fila in DetallePago.objects.filter(tipo_detalle=TipoDetallePago.ANTICIPO).order_by("pk")]


class CancelarCitaConAnticiposTests(CitaConAnticiposBase):
    esquema = "cancelar_cita_anticipos"
    dominio = "cancelar-cita-anticipos.localhost"

    def test_sin_anticipos_cancela_como_hoy(self):
        respuesta = self.abrir()
        self.assertNotContains(respuesta, "¿Qué hacemos con los anticipos?")
        self.assertEqual(self.cancelar().status_code, 200)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.CANCELADA)
        self.assertFalse(Pago.objects.exists())

    def test_el_panel_lista_los_anticipos_para_decidir(self):
        primera, segunda = self.con_anticipos((6000, MetodoPago.TARJETA), (4000, MetodoPago.TRANSFERENCIA))
        respuesta = self.abrir()
        self.assertContains(respuesta, "¿Qué hacemos con los anticipos?")
        self.assertContains(respuesta, 'name="refunds"')
        decision = respuesta.context["cancel_advances"]
        self.assertFalse(decision["locked"])
        self.assertEqual([fila["id"] for fila in decision["config"]["rows"]], [primera.pk, segunda.pk])
        self.assertEqual(decision["config"]["rows"][0]["methodLabel"], "Tarjeta")
        self.assertEqual(
            decision["config"]["refundMethods"],
            [(MetodoPago.EFECTIVO, "Efectivo"), (MetodoPago.TRANSFERENCIA, "Transferencia")],
        )

    def test_sin_reembolsos_retiene_todo_y_el_pago_queda_completado(self):
        self.con_anticipos((6000, MetodoPago.TARJETA), (4000, MetodoPago.EFECTIVO))
        respuesta = self.cancelar([])
        self.assertEqual(respuesta.status_code, 200)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.CANCELADA)
        self.assertEqual(self.estados(), [EstadoDetallePago.RETENIDO, EstadoDetallePago.RETENIDO])
        pago = Pago.objects.get()
        self.assertEqual((pago.estado_pago, pago.monto_total_cita), (EstadoPago.COMPLETADO, Decimal("10000")))
        self.assertIsNotNone(pago.fecha_pago_completado)

    def test_reembolsar_uno_crea_la_devolucion_enlazada(self):
        primera, segunda = self.con_anticipos((6000, MetodoPago.TARJETA), (4000, MetodoPago.TRANSFERENCIA))
        respuesta = self.cancelar([self.reembolso(segunda, MetodoPago.TRANSFERENCIA, " TRX-DEV-1 ")])
        self.assertEqual(respuesta.status_code, 200)
        devolucion = DetallePago.objects.get(tipo_detalle=TipoDetallePago.DEVOLUCION)
        self.assertEqual(devolucion.detalle_devuelto, segunda)
        self.assertEqual(
            (devolucion.monto_pago, devolucion.metodo_pago, devolucion.referencia_pago, devolucion.registrado_por),
            (Decimal("4000"), MetodoPago.TRANSFERENCIA, "TRX-DEV-1", self.encargada),
        )
        self.assertEqual(self.estados(), [EstadoDetallePago.RETENIDO, EstadoDetallePago.DEVUELTO])
        pago = Pago.objects.get()
        self.assertEqual((pago.estado_pago, pago.monto_total_cita), (EstadoPago.COMPLETADO, Decimal("6000")))
        self.assertEqual(DetallePago.objects.aggregate(total=net_paid())["total"], Decimal("6000"))

    def test_reembolsar_todo_deja_el_pago_reembolsado(self):
        primera, segunda = self.con_anticipos((6000, MetodoPago.TARJETA), (4000, MetodoPago.EFECTIVO))
        respuesta = self.cancelar([self.reembolso(primera), self.reembolso(segunda, referencia="no se guarda")])
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self.estados(), [EstadoDetallePago.DEVUELTO, EstadoDetallePago.DEVUELTO])
        self.assertEqual(
            list(DetallePago.objects.filter(tipo_detalle=TipoDetallePago.DEVOLUCION).values_list("referencia_pago", flat=True)),
            [None, None],
        )
        pago = Pago.objects.get()
        self.assertEqual((pago.estado_pago, pago.monto_total_cita), (EstadoPago.REEMBOLSADO, Decimal("0")))
        self.assertEqual(DetallePago.objects.aggregate(total=net_paid())["total"], Decimal("0"))

    def test_el_detalle_de_la_cita_cancelada_muestra_lo_retenido_y_reembolsado(self):
        primera, segunda = self.con_anticipos((6000, MetodoPago.TARJETA), (4000, MetodoPago.EFECTIVO))
        self.cancelar([self.reembolso(segunda)])
        respuesta = self.navegador().get(
            reverse("agenda_see_modal", args=[self.cita.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        filas = {fila["label"]: fila["value"] for fila in respuesta.context["payment"]["rows"]}
        self.assertEqual(filas, {"Estado": "Cita cancelada", "Retenido": "$6.000", "Reembolsado": "$4.000"})

    def test_solo_se_reembolsa_en_efectivo_o_transferencia(self):
        fila = self.con_anticipos((6000, MetodoPago.TARJETA))[0]
        for metodo in (MetodoPago.TARJETA, MetodoPago.CHEQUE, "CRIPTOMONEDA"):
            with self.subTest(metodo=metodo):
                respuesta = self.cancelar([self.reembolso(fila, metodo)])
                self.assertEqual(respuesta.status_code, 400)
                self.assertEqual(respuesta.json()["message"], "Los reembolsos enviados no son válidos.")

    def test_rechaza_reembolsos_mal_formados_sin_cancelar(self):
        fila = self.con_anticipos((6000, MetodoPago.EFECTIVO))[0]
        ajena = self.con_anticipos((1000, MetodoPago.EFECTIVO), cita=self.nueva_cita(self.encargada))[0]
        casos = [
            "no es json",
            json.dumps({"id": fila.pk}),
            json.dumps(["texto"]),
            json.dumps([{"id": "abc", "metodo": MetodoPago.EFECTIVO}]),
            json.dumps([self.reembolso(ajena)]),
            json.dumps([self.reembolso(fila), self.reembolso(fila)]),
            json.dumps([self.reembolso(fila, MetodoPago.TRANSFERENCIA, "x" * 101)]),
        ]
        for reembolsos in casos:
            with self.subTest(reembolsos=reembolsos):
                respuesta = self.navegador().post(
                    self.url(), {"refunds": reembolsos}, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
                )
                self.assertEqual(respuesta.status_code, 400)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.PENDIENTE)
        self.assertFalse(DetallePago.objects.filter(tipo_detalle=TipoDetallePago.DEVOLUCION).exists())
        fila.refresh_from_db()
        self.assertEqual(fila.estado_detalle, EstadoDetallePago.VIGENTE)

    def test_la_colaboradora_no_cancela_una_cita_con_anticipos(self):
        self.con_anticipos((6000, MetodoPago.EFECTIVO))
        respuesta = self.abrir(self.colaboradora)
        self.assertTrue(respuesta.context["cancel_advances"]["locked"])
        self.assertContains(respuesta, "Solo la propietaria o la encargada pueden cancelarla.")
        self.assertNotContains(respuesta, 'name="refunds"')
        respuesta = self.cancelar([], usuario=self.colaboradora)
        self.assertEqual(respuesta.status_code, 403)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.PENDIENTE)
        self.assertEqual(self.estados(), [EstadoDetallePago.VIGENTE])

    def test_la_colaboradora_sigue_cancelando_citas_sin_anticipos(self):
        self.assertEqual(self.cancelar(usuario=self.colaboradora).status_code, 200)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.CANCELADA)

    def test_los_cambios_de_estado_quedan_en_el_historial(self):
        fila = self.con_anticipos((6000, MetodoPago.EFECTIVO))[0]
        self.cancelar([])
        self.assertEqual(
            list(fila.history.order_by("history_date").values_list("estado_detalle", flat=True)),
            [EstadoDetallePago.VIGENTE, EstadoDetallePago.RETENIDO],
        )
