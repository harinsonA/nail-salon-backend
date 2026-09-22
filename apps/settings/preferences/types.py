from django import forms
from django.core.exceptions import ValidationError

from apps.settings.preferences.constants import Category, Scope


class BasePreference:
    def __init__(
        self,
        key,
        label,
        default,
        category=Category.SEGURIDAD,
        help_text="",
        scope=Scope.USER,
    ):
        self.key = key
        self.label = label
        self.default = default
        self.category = category
        self.help_text = help_text
        self.scope = scope

    def __str__(self):
        return self.key

    def __repr__(self):
        return f"<{type(self).__name__}: {self.key}>"

    def clean(self, value):
        return value

    def serialize(self, value):
        return value

    def deserialize(self, value):
        return value

    def form_field(self, value):
        raise NotImplementedError

    def get(self, user=None):
        from apps.settings.preferences.service import get_preference

        return get_preference(self, user=user)

    def set(self, value, user=None):
        from apps.settings.preferences.service import set_preference

        return set_preference(self, value, user=user)


class BooleanPreference(BasePreference):
    TRUE_VALUES = {"true", "on", "1", "si", "sí"}

    def clean(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.strip().lower() in self.TRUE_VALUES
        return bool(value)

    def is_enabled(self, user=None) -> bool:
        return self.get(user=user) is True

    def form_field(self, value):
        return forms.BooleanField(
            label=self.label,
            help_text=self.help_text,
            required=False,
            initial=value,
            widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        )


class IntegerPreference(BasePreference):
    def __init__(self, *args, min_value=None, max_value=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_value = min_value
        self.max_value = max_value

    def clean(self, value):
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValidationError("Debes indicar un número entero.")
        if self.min_value is not None and value < self.min_value:
            raise ValidationError(f"El valor mínimo es {self.min_value}.")
        if self.max_value is not None and value > self.max_value:
            raise ValidationError(f"El valor máximo es {self.max_value}.")
        return value

    def form_field(self, value):
        return forms.IntegerField(
            label=self.label,
            help_text=self.help_text,
            initial=value,
            min_value=self.min_value,
            max_value=self.max_value,
            widget=forms.NumberInput(attrs={"class": "form-control"}),
        )


class ChoicePreference(BasePreference):
    def __init__(self, *args, choices=(), coerce=str, **kwargs):
        super().__init__(*args, **kwargs)
        self.choices = tuple(choices)
        self.coerce = coerce

    @property
    def valid_values(self):
        return [value for value, _ in self.choices]

    def clean(self, value):
        try:
            value = self.coerce(value)
        except (TypeError, ValueError):
            raise ValidationError("Escoge una opción válida.")
        if value not in self.valid_values:
            raise ValidationError("Escoge una opción válida.")
        return value

    def form_field(self, value):
        return forms.TypedChoiceField(
            label=self.label,
            help_text=self.help_text,
            choices=self.choices,
            coerce=self.coerce,
            initial=value,
            widget=forms.Select(attrs={"class": "form-select"}),
        )


class TextPreference(BasePreference):
    def __init__(self, *args, max_length=255, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_length = max_length

    def clean(self, value):
        value = "" if value is None else str(value).strip()
        if len(value) > self.max_length:
            raise ValidationError(f"El texto no puede superar {self.max_length} caracteres.")
        return value

    def form_field(self, value):
        return forms.CharField(
            label=self.label,
            help_text=self.help_text,
            required=False,
            initial=value,
            max_length=self.max_length,
            widget=forms.TextInput(attrs={"class": "form-control"}),
        )


class JsonPreference(BasePreference):
    def clean(self, value):
        if not isinstance(value, (list, dict)):
            raise ValidationError("El valor debe ser una lista o un diccionario.")
        return value

    def form_field(self, value):
        return forms.JSONField(
            label=self.label,
            help_text=self.help_text,
            required=False,
            initial=value,
            widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        )
