from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from model_utils.models import TimeStampedModel

from apps.common.historial import HistorialRecords
from apps.common.models.con_principal import ConPrincipal
from apps.common.utils.phones import CountryPhonePrefix, PhoneCleaner

solo_digitos = RegexValidator(r"^\d+$", "El número solo debe contener dígitos.")


class TelefonoBase(TimeStampedModel, ConPrincipal):
    class Tipo(models.TextChoices):
        MOVIL = "movil", "Móvil"
        FIJO = "fijo", "Fijo"

    codigo_pais = models.CharField(
        max_length=8,
        choices=CountryPhonePrefix.choices,
        default=CountryPhonePrefix.CHILE,
    )
    numero = models.CharField(max_length=15, validators=[solo_digitos])
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.MOVIL)
    tiene_whatsapp = models.BooleanField(default=False)
    etiqueta = models.CharField(max_length=30, blank=True, default="")

    history = HistorialRecords(inherit=True)

    class Meta:
        abstract = True

    @staticmethod
    def restricciones(campo_dueno):
        return [
            models.UniqueConstraint(
                fields=[campo_dueno, "codigo_pais", "numero"],
                name="%(app_label)s_%(class)s_numero_unico",
            ),
            ConPrincipal.restriccion_principal(campo_dueno),
        ]

    def __str__(self):
        return f"{self.codigo_pais} {self.numero}"

    def clean(self):
        super().clean()
        if self.tipo != self.Tipo.MOVIL or not self.numero:
            return
        resultado = PhoneCleaner(self.codigo_pais).is_valid(self.numero)
        if resultado.is_err():
            raise ValidationError({"numero": resultado.err_value})
