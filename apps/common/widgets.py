from django import forms


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
