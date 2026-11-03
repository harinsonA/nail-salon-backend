from apps.settings.preferences.registry import PREFERENCES
from apps.settings.preferences.service import get_preferences, set_preference


def build_preference_fields(definitions, user=None) -> dict:
    values = get_preferences([definition.key for definition in definitions], user=user)
    return {
        definition.key: definition.form_field(values[definition.key])
        for definition in definitions
    }


class PreferenceFieldsMixin:
    preference_category = None
    preference_definitions = None

    def get_preference_definitions(self):
        if self.preference_definitions is not None:
            return self.preference_definitions
        if self.preference_category:
            return PREFERENCES.by_category(self.preference_category)
        return ()

    def add_preference_fields(self, user=None):
        self.preference_keys = []
        for key, field in build_preference_fields(
            self.get_preference_definitions(), user=user
        ).items():
            self.fields[key] = field
            self.preference_keys.append(key)

    @property
    def preference_fields(self):
        return [self[key] for key in getattr(self, "preference_keys", [])]

    def save_preferences(self, user=None):
        for key in getattr(self, "preference_keys", []):
            set_preference(key, self.cleaned_data[key], user=user)
