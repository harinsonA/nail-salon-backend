from datetime import date, datetime, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Cita, DetalleCita
from apps.clients.models import Cliente
from apps.payments.choices import (
    EstadoDetallePago,
    EstadoPago,
    MetodoPago,
    TipoDetallePago,
)
from apps.payments.models import DetallePago, Pago
from apps.profiles.models import Perfil
from tests.base import NegocioTestCase

User = get_user_model()
Rol = Perfil.Rol


class RegistrarAbonoTests(NegocioTestCase):
    esquema = "registrar_abono"
    dominio = "registrar-abono.localhost"

    def setUp(self):
        super().setUp()
        self.encargada = self.miembro(Rol.ENCARGADO, "ana", "Ana", "Pérez")
        self.colaboradora = self.miembro(Rol.COLABORADOR, "camila", "Camila", "Rojas")
        self.cliente = Cliente.objects.create(nombre="Paula", apellido="Herrera")
        self.cita = self.cita_completada(self.colaboradora)
        self.pago = self.pago_de(self.cita, abonado=Decimal("5000"))

    def miembro(self, rol, usuario, nombre, apellido):
        user = User.objects.create_user(
            username=usuario,
            email=f"{usuario}@correo.cl",
            password="x",
            first_name=nombre,
            last_name=apellido,
        )
        Perfil.objects.filter(user=user).update(rol=rol, debe_cambiar_clave=False)
        return User.objects.get(pk=user.pk)

    def cita_completada(self, asignada, dia=date(2026, 10, 20)):
        cita = Cita.objects.create(
            cliente=self.cliente,
            fecha_agenda=dia,
            hora_agenda=time(10, 30),
            estado=Cita.EstadoChoices.COMPLETADA,
            asignado_a=asignada,
        )
        DetalleCita.objects.create(
            cita=cita,
            nombre_servicio="Manicure",
            precio_servicio=Decimal("18000"),
            precio_acordado=Decimal("18000"),
        )
        return cita

    def pago_de(self, cita, abonado):
        pago = Pago.objects.create(
            cita=cita,
            monto_total_cita=Decimal("18000"),
            estado_pago=EstadoPago.PENDIENTE,
            cliente_nombre="Paula Herrera",
            fecha_cita=timezone.make_aware(datetime(2026, 10, 20, 10, 30)),
            atendido_por=self.colaboradora,
            atendido_por_nombre="Camila Rojas",
        )
        DetallePago.objects.create(
            pago=pago,
            fecha_pago=timezone.make_aware(datetime(2026, 10, 20, 11, 0)),
            monto_pago=abonado,
            metodo_pago=MetodoPago.EFECTIVO,
            registrado_por=self.colaboradora,
        )
        return pago

    def navegador(self, usuario=None):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario or self.encargada)
        return navegador

    def abrir(self, nombre, pk, usuario=None):
        url = reverse(nombre, args=[pk])
        return self.navegador(usuario).get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def abonar(self, nombre="add_payment_modal", pk=None, usuario=None, **datos):
        payload = {
            "payment_method": "EFECTIVO",
            "payment_date": "2026-10-22",
            "payment_time": "09:15",
            **datos,
        }
        url = reverse(nombre, args=[pk or self.pago.pk])
        return self.navegador(usuario).post(
            url, payload, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def errores(self, respuesta):
        self.assertEqual(respuesta.status_code, 400)
        return {
            error["id_element"]: error["error"] for error in respuesta.json()["errors"]
        }

    def test_deudores_abre_el_modal_con_el_formato_nuevo(self):
        respuesta = self.abrir("add_payment_modal", self.pago.pk)
        self.assertTemplateUsed(respuesta, "debtors/_add_payment.html")
        self.assertContains(respuesta, "Registrar abono: Paula Herrera")
        self.assertContains(respuesta, "$13.000")
        self.assertContains(respuesta, "20 octubre 2026, 11:00")
        self.assertEqual(
            respuesta.context["payment_config"],
            {"total": 18000, "paid": 5000, "balance": 13000},
        )

    def test_un_abono_parcial_queda_registrado_con_su_fecha_y_quien_lo_recibe(self):
        respuesta = self.abonar(down_payment="3000")
        self.assertEqual(respuesta.status_code, 200)
        abono = self.pago.detalles_pago.order_by("-pk").first()
        self.assertEqual(abono.monto_pago, Decimal("3000"))
        self.assertEqual(abono.registrado_por, self.encargada)
        self.assertEqual(
            (abono.tipo_detalle, abono.estado_detalle),
            (TipoDetallePago.ABONO, EstadoDetallePago.VIGENTE),
        )
        self.assertEqual(
            timezone.localtime(abono.fecha_pago).strftime("%Y-%m-%d %H:%M"),
            "2026-10-22 09:15",
        )
        self.pago.refresh_from_db()
        self.assertEqual(self.pago.estado_pago, EstadoPago.PENDIENTE)

    def test_el_abono_con_punto_de_miles_se_guarda_completo(self):
        self.assertEqual(self.abonar(down_payment="3.000").status_code, 200)
        self.assertEqual(
            self.pago.detalles_pago.order_by("-pk").first().monto_pago, Decimal("3000")
        )

    def test_abonar_justo_el_saldo_deja_el_pago_completado(self):
        self.assertEqual(self.abonar(down_payment="13000").status_code, 200)
        self.pago.refresh_from_db()
        self.assertEqual(self.pago.estado_pago, EstadoPago.COMPLETADO)

    def test_pagar_el_saldo_completo_registra_lo_que_faltaba(self):
        self.assertEqual(self.abonar(full_payment="on").status_code, 200)
        self.assertEqual(
            self.pago.detalles_pago.order_by("-pk").first().monto_pago, Decimal("13000")
        )
        self.pago.refresh_from_db()
        self.assertEqual(self.pago.estado_pago, EstadoPago.COMPLETADO)

    def test_el_abono_no_supera_el_saldo_ni_es_cero(self):
        self.assertIn(
            "$13.000",
            self.errores(self.abonar(down_payment="13001"))["id_down_payment"],
        )
        self.assertIn("id_down_payment", self.errores(self.abonar(down_payment="0")))

    def test_el_abono_vacio_pide_monto_y_el_negativo_se_rechaza(self):
        self.assertEqual(
            self.errores(self.abonar(down_payment=""))["id_down_payment"],
            "El monto debe ser mayor a $0.",
        )
        self.assertEqual(
            self.errores(self.abonar(down_payment="-500"))["id_down_payment"],
            "El campo 'monto abonado' no puede ser negativo.",
        )

    def test_sin_efectivo_la_referencia_es_opcional(self):
        respuesta = self.abonar(down_payment="3000", payment_method="TRANSFERENCIA")
        self.assertEqual(respuesta.status_code, 200)
        abono = self.pago.detalles_pago.order_by("-pk").first()
        self.assertEqual(
            (abono.metodo_pago, abono.referencia_pago), ("TRANSFERENCIA", None)
        )

    def test_guarda_la_referencia_cuando_la_ingresan(self):
        respuesta = self.abonar(
            down_payment="3000", payment_method="TARJETA", payment_reference="  TRX-9  "
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            self.pago.detalles_pago.order_by("-pk").first().referencia_pago, "TRX-9"
        )

    def test_un_pago_ya_saldado_no_acepta_otro_abono_en_deudores(self):
        DetallePago.objects.create(
            pago=self.pago,
            fecha_pago=timezone.now(),
            monto_pago=Decimal("13000"),
            metodo_pago=MetodoPago.EFECTIVO,
        )
        errores = self.errores(self.abonar(full_payment="on"))
        self.assertEqual(
            errores["id_down_payment"], "Este pago ya no tiene saldo pendiente."
        )

    def test_el_calendario_abre_el_mismo_modal_con_su_propio_acceso(self):
        respuesta = self.abrir("agenda_payment_modal", self.pago.pk)
        self.assertTemplateUsed(respuesta, "debtors/_add_payment.html")
        self.assertEqual(
            self.abrir(
                "agenda_payment_modal", self.pago.pk, self.colaboradora
            ).status_code,
            200,
        )
        respuesta = self.abonar(
            "agenda_payment_modal", down_payment="2000", usuario=self.colaboradora
        )
        self.assertEqual(respuesta.status_code, 200)

    def test_el_calendario_responde_404_si_no_hay_un_pago_pendiente_valido(self):
        ajena = self.pago_de(
            self.cita_completada(self.encargada, date(2026, 10, 21)),
            abonado=Decimal("1000"),
        )
        saldado = self.pago_de(
            self.cita_completada(self.colaboradora, date(2026, 10, 22)),
            abonado=Decimal("1000"),
        )
        saldado.estado_pago = EstadoPago.COMPLETADO
        saldado.save()
        borrado = self.pago_de(
            self.cita_completada(self.colaboradora, date(2026, 10, 23)),
            abonado=Decimal("1000"),
        )
        borrado.delete()
        self.assertEqual(
            self.abrir("agenda_payment_modal", ajena.pk, self.colaboradora).status_code,
            404,
        )
        self.assertEqual(
            self.abrir("agenda_payment_modal", saldado.pk).status_code, 404
        )
        self.assertEqual(
            self.abrir("agenda_payment_modal", borrado.pk).status_code, 404
        )
        self.assertEqual(self.abrir("agenda_payment_modal", 999999).status_code, 404)

    def acciones_del_dia(self, dia):
        respuesta = self.navegador().get(
            reverse("calendar_data"),
            {"vista": "mes", "desde": "2026-09-28", "hasta": "2026-11-01"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        cita = respuesta.json()["dias"][dia]["citas"][0]
        return {accion["label"]: accion["link"] for accion in cita["acciones"]}

    def test_el_menu_ofrece_registrar_abono_solo_con_saldo_pendiente(self):
        acciones = self.acciones_del_dia("2026-10-20")
        self.assertEqual(
            acciones["Registrar abono"],
            reverse("agenda_payment_modal", args=[self.pago.pk]),
        )
        self.pago.estado_pago = EstadoPago.COMPLETADO
        self.pago.save()
        self.assertNotIn("Registrar abono", self.acciones_del_dia("2026-10-20"))

    def test_una_completada_sin_pago_no_ofrece_abono_ni_falla(self):
        self.cita_completada(self.colaboradora, date(2026, 10, 24))
        self.assertEqual(list(self.acciones_del_dia("2026-10-24")), ["Ver detalle"])
        respuesta = self.abrir(
            "agenda_see_modal", Cita.objects.get(fecha_agenda=date(2026, 10, 24)).pk
        )
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, "data-panel-payment")

    def test_el_detalle_muestra_el_boton_de_abono_solo_si_hay_saldo(self):
        respuesta = self.abrir("agenda_see_modal", self.cita.pk)
        self.assertContains(
            respuesta, reverse("agenda_payment_modal", args=[self.pago.pk])
        )
        self.pago.estado_pago = EstadoPago.COMPLETADO
        self.pago.save()
        self.assertNotContains(
            self.abrir("agenda_see_modal", self.cita.pk), "data-panel-payment"
        )
