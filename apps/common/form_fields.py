from django import forms

from apps.common.utils.currency import Money
from apps.common.utils.utils import CommonCleaner
from apps.common.widgets import MoneyInput

"""========================================================================="""
# region ........ Constants


NOTE_MAX_LENGTH = 250
MONEY_INVALID = "El campo '{name}' debe ser un monto en pesos, sin decimales."
MONEY_NEGATIVE = "El campo '{name}' no puede ser negativo."
MONEY_TOO_LARGE = "El campo '{name}' no puede superar {limit}."


# endregion
"""========================================================================="""

"""========================================================================="""
# region ........ Fields


class CleanedCharField(forms.CharField):
    def __init__(self, *args, allow_dots=False, **kwargs):
        self.allow_dots = allow_dots
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        return " ".join(super().to_python(value).split())

    def validate(self, value):
        super().validate(value)
        if value in self.empty_values:
            return
        result = self.check(self.error_name(), value)
        if result.is_err():
            raise forms.ValidationError(result.value)

    def error_name(self):
        return (self.label or "").lower()

    def check(self, field_name, value):
        raise NotImplementedError


class AlphabeticField(CleanedCharField):
    def check(self, field_name, value):
        return CommonCleaner.clean_alphabetic_field(field_name, value, allow_dots=self.allow_dots)


class AlphanumericField(CleanedCharField):
    def check(self, field_name, value):
        return CommonCleaner.clean_alphanumeric_field(field_name, value, allow_dots=self.allow_dots)


class NumericField(CleanedCharField):
    def check(self, field_name, value):
        return CommonCleaner.clean_numeric_field(field_name, value)


class LowercaseCodeField(CleanedCharField):
    def to_python(self, value):
        return super().to_python(value).lower()


class SubdomainField(LowercaseCodeField):
    def check(self, field_name, value):
        return CommonCleaner.clean_subdomain_field(value)


class SchemaField(LowercaseCodeField):
    def check(self, field_name, value):
        return CommonCleaner.clean_schema_field(value)


class NoteField(CleanedCharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", NOTE_MAX_LENGTH)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        return forms.CharField.to_python(self, value)

    def check(self, field_name, value):
        return CommonCleaner.clean_250_characters_field(field_name, value)


class MoneyField(forms.IntegerField):
    widget = MoneyInput

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("min_value", 0)
        super().__init__(*args, **kwargs)
        if self.max_value is not None:
            self.error_messages["max_value"] = MONEY_TOO_LARGE.format(
                name=(self.label or "").lower(), limit=Money.format(self.max_value)
            )

    def to_python(self, value):
        if value in self.empty_values:
            return None
        name = (self.label or "").lower()
        if str(value).strip().startswith("-"):
            raise forms.ValidationError(MONEY_NEGATIVE.format(name=name), code="min_value")
        try:
            return Money.parse(value)
        except ValueError:
            raise forms.ValidationError(MONEY_INVALID.format(name=name), code="invalid")


# endregion
"""========================================================================="""
