from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from apps.common.utils.phones import CountryPhonePrefix
from apps.tenancy.alta import dominio_de
from apps.tenancy.estados import estados_posibles
from apps.tenancy.models import Dominio, Negocio, Persona, PersonaTelefono, Rubro
from apps.tenancy.models.negocio import validar_zona_horaria
from apps.tenancy.subdominios import LARGO_MAXIMO, esquema_desde_subdominio


class AltaNegocioForm(forms.Form):
    nombre = forms.CharField(label="Nombre del negocio", max_length=150)
    subdominio = forms.CharField(
        label="Subdominio",
        max_length=LARGO_MAXIMO,
    )
    rubro = forms.ModelChoiceField(label="Rubro", queryset=Rubro.objects.filter(activo=True), required=False)
    zona_horaria = forms.CharField(
        label="Zona horaria",
        max_length=50,
        initial="America/Santiago",
        validators=[validar_zona_horaria],
    )
    titular = forms.ModelChoiceField(
        label="Titular existente",
        queryset=Persona.objects.all(),
        required=False,
        help_text="Déjalo vacío para registrar una persona nueva con los campos de abajo.",
    )
    nombres = forms.CharField(label="Nombres del titular", max_length=100, required=False)
    apellidos = forms.CharField(label="Apellidos del titular", max_length=100, required=False)
    codigo_pais = forms.ChoiceField(
        label="Código de país",
        choices=CountryPhonePrefix.choices,
        initial=CountryPhonePrefix.CHILE,
        required=False,
    )
    telefono = forms.CharField(label="Teléfono móvil del titular", max_length=15, required=False)
    correo = forms.EmailField(
        label="Correo de acceso del propietario",
        help_text="Con este correo entra a su negocio. Se guarda también en la ficha del titular.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["subdominio"].help_text = (
            f"Minúsculas, números y guiones. Será la dirección del negocio: subdominio.{settings.DOMINIO_BASE}"
        )

    def clean_subdominio(self):
        subdominio = self.cleaned_data["subdominio"].strip().lower()
        esquema = esquema_desde_subdominio(subdominio)
        tomado = (
            Negocio.objects.filter(schema_name=esquema).exists()
            or Dominio.objects.filter(domain=dominio_de(subdominio)).exists()
        )
        if tomado:
            raise ValidationError("Ese subdominio ya lo usa otro negocio.")
        return subdominio

    def clean_correo(self):
        return self.cleaned_data["correo"].strip().lower()

    def clean(self):
        datos = super().clean()
        if not datos.get("titular") and not datos.get("nombres"):
            self.add_error("nombres", "Elige un titular existente o escribe los nombres del nuevo.")
        if datos.get("telefono") and not datos.get("titular"):
            telefono = PersonaTelefono(codigo_pais=datos.get("codigo_pais"), numero=datos["telefono"])
            try:
                telefono.full_clean(exclude=["persona"], validate_unique=False, validate_constraints=False)
            except ValidationError as error:
                for mensaje in error.message_dict.get("numero", []) + error.message_dict.get("codigo_pais", []):
                    self.add_error("telefono", mensaje)
        return datos


class CambiarEstadoForm(forms.Form):
    estado = forms.ChoiceField(label="Nuevo estado")
    motivo = forms.CharField(
        label="Motivo",
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text="Queda en el historial del negocio: por ejemplo, «dos meses sin pago».",
    )

    def __init__(self, negocio, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.negocio = negocio
        self.fields["estado"].choices = [(estado.value, estado.label) for estado in estados_posibles(negocio)]


class RestablecerClavePropietarioForm(forms.Form):
    identidad_confirmada = forms.BooleanField(
        label="Confirmé la identidad del titular",
        help_text="Por ejemplo, llamándolo a su teléfono registrado antes de entregarle la clave.",
    )
