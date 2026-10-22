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
from apps.settings.preferences import (
    CALENDAR_DEFAULT_VIEW,
    CALENDAR_SHOW_CANCELLED,
    CALENDAR_SHOW_DEBT,
    Scope,
)
from tests.base import NegocioTestCase

User = get_user_model()
Rol = Perfil.Rol

AHORA = datetime(2026, 10, 21, 12, 0)
SEMANA = {"desde": "2026-10-19", "hasta": "2026-10-25"}


class CalendarioV2PreferenciasTests(NegocioTestCase):
    esquema = "calendario_preferencias"
    dominio = "calendario-preferencias.localhost"

    def setUp(self):
        super().setUp()
        Preference.objects.create(scope=Scope.NEGOCIO, scope_id="", key="calendario_v2", value=True)
        self.encargada = self.miembro(Rol.ENCARGADO, "ana")
        self.colaboradora = self.miembro(Rol.COLABORADOR, "camila")
        cliente = Cliente.objects.create(nombre="Paula", apellido="Herrera")
        for hora, estado in [
            ((10, 0), Cita.EstadoChoices.PENDIENTE),
            ((11, 0), Cita.EstadoChoices.COMPLETADA),
            ((12, 0), Cita.EstadoChoices.CANCELADA),
        ]:
            Cita.objects.create(
                cliente=cliente,
                fecha_agenda=date(2026, 10, 22),
                hora_agenda=time(*hora),
                estado=estado,
                asignado_a=self.colaboradora,
            )

    def miembro(self, rol, usuario):
        user = User.objects.create_user(username=usuario, email=f"{usuario}@correo.cl", password="x")
        Perfil.objects.filter(user=user).update(rol=rol, debe_cambiar_clave=False)
        return User.objects.get(pk=user.pk)

    def navegador(self, usuario=None):
        navegador = Client(HTTP_HOST=self.dominio)
        navegador.force_login(usuario or self.encargada)
        return navegador

    def configuracion(self, usuario=None):
        return self.navegador(usuario).get(reverse("calendar_v2")).context["calendar_config"]

    def datos(self, vista, usuario=None):
        with mock.patch.object(CalendarQuery, "now", return_value=timezone.make_aware(AHORA)):
            return self.navegador(usuario).get(
                reverse("calendar_v2_data"),
                {"vista": vista, **SEMANA},
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            ).json()

    def guardar(self, usuario=None, **cambios):
        datos = {
            "calendario_vista_inicial": "mes",
            "calendario_ver_pendientes": "on",
            "calendario_ver_completadas": "on",
            "calendario_ver_canceladas": "on",
            "calendario_aviso_saldo": "on",
            **cambios,
        }
        datos = {clave: valor for clave, valor in datos.items() if valor is not None}
        return self.navegador(usuario).post(
            reverse("calendar_v2_preferences"), datos, HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )

    def test_por_defecto_abre_en_mes_y_muestra_todo(self):
        configuracion = self.configuracion()
        self.assertEqual(configuracion["view"], "mes")
        self.assertEqual(
            configuracion["visible"], {"pendiente": True, "completada": True, "cancelada": True}
        )
        self.assertTrue(configuracion["showDebt"])
        self.assertNotContains(self.navegador().get(reverse("calendar_v2")), "is-filtered")

    def test_el_modal_muestra_las_dos_pestanas(self):
        respuesta = self.navegador().get(
            reverse("calendar_v2_preferences"), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertTemplateUsed(respuesta, "calendar_v2/preferences_modal.html")
        self.assertContains(respuesta, "Visibilidad")
        self.assertContains(respuesta, "Vista al ingresar")
        self.assertContains(respuesta, 'value="mes" class="form-check-input"', html=False)
        self.assertContains(respuesta, "Mostrar saldo pendiente")

    def test_guardar_cambia_la_vista_y_oculta_estados_solo_para_esa_persona(self):
        respuesta = self.guardar(calendario_vista_inicial="semana", calendario_ver_canceladas=None)
        self.assertEqual(respuesta.status_code, 200)
        ajustes = respuesta.json()["settings"]
        self.assertEqual(ajustes["view"], "semana")
        self.assertFalse(ajustes["visible"]["cancelada"])
        self.assertTrue(ajustes["filtered"])
        self.assertEqual(CALENDAR_DEFAULT_VIEW.get(self.encargada), "semana")
        self.assertFalse(CALENDAR_SHOW_CANCELLED.get(self.encargada))
        self.assertEqual(CALENDAR_DEFAULT_VIEW.get(self.colaboradora), "mes")
        self.assertTrue(CALENDAR_SHOW_CANCELLED.get(self.colaboradora))
        self.assertContains(self.navegador().get(reverse("calendar_v2")), "is-filtered")

    def test_el_aviso_de_saldo_se_puede_apagar(self):
        self.guardar(calendario_aviso_saldo=None)
        self.assertFalse(CALENDAR_SHOW_DEBT.get(self.encargada))
        self.assertFalse(self.configuracion()["showDebt"])

    def test_una_vista_invalida_no_se_guarda(self):
        respuesta = self.guardar(calendario_vista_inicial="anio")
        self.assertEqual(respuesta.status_code, 400)
        self.assertEqual(CALENDAR_DEFAULT_VIEW.get(self.encargada), "mes")

    def test_los_datos_llegan_sin_los_estados_ocultos(self):
        self.guardar(calendario_ver_canceladas=None, calendario_ver_completadas=None)
        mes = self.datos("mes")["dias"]["2026-10-22"]
        self.assertEqual(mes["total"], 1)
        self.assertEqual([cita["estado"] for cita in mes["citas"]], ["pendiente"])
        semana = self.datos("semana")["dias"]["2026-10-22"]
        self.assertEqual([bloque["hora"] for bloque in semana["bloques"]], [10])

    def test_el_resumen_del_dia_sigue_contando_todas(self):
        self.guardar(calendario_ver_canceladas=None)
        dia = self.datos("dia")["dias"]["2026-10-22"]
        self.assertEqual(dia["total"], 2)
        self.assertEqual(dia["resumen"], {"pendiente": 1, "completada": 1, "cancelada": 1})

    def test_sin_el_calendario_nuevo_no_hay_preferencias(self):
        Preference.objects.filter(key="calendario_v2").delete()
        respuesta = self.navegador().get(
            reverse("calendar_v2_preferences"), HTTP_X_REQUESTED_WITH="XMLHttpRequest"
        )
        self.assertEqual(respuesta.status_code, 404)
