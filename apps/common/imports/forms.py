from django import forms
from django.template.defaultfilters import filesizeformat

from apps.common.form_classes import FORM_CONTROL_CLASS


class BaseImportForm(forms.Form):
    """Formulario común de importación. Valida SOLO el archivo (formato y peso).

    La validación del contenido de cada fila vive en el Validator de cada
    sección; este formulario es agnóstico al dominio.

    Args:
        is_async (bool): Si es True valida además que el archivo sea UTF-8 y
            deja el texto decodificado en cleaned_data["contenido"], listo
            para guardarse en la TareaEnProceso. Las vistas síncronas no lo
            activan: siguen recibiendo solo el archivo y ni siquiera pagan el
            costo de decodificar.
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

    def __init__(self, *args, is_async=False, **kwargs):
        self.is_async = is_async
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if not self.is_async:
            return cleaned_data

        archivo = cleaned_data.get("archivo")
        if not archivo:
            return cleaned_data

        archivo.seek(0)
        try:
            cleaned_data["contenido"] = archivo.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            self.add_error(
                "archivo",
                "El archivo debe estar codificado en UTF-8. "
                "Guárdalo como 'CSV UTF-8' y reintenta.",
            )
        return cleaned_data

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
