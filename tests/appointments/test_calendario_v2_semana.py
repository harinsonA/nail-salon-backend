from datetime import date, datetime, time
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.appointments.calendar_v2.query import CalendarQuery
from apps.appointments.models import Cita
from apps.clients.models import Cliente
from apps.profiles.models import Perfil
from apps.settings.models import Preference
from apps.settings.preferences import Scope
from tests.base import NegocioTestCase

User = get_user_model()

AHORA = datetime(2026, 10, 21, 12, 0)
SEMANA = {"vista": "semana", "desde": "2026-10-19", "hasta": "2026-10-25"}


class CalendarioV2SemanaTests(NegocioTestCase):
    esquema = "calendario_semana"
    dominio = "calendario-semana.localhost"

    def setUp(self):
        super().setUp()
        Preference.objects.create(scope=Scope.NEGOCIO, scope_id="", key="calendario_v2", value=True)
        self.encargada = User.objects.create_user(username="ana", email="ana@correo.cl", password="x")
        Perfil.objects.filter(user=self.encargada).update(rol=Perfil.Rol.ENCARGADO, debe_cambiar_clave=False)
        self.cliente = Cliente.objects.create(nombre="Paula", apellido="Herrera")

    def cita(self, dia, hora, estado=Cita.EstadoChoices.PENDIENTE):
        return Cita.objects.create(
            cliente=self.cliente,
            fecha_agenda=date(2026, 10, dia),
            hora_agenda=time(*hora),
            estado=estado,
            asignado_a=self.encargada,
        )

    def datos(self, **filtros):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(self.encargada)
        with mock.patch.object(CalendarQuery, "now", return_value=timezone.make_aware(AHORA)):
            return navegador.get(reverse("calendar_v2_data"), {**SEMANA, **filtros}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def test_agrupa_las_citas_en_bloques_de_la_hora_en_que_empiezan(self):
        self.cita(22, (10, 0))
        self.cita(22, (10, 30))
        self.cita(22, (11, 0))
        respuesta = self.datos()
        self.assertEqual(respuesta.status_code, 200)
        dia = respuesta.json()["dias"]["2026-10-22"]
        self.assertEqual(dia["total"], 3)
        self.assertEqual([bloque["hora"] for bloque in dia["bloques"]], [10, 11])
        self.assertEqual([cita["hora"] for cita in dia["bloques"][0]["citas"]], ["10:00", "10:30"])

    def test_el_bloque_toma_el_estado_de_sus_citas_o_queda_mixto(self):
        self.cita(23, (9, 0))
        self.cita(23, (9, 15))
        self.cita(23, (15, 0), estado=Cita.EstadoChoices.COMPLETADA)
        self.cita(23, (15, 30))
        bloques = {bloque["hora"]: bloque["estado"] for bloque in self.datos().json()["dias"]["2026-10-23"]["bloques"]}
        self.assertEqual(bloques, {9: "pendiente", 15: "mixto"})

    def test_el_bloque_de_pendientes_que_ya_pasaron_queda_como_vencida(self):
        self.cita(20, (10, 0))
        bloque = self.datos().json()["dias"]["2026-10-20"]["bloques"][0]
        self.assertEqual(bloque["estado"], "vencida")
        self.assertTrue(bloque["citas"][0]["sin_cerrar"])

    def test_cada_cita_del_bloque_trae_sus_acciones(self):
        cita = self.cita(24, (12, 0))
        acciones = self.datos().json()["dias"]["2026-10-24"]["bloques"][0]["citas"][0]["acciones"]
        self.assertEqual(acciones[0]["link"], reverse("agenda_see_modal", args=[cita.pk]))

    def test_la_pagina_abre_en_mes_y_ofrece_dia_semana_y_mes_en_orden(self):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(self.encargada)
        respuesta = navegador.get(reverse("calendar_v2"))
        configuracion = respuesta.context["calendar_config"]
        self.assertEqual(configuracion["view"], "mes")
        self.assertEqual([vista["key"] for vista in configuracion["views"]], ["dia", "semana", "mes"])
        self.assertEqual(configuracion["hours"], {"desde": 5, "hasta": 24})
        self.assertContains(respuesta, 'data-cal2-view="semana"')
        self.assertContains(respuesta, 'data-cal2-view="mes"')
