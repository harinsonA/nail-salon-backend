from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from model_utils.models import TimeStampedModel

from apps.common.historial import HistorialRecords
from apps.common.models.con_principal import ConPrincipal

codigo_pais_iso = RegexValidator(r"^[A-Z]{2}$", "Usa el código de país de dos letras en mayúscula (CL, PE, CO).")


class DireccionBase(TimeStampedModel, ConPrincipal):
    etiqueta = models.CharField(max_length=30, blank=True, default="")
    calle = models.CharField(max_length=150)
    numero = models.CharField(max_length=15, blank=True, default="")
    complemento = models.CharField(max_length=60, blank=True, default="")
    comuna = models.CharField(max_length=80, blank=True, default="")
    ciudad = models.CharField(max_length=80, blank=True, default="")
    region = models.CharField(max_length=80, blank=True, default="")
    pais = models.CharField(max_length=2, default="CL", validators=[codigo_pais_iso])
    codigo_postal = models.CharField(max_length=12, blank=True, default="")
    referencia = models.CharField(max_length=150, blank=True, default="")
    latitud = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitud = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )

    history = HistorialRecords(inherit=True)

    class Meta:
        abstract = True

    @staticmethod
    def restricciones(campo_dueno):
        return [
            ConPrincipal.restriccion_principal(campo_dueno),
            models.CheckConstraint(
                condition=models.Q(latitud__isnull=True, longitud__isnull=True)
                | models.Q(latitud__isnull=False, longitud__isnull=False),
                name="%(app_label)s_%(class)s_coordenadas_completas",
            ),
        ]

    def __str__(self):
        return " ".join(parte for parte in (self.calle, self.numero) if parte)
