from django.contrib.auth import get_user_model
from django.db import connection

from apps.settings.models import Preference
from apps.settings.preferences import CALENDAR_V2, PREFERENCES, Category, Scope
from tests.base import NegocioTestCase

User = get_user_model()


class PreferenciaCalendarioV2Tests(NegocioTestCase):
    def test_sin_fila_queda_apagada(self):
        self.assertFalse(CALENDAR_V2.is_enabled())

    def test_la_fila_del_negocio_la_activa_para_todo_el_equipo(self):
        Preference.objects.create(scope=Scope.NEGOCIO, scope_id="", key="calendario_v2", value=True)
        usuario = User.objects.create_user(username="ana", email="ana@correo.cl")
        self.assertTrue(CALENDAR_V2.is_enabled())
        self.assertTrue(CALENDAR_V2.is_enabled(user=usuario))

    def test_con_valor_falso_queda_apagada(self):
        Preference.objects.create(scope=Scope.NEGOCIO, scope_id="", key="calendario_v2", value=False)
        self.assertFalse(CALENDAR_V2.is_enabled())

    def test_una_fila_de_usuario_no_la_activa(self):
        usuario = User.objects.create_user(username="ana", email="ana@correo.cl")
        Preference.objects.create(scope=Scope.USER, scope_id=str(usuario.pk), key="calendario_v2", value=True)
        self.assertFalse(CALENDAR_V2.is_enabled(user=usuario))

    def test_fuera_de_un_negocio_queda_apagada(self):
        Preference.objects.create(scope=Scope.NEGOCIO, scope_id="", key="calendario_v2", value=True)
        connection.set_schema_to_public()
        self.assertFalse(CALENDAR_V2.is_enabled())

    def test_no_aparece_en_el_modal_de_perfil(self):
        self.assertNotIn(CALENDAR_V2, PREFERENCES.by_category(Category.SEGURIDAD))
        self.assertEqual(PREFERENCES.by_category(Category.FUNCIONES_NUEVAS), [CALENDAR_V2])
