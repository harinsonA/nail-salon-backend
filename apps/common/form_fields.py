from django import forms

from apps.common.utils.utils import CommonCleaner

"""========================================================================="""
# region ........ Constants


NOTE_MAX_LENGTH = 250


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


class NoteField(CleanedCharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", NOTE_MAX_LENGTH)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        return forms.CharField.to_python(self, value)

    def check(self, field_name, value):
        return CommonCleaner.clean_250_characters_field(field_name, value)


# endregion
"""========================================================================="""
