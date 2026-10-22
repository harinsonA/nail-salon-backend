from datetime import date, datetime, time
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.appointments.models import Cita, DetalleCita
from apps.clients.models import Cliente
from apps.payments.choices import EstadoPago, MetodoPago
from apps.payments.models import DetallePago, Pago
from apps.profiles.models import Perfil
from tests.base import NegocioTestCase

User = get_user_model()
Rol = Perfil.Rol


class PanelCitaTests(NegocioTestCase):
    esquema = "panel_cita"
    dominio = "panel-cita.localhost"

    def setUp(self):
        super().setUp()
        self.encargada = self.miembro(Rol.ENCARGADO, "ana", "Ana", "Pérez")
        self.colaboradora = self.miembro(Rol.COLABORADOR, "camila", "Camila", "Rojas")
        self.cliente = Cliente.objects.create(nombre="Paula", apellido="Herrera", telefono="+56911112222")

    def miembro(self, rol, usuario, nombre, apellido):
        user = User.objects.create_user(
            username=usuario, email=f"{usuario}@correo.cl", password="x", first_name=nombre, last_name=apellido
        )
        Perfil.objects.filter(user=user).update(rol=rol, debe_cambiar_clave=False)
        return User.objects.get(pk=user.pk)

    def cita(self, estado=Cita.EstadoChoices.PENDIENTE, asignada=None, dia=date(2030, 1, 7)):
        cita = Cita.objects.create(
            cliente=self.cliente,
            fecha_agenda=dia,
            hora_agenda=time(10, 30),
            estado=estado,
            observaciones="Prefiere tonos nude.",
            creado_por=self.encargada,
            asignado_a=asignada or self.colaboradora,
        )
        DetalleCita.objects.create(
            cita=cita,
            nombre_servicio="Manicure",
            precio_servicio=Decimal("10000"),
            cantidad_servicios=2,
            descuento=Decimal("2000"),
            precio_acordado=Decimal("18000"),
        )
        return cita

    def abrir(self, nombre, cita, usuario=None):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario or self.encargada)
        return navegador.get(reverse(nombre, args=[cita.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def confirmar(self, nombre, cita, usuario=None):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario or self.encargada)
        return navegador.post(reverse(nombre, args=[cita.pk]), HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def test_el_detalle_muestra_la_cita_con_el_formato_nuevo(self):
        respuesta = self.abrir("agenda_see_modal", self.cita())
        self.assertTemplateUsed(respuesta, "appointments/agenda_panel.html")
        self.assertContains(respuesta, "Detalle de cita: Paula Herrera")
        self.assertContains(respuesta, "Lunes 7 enero 2030")
        self.assertContains(respuesta, "+56911112222")
        self.assertContains(respuesta, "Camila Rojas")
        self.assertContains(respuesta, "$20.000")
        self.assertContains(respuesta, "-$2.000")
        self.assertContains(respuesta, "$18.000")
        self.assertContains(respuesta, "Se registra al completar la cita")
        self.assertContains(respuesta, "Prefiere tonos nude.")
        self.assertContains(respuesta, "Cita creada por <strong>Ana Pérez (tú)</strong>")
        self.assertNotContains(respuesta, "data-panel-confirm")

    def test_una_pendiente_que_ya_paso_queda_sin_cerrar(self):
        respuesta = self.abrir("agenda_see_modal", self.cita(dia=date(2020, 1, 6)))
        self.assertContains(respuesta, "Pendiente sin cerrar")
        self.assertContains(respuesta, "calendar-event--vencida")

    def test_la_completada_muestra_sus_abonos_y_el_saldo(self):
        cita = self.cita(estado=Cita.EstadoChoices.COMPLETADA)
        pago = Pago.objects.create(
            cita=cita,
            monto_total_cita=Decimal("18000"),
            estado_pago=EstadoPago.PENDIENTE,
            cliente_nombre="Paula Herrera",
            fecha_cita=timezone.make_aware(datetime(2030, 1, 7, 10, 30)),
            atendido_por=self.colaboradora,
            atendido_por_nombre="Camila Rojas",
        )
        DetallePago.objects.create(
            pago=pago,
            fecha_pago=timezone.make_aware(datetime(2030, 1, 7, 11, 5)),
            monto_pago=Decimal("5000"),
            metodo_pago=MetodoPago.TRANSFERENCIA,
            registrado_por=self.colaboradora,
        )
        respuesta = self.abrir("agenda_see_modal", cita)
        self.assertContains(respuesta, "Atendió")
        self.assertContains(respuesta, "Pago incompleto")
        self.assertContains(respuesta, "$13.000")
        self.assertContains(respuesta, "7 enero 2030, 11:05")
        self.assertContains(respuesta, "Transferencia")

    def test_cancelar_muestra_el_panel_con_su_boton_y_cancela(self):
        cita = self.cita()
        respuesta = self.abrir("agenda_cancel_modal", cita)
        self.assertContains(respuesta, "Cancelar cita: Paula Herrera")
        self.assertContains(respuesta, "data-panel-confirm")
        self.assertEqual(self.confirmar("agenda_cancel_modal", cita).status_code, 200)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.EstadoChoices.CANCELADA)

    def test_restaurar_vuelve_la_cita_a_pendiente(self):
        cita = self.cita(estado=Cita.EstadoChoices.CANCELADA)
        self.assertContains(self.abrir("agenda_restore_modal", cita), "Restaurar cita: Paula Herrera")
        respuesta = self.confirmar("agenda_restore_modal", cita)
        self.assertIn("7 enero 2030", respuesta.json()["message"])
        cita.refresh_from_db()
        self.assertEqual(cita.estado, Cita.EstadoChoices.PENDIENTE)

    def test_la_colaboradora_no_abre_ni_cambia_citas_ajenas(self):
        ajena = self.cita(asignada=self.encargada)
        cancelada = self.cita(estado=Cita.EstadoChoices.CANCELADA, asignada=self.encargada)
        for nombre, cita in [("agenda_see_modal", ajena), ("agenda_cancel_modal", ajena), ("agenda_restore_modal", cancelada)]:
            self.assertEqual(self.abrir(nombre, cita, self.colaboradora).status_code, 404)
        self.assertEqual(self.confirmar("agenda_cancel_modal", ajena, self.colaboradora).status_code, 404)
        self.assertEqual(self.confirmar("agenda_restore_modal", cancelada, self.colaboradora).status_code, 404)
        ajena.refresh_from_db()
        self.assertEqual(ajena.estado, Cita.EstadoChoices.PENDIENTE)

    def test_la_colaboradora_si_abre_las_suyas(self):
        propia = self.cita()
        self.assertEqual(self.abrir("agenda_see_modal", propia, self.colaboradora).status_code, 200)
        self.assertEqual(self.confirmar("agenda_cancel_modal", propia, self.colaboradora).status_code, 200)

    def test_eliminar_muestra_el_panel_con_su_boton_y_elimina(self):
        cita = self.cita()
        respuesta = self.abrir("agenda_delete_modal", cita)
        self.assertContains(respuesta, "Eliminar cita: Paula Herrera")
        self.assertContains(respuesta, "btn-danger")
        confirmacion = self.confirmar("agenda_delete_modal", cita)
        self.assertEqual(confirmacion.status_code, 200)
        self.assertIn("fue eliminada", confirmacion.json()["message"])
        self.assertFalse(Cita.objects.filter(pk=cita.pk).exists())

    def test_la_colaboradora_no_elimina_citas_ajenas(self):
        ajena = self.cita(asignada=self.encargada)
        self.assertEqual(self.abrir("agenda_delete_modal", ajena, self.colaboradora).status_code, 404)
        self.assertEqual(self.confirmar("agenda_delete_modal", ajena, self.colaboradora).status_code, 404)
        self.assertTrue(Cita.objects.filter(pk=ajena.pk).exists())
