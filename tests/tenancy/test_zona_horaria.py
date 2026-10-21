from datetime import datetime
from datetime import timezone as dt_timezone
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import RequestFactory
from django.utils import timezone
from django_tenants.utils import get_tenant_model, schema_context

from apps.appointments.views.calendar.view import CalendarView
from apps.common.custom_time_fields import MONTH_NUMBER_TO_NAME, CustomMonthField
from apps.tareas.decorators import background_task
from apps.tareas.models import TareaEnProceso
from apps.tenancy.middleware import BusinessTimeZoneMiddleware
from dashboard.services.periods import last_n_months
from tests.base import NegocioTestCase

User = get_user_model()

FIN_DE_OCTUBRE_UTC = datetime(2026, 10, 31, 20, 0, tzinfo=dt_timezone.utc)
zonas_vistas = []


@background_task
def anotar_zona_horaria(tarea, user):
    zonas_vistas.append(timezone.get_current_timezone_name())
    tarea.completar()


class ZonaHorariaDelNegocioTests(NegocioTestCase):
    esquema = "zona"
    dominio = "zona.localhost"

    def cambiar_zona(self, zona):
        connection.set_schema_to_public()
        self.negocio.zona_horaria = zona
        self.negocio.save(update_fields=["zona_horaria"])
        connection.set_tenant(self.negocio)

    def peticion_del_negocio(self, negocio=None):
        request = RequestFactory().get("/")
        request.tenant = negocio or self.negocio
        return request

    def zona_dentro_del_middleware(self, negocio):
        request = self.peticion_del_negocio(negocio)
        middleware = BusinessTimeZoneMiddleware(
            lambda request: timezone.get_current_timezone_name()
        )
        return middleware(request)

    def test_activa_la_zona_del_negocio_solo_durante_la_peticion(self):
        self.cambiar_zona("Asia/Tokyo")
        self.assertEqual(self.zona_dentro_del_middleware(self.negocio), "Asia/Tokyo")
        self.assertEqual(timezone.get_current_timezone_name(), settings.TIME_ZONE)

    def test_fuera_de_un_negocio_usa_la_zona_del_proyecto(self):
        publico = get_tenant_model()(schema_name="public", zona_horaria="Asia/Tokyo")
        self.assertEqual(self.zona_dentro_del_middleware(publico), settings.TIME_ZONE)

    def test_el_calendario_abre_en_el_mes_del_negocio(self):
        meses = {}
        for zona in ("America/Santiago", "Asia/Tokyo"):
            self.cambiar_zona(zona)
            vista = CalendarView()
            vista.request = RequestFactory().get("/")
            vista.request.session = {}
            with mock.patch(
                "django.utils.timezone.now", return_value=FIN_DE_OCTUBRE_UTC
            ):
                meses[zona] = BusinessTimeZoneMiddleware(
                    lambda request: vista.get_initial_month()
                )(self.peticion_del_negocio())
        self.assertEqual(meses["America/Santiago"], f"{MONTH_NUMBER_TO_NAME[10]} 2026")
        self.assertEqual(meses["Asia/Tokyo"], f"{MONTH_NUMBER_TO_NAME[11]} 2026")

    def test_el_mes_por_defecto_de_los_filtros_sigue_la_zona_activa(self):
        with mock.patch("django.utils.timezone.now", return_value=FIN_DE_OCTUBRE_UTC):
            with timezone.override("America/Santiago"):
                desde_santiago, _ = CustomMonthField().to_python("")
            with timezone.override("Asia/Tokyo"):
                desde_tokio, _ = CustomMonthField().to_python("")
        self.assertEqual((desde_santiago.month, desde_santiago.day), (10, 1))
        self.assertEqual((desde_tokio.month, desde_tokio.day), (11, 1))

    def test_los_periodos_del_dashboard_terminan_en_el_mes_del_negocio(self):
        with mock.patch("django.utils.timezone.now", return_value=FIN_DE_OCTUBRE_UTC):
            with timezone.override("Asia/Tokyo"):
                self.assertEqual(last_n_months(1), [(2026, 11)])
            with timezone.override("America/Santiago"):
                self.assertEqual(last_n_months(1), [(2026, 10)])

    def test_las_tareas_de_fondo_corren_con_la_zona_del_negocio(self):
        self.cambiar_zona("Asia/Tokyo")
        with schema_context(self.esquema):
            usuario = User.objects.create_user(
                username="tareas", email="tareas@correo.cl"
            )
            tarea = TareaEnProceso.objects.create(
                nombre_proceso="Prueba", origen="prueba", user_id=usuario.id
            )
        zonas_vistas.clear()
        anotar_zona_horaria(self.esquema, tarea.pk)
        self.assertEqual(zonas_vistas, ["Asia/Tokyo"])
        self.assertEqual(timezone.get_current_timezone_name(), settings.TIME_ZONE)
