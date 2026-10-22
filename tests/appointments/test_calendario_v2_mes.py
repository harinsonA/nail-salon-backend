from datetime import date, datetime, time
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.appointments.calendar_v2.query import CalendarQuery
from apps.appointments.models import Cita
from apps.clients.models import Cliente
from apps.payments.choices import EstadoPago
from apps.payments.models import Pago
from apps.profiles.models import Perfil
from apps.settings.models import Preference
from apps.settings.preferences import Scope
from tests.base import NegocioTestCase

User = get_user_model()
Rol = Perfil.Rol

AHORA = datetime(2026, 10, 21, 12, 0)
OCTUBRE = {"vista": "mes", "desde": "2026-09-28", "hasta": "2026-11-01"}


class CalendarioV2MesTests(NegocioTestCase):
    esquema = "calendario_mes"
    dominio = "calendario-mes.localhost"

    def setUp(self):
        super().setUp()
        Preference.objects.create(scope=Scope.NEGOCIO, scope_id="", key="calendario_v2", value=True)
        self.encargada = self.crear_usuario("ana", Rol.ENCARGADO)
        self.colaboradora = self.crear_usuario("camila", Rol.COLABORADOR)
        self.paula = Cliente.objects.create(nombre="Paula", apellido="Herrera")
        self.javiera = Cliente.objects.create(nombre="Javiera", apellido="Morales")

    def crear_usuario(self, nombre, rol):
        usuario = User.objects.create_user(username=nombre, email=f"{nombre}@correo.cl", password="x")
        Perfil.objects.filter(user=usuario).update(rol=rol, debe_cambiar_clave=False)
        return usuario

    def cita(self, dia, hora, cliente=None, estado=Cita.EstadoChoices.PENDIENTE, asignado_a=None):
        return Cita.objects.create(
            cliente=cliente or self.paula,
            fecha_agenda=date(2026, 10, dia),
            hora_agenda=time(*hora),
            estado=estado,
            asignado_a=asignado_a or self.encargada,
        )

    def datos(self, usuario=None, **filtros):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario or self.encargada)
        with mock.patch.object(CalendarQuery, "now", return_value=timezone.make_aware(AHORA)):
            return navegador.get(reverse("calendar_v2_data"), {**OCTUBRE, **filtros}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def test_agrupa_por_dia_con_tres_citas_y_el_resto_como_mas(self):
        for hora in [(9, 0), (10, 30), (12, 0), (15, 0), (17, 30)]:
            self.cita(23, hora)
        respuesta = self.datos()
        self.assertEqual(respuesta.status_code, 200)
        dia = respuesta.json()["dias"]["2026-10-23"]
        self.assertEqual(dia["total"], 5)
        self.assertEqual(dia["mas"], 2)
        self.assertEqual([cita["hora"] for cita in dia["citas"]], ["09:00", "10:30", "12:00"])

    def test_solo_trae_el_rango_pedido(self):
        self.cita(15, (10, 0))
        respuesta = self.datos(desde="2026-10-01", hasta="2026-10-07")
        self.assertEqual(respuesta.json()["dias"], {})

    def test_marca_las_pendientes_que_ya_pasaron(self):
        pasada = self.cita(20, (10, 0))
        de_hoy_pasada = self.cita(21, (11, 0))
        de_hoy_futura = self.cita(21, (16, 0))
        futura = self.cita(22, (10, 0))
        completada = self.cita(19, (10, 0), estado=Cita.EstadoChoices.COMPLETADA)
        dias = self.datos().json()["dias"]
        marcas = {cita["id"]: cita["sin_cerrar"] for dia in dias.values() for cita in dia["citas"]}
        self.assertTrue(marcas[pasada.pk])
        self.assertTrue(marcas[de_hoy_pasada.pk])
        self.assertFalse(marcas[de_hoy_futura.pk])
        self.assertFalse(marcas[futura.pk])
        self.assertFalse(marcas[completada.pk])

    def test_marca_las_completadas_con_saldo(self):
        con_saldo = self.cita(14, (10, 0), estado=Cita.EstadoChoices.COMPLETADA)
        pagada = self.cita(14, (12, 0), cliente=self.javiera, estado=Cita.EstadoChoices.COMPLETADA)
        for cita, estado in [(con_saldo, EstadoPago.PENDIENTE), (pagada, EstadoPago.COMPLETADO)]:
            Pago.objects.create(
                cita=cita,
                monto_total_cita=Decimal("20000"),
                cliente_nombre="Cliente",
                fecha_cita=timezone.now(),
                estado_pago=estado,
            )
        citas = {cita["id"]: cita for cita in self.datos().json()["dias"]["2026-10-14"]["citas"]}
        self.assertTrue(citas[con_saldo.pk]["con_saldo"])
        self.assertFalse(citas[pagada.pk]["con_saldo"])

    def test_las_acciones_traen_la_url_de_cada_cita_segun_el_estado(self):
        pendiente = self.cita(8, (10, 0))
        completada = self.cita(8, (11, 0), estado=Cita.EstadoChoices.COMPLETADA)
        cancelada = self.cita(8, (12, 0), estado=Cita.EstadoChoices.CANCELADA)
        citas = {cita["id"]: cita["acciones"] for cita in self.datos().json()["dias"]["2026-10-08"]["citas"]}
        self.assertEqual(
            [accion["link"] for accion in citas[pendiente.pk]],
            [
                reverse("agenda_see_modal", args=[pendiente.pk]),
                reverse("agenda_update_modal", args=[pendiente.pk]),
                reverse("agenda_confirmation_modal", args=[pendiente.pk]),
                reverse("agenda_cancel_modal", args=[pendiente.pk]),
            ],
        )
        self.assertEqual([accion["label"] for accion in citas[completada.pk]], ["Ver detalle"])
        self.assertEqual(
            [accion["link"] for accion in citas[cancelada.pk]],
            [reverse("agenda_see_modal", args=[cancelada.pk]), reverse("agenda_restore_modal", args=[cancelada.pk])],
        )

    def test_la_colaboradora_solo_ve_sus_citas(self):
        propia = self.cita(9, (10, 0), asignado_a=self.colaboradora)
        self.cita(9, (11, 0), cliente=self.javiera)
        citas_colaboradora = self.datos(self.colaboradora).json()["dias"]["2026-10-09"]["citas"]
        citas_encargada = self.datos().json()["dias"]["2026-10-09"]["citas"]
        self.assertEqual([cita["id"] for cita in citas_colaboradora], [propia.pk])
        self.assertEqual(len(citas_encargada), 2)

    def test_busca_por_nombre_o_apellido_del_cliente(self):
        self.cita(12, (10, 0))
        self.cita(12, (11, 0), cliente=self.javiera)
        por_nombre = self.datos(buscar="paula").json()["dias"]["2026-10-12"]["citas"]
        por_apellido = self.datos(buscar="morales").json()["dias"]["2026-10-12"]["citas"]
        self.assertEqual([cita["cliente"] for cita in por_nombre], ["Paula Herrera"])
        self.assertEqual([cita["cliente"] for cita in por_apellido], ["Javiera Morales"])

    def test_rechaza_rangos_invalidos(self):
        al_reves = self.datos(desde="2026-10-31", hasta="2026-10-01")
        muy_largo = self.datos(desde="2026-01-01", hasta="2026-12-31")
        self.assertEqual(al_reves.status_code, 400)
        self.assertEqual(muy_largo.status_code, 400)
        self.assertIn("42", muy_largo.json()["message"])

    def test_sin_la_preferencia_no_entrega_datos(self):
        Preference.objects.filter(key="calendario_v2").delete()
        self.assertEqual(self.datos().status_code, 404)

    def test_la_pagina_trae_la_configuracion_del_calendario(self):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(self.encargada)
        respuesta = navegador.get(reverse("calendar_v2"))
        configuracion = respuesta.context["calendar_config"]
        self.assertEqual(configuracion["dataUrl"], reverse("calendar_v2_data"))
        self.assertEqual(configuracion["today"], timezone.localdate().isoformat())
        self.assertEqual(
            configuracion["newAppointmentUrl"], reverse("create_appointment_from_calendar", args=["__fecha__"])
        )
        self.assertContains(respuesta, 'id="calendar-config"')
        self.assertContains(respuesta, "js/custom/calendar/calendar.controller.js")
