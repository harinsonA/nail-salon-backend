from django.contrib.auth import get_user_model
from django.db import connection

from apps.settings.models import Preference
from apps.settings.preferences import ADVANCE_MODULE, PREFERENCES, Category, Scope
from tests.base import NegocioTestCase

User = get_user_model()


class PreferenciaAnticiposTests(NegocioTestCase):
    def test_sin_fila_queda_apagada(self):
        self.assertFalse(ADVANCE_MODULE.is_enabled())

    def test_la_fila_del_negocio_la_activa_para_todo_el_equipo(self):
        Preference.objects.create(scope=Scope.NEGOCIO, scope_id="", key="advance_module", value=True)
        usuario = User.objects.create_user(username="ana", email="ana@correo.cl")
        self.assertTrue(ADVANCE_MODULE.is_enabled())
        self.assertTrue(ADVANCE_MODULE.is_enabled(user=usuario))

    def test_con_valor_falso_queda_apagada(self):
        Preference.objects.create(scope=Scope.NEGOCIO, scope_id="", key="advance_module", value=False)
        self.assertFalse(ADVANCE_MODULE.is_enabled())

    def test_una_fila_de_usuario_no_la_activa(self):
        usuario = User.objects.create_user(username="ana", email="ana@correo.cl")
        Preference.objects.create(scope=Scope.USER, scope_id=str(usuario.pk), key="advance_module", value=True)
        self.assertFalse(ADVANCE_MODULE.is_enabled(user=usuario))

    def test_fuera_de_un_negocio_queda_apagada(self):
        Preference.objects.create(scope=Scope.NEGOCIO, scope_id="", key="advance_module", value=True)
        connection.set_schema_to_public()
        self.assertFalse(ADVANCE_MODULE.is_enabled())

    def test_ningun_formulario_la_muestra(self):
        for category, _ in Category.CHOICES:
            if category != Category.FUNCIONES_NUEVAS:
                self.assertNotIn(ADVANCE_MODULE, PREFERENCES.by_category(category))
        self.assertEqual(PREFERENCES.by_category(Category.FUNCIONES_NUEVAS), [ADVANCE_MODULE])
