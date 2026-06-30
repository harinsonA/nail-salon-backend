from django import forms
from django.template.defaultfilters import filesizeformat

from apps.common.form_classes import FORM_CONTROL_CLASS


class BaseImportForm(forms.Form):
    """Formulario común de importación. Valida SOLO el archivo (formato y peso).

    La validación del contenido de cada fila vive en el Validator de cada
    sección; este formulario es agnóstico al dominio.
    """

    ALLOWED_EXTENSIONS = (".csv",)
    MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5 MB (ajustable)

    archivo = forms.FileField(
        label="Archivo",
        help_text="Solo archivos .csv en UTF-8",
        widget=forms.ClearableFileInput(
            attrs={"class": FORM_CONTROL_CLASS, "accept": ".csv"}
        ),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        nombre = archivo.name.lower()
        if not nombre.endswith(self.ALLOWED_EXTENSIONS):
            raise forms.ValidationError("Formato no permitido. Sube un archivo .csv")
        if archivo.size == 0:
            raise forms.ValidationError("El archivo está vacío.")
        if archivo.size > self.MAX_UPLOAD_SIZE:
            raise forms.ValidationError(
                f"El archivo supera el máximo permitido "
                f"({filesizeformat(self.MAX_UPLOAD_SIZE)})."
            )
        return archivo
