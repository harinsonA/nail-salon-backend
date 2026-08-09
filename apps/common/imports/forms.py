from django import forms
from django.template.defaultfilters import filesizeformat

from apps.common.form_classes import FORM_CONTROL_CLASS


class BaseImportForm(forms.Form):
    """Formulario común de importación. Valida SOLO el archivo.

    Comprueba extensión, que no esté vacío, el peso máximo y que sea UTF-8, y
    deja el texto decodificado en cleaned_data["contenido"] listo para
    guardarse en la TareaEnProceso. La validación del contenido de cada fila
    vive en el Validator de cada sección; este formulario es agnóstico al
    dominio.
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

    def clean(self):
        cleaned_data = super().clean()
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
