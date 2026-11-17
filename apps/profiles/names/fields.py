from django import forms

from apps.common.form_classes import FORM_CONTROL_CLASS
from apps.common.form_fields import AlphabeticField

NAME_MAX_LENGTH = 150


class PersonNameFields:
    FIRST_NAME_REQUIRED = "Escribe el nombre."
    LAST_NAME_REQUIRED = "Escribe el apellido."

    @classmethod
    def first_name(cls, placeholder="Nombre"):
        return cls.field("Nombre", cls.FIRST_NAME_REQUIRED, placeholder)

    @classmethod
    def last_name(cls, placeholder="Apellido"):
        return cls.field("Apellido", cls.LAST_NAME_REQUIRED, placeholder)

    @staticmethod
    def field(label, required_message, placeholder):
        return AlphabeticField(
            label=label,
            max_length=NAME_MAX_LENGTH,
            error_messages={"required": required_message},
            widget=forms.TextInput(attrs={"class": FORM_CONTROL_CLASS, "placeholder": placeholder}),
        )
