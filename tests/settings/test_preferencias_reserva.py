from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.appointments.calendar.constants import (
    APPOINTMENT_PREFERENCE_FIELDS,
    CALENDAR_PREFERENCE_FIELDS,
)
from apps.settings.models import Preference
from apps.settings.preferences import (
    PREFERENCES,
    RESERVATION_AMOUNT,
    RESERVATION_DISCOUNTS_TOTAL,
    RESERVATION_ENABLED,
    RESERVATION_MODULE,
    Category,
    Scope,
)
from tests.base import NegocioTestCase

User = get_user_model()

RESERVA = (
    RESERVATION_MODULE,
    RESERVATION_ENABLED,
    RESERVATION_DISCOUNTS_TOTAL,
    RESERVATION_AMOUNT,
)


class PreferenciasReservaTests(NegocioTestCase):
    esquema = "preferencias_reserva"

    def test_sin_configurar_el_modulo_esta_apagado_y_el_valor_en_cero(self):
        self.assertIs(RESERVATION_MODULE.get(), False)
        self.assertIs(RESERVATION_ENABLED.get(), False)
        self.assertIs(RESERVATION_DISCOUNTS_TOTAL.get(), False)
        self.assertEqual(RESERVATION_AMOUNT.get(), 0)

    def test_guardan_y_vuelven_con_su_tipo(self):
        RESERVATION_MODULE.set(True)
        RESERVATION_ENABLED.set(True)
        RESERVATION_DISCOUNTS_TOTAL.set(True)
        RESERVATION_AMOUNT.set("5000")
        self.assertIs(RESERVATION_MODULE.is_enabled(), True)
        self.assertIs(RESERVATION_ENABLED.is_enabled(), True)
        self.assertIs(RESERVATION_DISCOUNTS_TOTAL.is_enabled(), True)
        self.assertEqual(RESERVATION_AMOUNT.get(), 5000)

    def test_volver_a_cero_actualiza_la_misma_fila(self):
        RESERVATION_AMOUNT.set(5000)
        RESERVATION_AMOUNT.set(0)
        self.assertEqual(RESERVATION_AMOUNT.get(), 0)
        self.assertEqual(Preference.objects.filter(key=RESERVATION_AMOUNT.key).count(), 1)

    def test_son_del_negocio_y_no_de_cada_usuario(self):
        ana = User.objects.create_user(username="ana", password="clave-de-prueba")
        camila = User.objects.create_user(username="camila", password="clave-de-prueba")
        for preference, value in zip(RESERVA, (True, True, True, 5000)):
            preference.set(value, user=ana)
            self.assertEqual(preference.get(user=camila), value)
            guardada = Preference.objects.get(key=preference.key)
            self.assertEqual(guardada.scope, Scope.NEGOCIO)
            self.assertEqual(guardada.scope_id, "")

    def test_el_valor_rechaza_negativos_y_montos_sobre_el_tope(self):
        for invalido in (-1, 100_000_000, "abc"):
            with self.assertRaises(ValidationError):
                RESERVATION_AMOUNT.set(invalido)
        self.assertFalse(Preference.objects.filter(key=RESERVATION_AMOUNT.key).exists())

    def test_el_modulo_se_activa_desde_la_base_para_todo_el_negocio(self):
        ana = User.objects.create_user(username="ana", password="clave-de-prueba")
        Preference.objects.create(
            scope=Scope.USER, scope_id=str(ana.pk), key=RESERVATION_MODULE.key, value=True
        )
        self.assertFalse(RESERVATION_MODULE.is_enabled(user=ana))
        Preference.objects.create(
            scope=Scope.NEGOCIO, scope_id="", key=RESERVATION_MODULE.key, value=True
        )
        self.assertTrue(RESERVATION_MODULE.is_enabled())
        self.assertTrue(RESERVATION_MODULE.is_enabled(user=ana))

    def test_el_modulo_es_una_funcion_nueva_y_no_entra_a_ningun_formulario(self):
        self.assertEqual(
            PREFERENCES.by_category(Category.FUNCIONES_NUEVAS), [RESERVATION_MODULE]
        )
        self.assertNotIn(RESERVATION_MODULE, CALENDAR_PREFERENCE_FIELDS)
        self.assertNotIn(RESERVATION_MODULE, APPOINTMENT_PREFERENCE_FIELDS)

    def test_cada_preferencia_de_agenda_esta_en_una_sola_lista(self):
        self.assertCountEqual(
            CALENDAR_PREFERENCE_FIELDS + APPOINTMENT_PREFERENCE_FIELDS,
            PREFERENCES.by_category(Category.AGENDA),
        )
