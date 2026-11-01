from django import forms

from apps.common.form_classes import FORM_CONTROL_CLASS
from apps.common.utils.currency import Money

"""========================================================================="""
# region ........ functions


class BasePickerWidget(forms.TextInput):
    def __init__(self, attrs=None, class_name="", placeholder=""):
        default_attrs = {
            "class": f"form-control {class_name}".strip(),
            "autocomplete": "off",
            "placeholder": placeholder,
        }
        if attrs:
            class_name = attrs.pop("class", None)
            if class_name:
                default_attrs["class"] += f" {class_name}"
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Inputs


def text_input(placeholder="", **attrs):
    return forms.TextInput(
        attrs={"class": FORM_CONTROL_CLASS, "placeholder": placeholder, **attrs}
    )


def password_input():
    return forms.PasswordInput(
        attrs={"class": FORM_CONTROL_CLASS, "autocomplete": "new-password"}
    )


def switch_input():
    return forms.CheckboxInput(attrs={"class": "form-check-input", "role": "switch"})


class MoneyInput(forms.TextInput):
    def __init__(self, attrs=None):
        super().__init__(
            attrs={
                "class": FORM_CONTROL_CLASS,
                "placeholder": "0",
                "inputmode": "numeric",
                "autocomplete": "off",
                "data-money": "",
                **(attrs or {}),
            }
        )

    def format_value(self, value):
        if isinstance(value, str):
            try:
                value = Money.parse(value)
            except ValueError:
                return value
        return Money.digits(value) if value else None


# endregion
"""========================================================================="""
"""========================================================================="""
# region ........ Dates


class DatePickerWidget(BasePickerWidget):
    def __init__(self, attrs=None):
        super().__init__(
            attrs=attrs,
            class_name="datepicker",
            placeholder="DD/MM/YYYY",
        )


class MonthPickerWidget(BasePickerWidget):
    def __init__(self, attrs=None):
        super().__init__(
            attrs=attrs,
            class_name="monthpicker",
            placeholder="Enero 2000",
        )


# endregion
"""========================================================================="""
