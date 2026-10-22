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
SEMANA = {"vista": "dia", "desde": "2026-10-19", "hasta": "2026-10-25"}


class CalendarioV2DiaTests(NegocioTestCase):
    esquema = "calendario_dia"
    dominio = "calendario-dia.localhost"

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

    def test_cada_dia_trae_el_resumen_por_estado(self):
        self.cita(22, (9, 0))
        self.cita(22, (9, 30))
        self.cita(22, (11, 0), estado=Cita.EstadoChoices.COMPLETADA)
        self.cita(22, (15, 0), estado=Cita.EstadoChoices.CANCELADA)
        dia = self.datos().json()["dias"]["2026-10-22"]
        self.assertEqual(dia["total"], 4)
        self.assertEqual(dia["resumen"], {"pendiente": 2, "completada": 1, "cancelada": 1})

    def test_el_resumen_cuenta_por_estado_real_aunque_la_cita_este_sin_cerrar(self):
        self.cita(20, (10, 0))
        dia = self.datos().json()["dias"]["2026-10-20"]
        self.assertEqual(dia["resumen"]["pendiente"], 1)
        self.assertEqual(dia["bloques"][0]["estado"], "vencida")

    def test_trae_los_bloques_por_hora_de_toda_la_semana(self):
        self.cita(19, (10, 0))
        self.cita(19, (10, 45))
        self.cita(25, (18, 0))
        dias = self.datos().json()["dias"]
        self.assertEqual(set(dias), {"2026-10-19", "2026-10-25"})
        self.assertEqual([cita["hora"] for cita in dias["2026-10-19"]["bloques"][0]["citas"]], ["10:00", "10:45"])

    def test_el_buscador_tambien_filtra_el_resumen(self):
        self.cita(23, (10, 0))
        otra = Cliente.objects.create(nombre="Marta", apellido="Soto")
        Cita.objects.create(cliente=otra, fecha_agenda=date(2026, 10, 23), hora_agenda=time(11, 0))
        dia = self.datos(buscar="Marta").json()["dias"]["2026-10-23"]
        self.assertEqual(dia["total"], 1)
        self.assertEqual(dia["resumen"]["pendiente"], 1)

    def test_la_pagina_ofrece_dia_semana_y_mes_sin_el_listado_viejo_del_dia(self):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(self.encargada)
        respuesta = navegador.get(reverse("calendar_v2"))
        configuracion = respuesta.context["calendar_config"]
        self.assertEqual([vista["label"] for vista in configuracion["views"]], ["Día", "Semana", "Mes"])
        self.assertNotIn("dayUrl", configuracion)
        self.assertContains(respuesta, 'data-cal2-view="dia"')
