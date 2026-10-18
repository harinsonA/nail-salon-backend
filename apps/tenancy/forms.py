from django import forms

from apps.tenancy.estados import estados_posibles


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
