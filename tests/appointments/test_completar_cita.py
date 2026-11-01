from datetime import date, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.appointments.models import Cita, DetalleCita
from apps.clients.models import Cliente
from apps.payments.choices import EstadoDetallePago, TipoDetallePago
from apps.payments.models import Pago
from apps.profiles.models import Perfil
from apps.services.models import Categoria, Servicio
from tests.base import NegocioTestCase

User = get_user_model()


class CompletarCitaTests(NegocioTestCase):
    esquema = "completar_cita"
    dominio = "completar-cita.localhost"

    def setUp(self):
        super().setUp()
        self.encargada = User.objects.create_user(username="ana", email="ana@correo.cl", password="x")
        Perfil.objects.filter(user=self.encargada).update(rol=Perfil.Rol.ENCARGADO, debe_cambiar_clave=False)
        categoria = Categoria.objects.create(nombre="Manos")
        servicio = Servicio.objects.create(nombre="Manicure", precio=Decimal("10000"), categoria=categoria)
        self.cita = Cita.objects.create(
            cliente=Cliente.objects.create(nombre="Clienta"),
            fecha_agenda=date(2026, 10, 20),
            hora_agenda=time(10, 0),
        )
        DetalleCita.objects.create(cita=self.cita, servicio=servicio, precio_acordado=Decimal("10000"))

    def completar(self, **datos):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(self.encargada)
        return navegador.post(
            reverse("agenda_confirmation_modal", args=[self.cita.pk]),
            {"payment_method": "EFECTIVO", "remaining_payment": "0", **datos},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

    def assertNoSeCompleta(self, respuesta):
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("down_payment", str(respuesta.json()["errors"]))
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.PENDIENTE)
        self.assertFalse(Pago.objects.filter(cita=self.cita).exists())

    def test_sin_pago_completo_el_monto_abonado_vacio_cuenta_como_cero(self):
        respuesta = self.completar(down_payment="")
        self.assertEqual(respuesta.status_code, 200)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.COMPLETADA)
        self.assertFalse(self.cita.pago.detalles_pago.exists())

    def test_sin_pago_completo_el_monto_abonado_no_puede_ser_negativo(self):
        respuesta = self.completar(down_payment="-500")
        self.assertNoSeCompleta(respuesta)
        self.assertIn("El campo 'monto abonado' no puede ser negativo.", str(respuesta.json()["errors"]))

    def test_el_monto_abonado_con_punto_de_miles_se_guarda_completo(self):
        respuesta = self.completar(down_payment="4.000")
        self.assertEqual(respuesta.status_code, 200)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.pago.detalles_pago.get().monto_pago, Decimal("4000"))

    def test_sin_pago_completo_acepta_monto_abonado_cero(self):
        respuesta = self.completar(down_payment="0")
        self.assertEqual(respuesta.status_code, 200)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.COMPLETADA)
        self.assertFalse(self.cita.pago.detalles_pago.exists())

    def test_con_pago_completo_el_monto_abonado_vacio_no_importa(self):
        respuesta = self.completar(full_payment="on", down_payment="")
        self.assertEqual(respuesta.status_code, 200)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.COMPLETADA)
        self.assertEqual(self.cita.pago.detalles_pago.get().monto_pago, Decimal("10000"))

    def navegador(self, usuario=None):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario or self.encargada)
        return navegador

    def abrir(self, usuario=None):
        url = reverse("agenda_confirmation_modal", args=[self.cita.pk])
        return self.navegador(usuario).get(url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def test_abre_el_modal_con_el_formato_nuevo(self):
        respuesta = self.abrir()
        self.assertContains(respuesta, "Completar cita: Clienta")
        self.assertContains(respuesta, "Paga el total ahora")
        self.assertContains(respuesta, "$10.000")
        self.assertContains(respuesta, "20 octubre 2026, 10:00")
        self.assertContains(respuesta, "initAppointmentComplete")
        self.assertEqual(respuesta.context["total_value"], 10000)

    def test_un_abono_igual_al_total_pide_activar_el_pago_completo(self):
        respuesta = self.completar(down_payment="10000")
        self.assertNoSeCompleta(respuesta)
        self.assertIn('activa \\"Paga el total ahora\\"', respuesta.content.decode())

    def test_con_tarjeta_o_transferencia_la_referencia_es_opcional(self):
        respuesta = self.completar(full_payment="on", payment_method="TARJETA")
        self.assertEqual(respuesta.status_code, 200)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, Cita.EstadoChoices.COMPLETADA)
        abono = self.cita.pago.detalles_pago.get()
        self.assertEqual((abono.metodo_pago, abono.referencia_pago), ("TARJETA", None))

    def test_sin_pago_hoy_no_pide_referencia(self):
        respuesta = self.completar(down_payment="0", payment_method="TRANSFERENCIA")
        self.assertEqual(respuesta.status_code, 200)

    def test_guarda_la_referencia_y_las_observaciones_del_abono(self):
        respuesta = self.completar(
            down_payment="4000",
            payment_method="TRANSFERENCIA",
            payment_reference="TRX-123",
            observations="Paga el resto el viernes.",
        )
        self.assertEqual(respuesta.status_code, 200)
        abono = self.cita.pago.detalles_pago.get()
        self.assertEqual((abono.monto_pago, abono.referencia_pago), (Decimal("4000"), "TRX-123"))
        self.assertEqual(abono.notas_detalle, "Paga el resto el viernes.")
        self.assertEqual((abono.tipo_detalle, abono.estado_detalle), (TipoDetallePago.ABONO, EstadoDetallePago.VIGENTE))

    def test_las_observaciones_no_superan_250_caracteres(self):
        respuesta = self.completar(full_payment="on", observations="a" * 251)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("id_observations", str(respuesta.json()["errors"]))

    def test_solo_se_completan_citas_pendientes(self):
        self.cita.estado = Cita.EstadoChoices.CANCELADA
        self.cita.save()
        self.assertEqual(self.abrir().status_code, 404)
        self.assertEqual(self.completar(full_payment="on").status_code, 404)

    def test_la_colaboradora_solo_completa_las_suyas(self):
        colaboradora = User.objects.create_user(username="camila", email="camila@correo.cl", password="x")
        Perfil.objects.filter(user=colaboradora).update(rol=Perfil.Rol.COLABORADOR, debe_cambiar_clave=False)
        colaboradora = User.objects.get(pk=colaboradora.pk)
        self.cita.asignado_a = self.encargada
        self.cita.save()
        self.assertEqual(self.abrir(colaboradora).status_code, 404)
        self.cita.asignado_a = colaboradora
        self.cita.save()
        self.assertEqual(self.abrir(colaboradora).status_code, 200)
