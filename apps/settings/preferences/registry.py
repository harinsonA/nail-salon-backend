from apps.payments.choices import MetodoPago
from apps.settings.preferences.constants import Category, Scope
from apps.settings.preferences.types import (
    BooleanPreference,
    ChoicePreference,
    IntegerPreference,
)


class PreferenceRegistry:
    def __init__(self, *definitions):
        self._definitions = {definition.key: definition for definition in definitions}

    def __iter__(self):
        return iter(self._definitions.values())

    def __contains__(self, key):
        return str(key) in self._definitions

    def __len__(self):
        return len(self._definitions)

    def get(self, key):
        try:
            return self._definitions[str(key)]
        except KeyError:
            raise KeyError(f"La preferencia '{key}' no está definida en el registro.")

    def by_category(self, category):
        return [
            definition for definition in self if definition.category == category
        ]


SESSION_IDLE_MINUTES = ChoicePreference(
    key="session_idle_minutes",
    label="Cerrar sesión por inactividad",
    help_text=(
        "Tiempo sin usar la agenda antes de pedirte la contraseña otra vez. "
        "La sesión se cierra igualmente al cerrar el navegador y cada madrugada."
    ),
    default=120,
    coerce=int,
    choices=(
        (15, "15 minutos"),
        (30, "30 minutos"),
        (60, "1 hora"),
        (120, "2 horas"),
        (240, "4 horas"),
        (0, "No cerrar por inactividad"),
    ),
    category=Category.SEGURIDAD,
)


CALENDAR_DEFAULT_VIEW = ChoicePreference(
    key="calendario_vista_inicial",
    label="Vista al ingresar",
    help_text="El calendario se abre en esta vista cada vez que entras.",
    default="mes",
    choices=(
        ("dia", "Día"),
        ("semana", "Semana"),
        ("mes", "Mes"),
    ),
    category=Category.AGENDA,
)


CALENDAR_SHOW_PENDING = BooleanPreference(
    key="calendario_ver_pendientes",
    label="Pendientes",
    default=True,
    category=Category.AGENDA,
)


CALENDAR_SHOW_COMPLETED = BooleanPreference(
    key="calendario_ver_completadas",
    label="Completadas",
    default=True,
    category=Category.AGENDA,
)


CALENDAR_SHOW_CANCELLED = BooleanPreference(
    key="calendario_ver_canceladas",
    label="Canceladas",
    default=True,
    category=Category.AGENDA,
)


CALENDAR_SHOW_DEBT = BooleanPreference(
    key="calendario_aviso_saldo",
    label="Mostrar saldo pendiente",
    default=True,
    category=Category.AGENDA,
)


RESERVATION_ENABLED = BooleanPreference(
    key="reserva_habilitada",
    label="Incluir reserva en las citas",
    default=False,
    category=Category.AGENDA,
    scope=Scope.NEGOCIO,
)


RESERVATION_DISCOUNTS_TOTAL = BooleanPreference(
    key="reserva_descuenta_total",
    label="Descontar la reserva del total",
    default=False,
    category=Category.AGENDA,
    scope=Scope.NEGOCIO,
)


RESERVATION_AMOUNT = IntegerPreference(
    key="valor_reserva",
    label="Valor de la reserva",
    default=0,
    min_value=0,
    max_value=99_999_999,
    category=Category.AGENDA,
    scope=Scope.NEGOCIO,
)


RESERVATION_PAYMENT_METHOD = ChoicePreference(
    key="reserva_metodo_pago",
    label="Método de pago de la reserva",
    default=MetodoPago.EFECTIVO,
    choices=MetodoPago.CHOICES,
    category=Category.AGENDA,
    scope=Scope.NEGOCIO,
)


PREFERENCES = PreferenceRegistry(
    SESSION_IDLE_MINUTES,
    CALENDAR_DEFAULT_VIEW,
    CALENDAR_SHOW_PENDING,
    CALENDAR_SHOW_COMPLETED,
    CALENDAR_SHOW_CANCELLED,
    CALENDAR_SHOW_DEBT,
    RESERVATION_ENABLED,
    RESERVATION_DISCOUNTS_TOTAL,
    RESERVATION_AMOUNT,
    RESERVATION_PAYMENT_METHOD,
)
