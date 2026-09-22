from apps.settings.preferences.constants import Category
from apps.settings.preferences.types import ChoicePreference


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


PREFERENCES = PreferenceRegistry(
    SESSION_IDLE_MINUTES,
)
