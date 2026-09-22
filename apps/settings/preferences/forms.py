from apps.settings.preferences.registry import PREFERENCES
from apps.settings.preferences.service import get_category_preferences, set_preference


def build_preference_fields(category, user=None) -> dict:
    values = get_category_preferences(category, user=user)
    return {
        definition.key: definition.form_field(values[definition.key])
        for definition in PREFERENCES.by_category(category)
    }


class PreferenceFieldsMixin:
    preference_category = None

    def add_preference_fields(self, user=None):
        self.preference_keys = []
        if not self.preference_category:
            return
        for key, field in build_preference_fields(
            self.preference_category, user=user
        ).items():
            self.fields[key] = field
            self.preference_keys.append(key)

    @property
    def preference_fields(self):
        return [self[key] for key in getattr(self, "preference_keys", [])]

    def save_preferences(self, user=None):
        for key in getattr(self, "preference_keys", []):
            set_preference(key, self.cleaned_data[key], user=user)
