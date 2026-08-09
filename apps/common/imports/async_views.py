from django.contrib import messages
from django.shortcuts import redirect
from django.views.generic import FormView

from apps.common.views.base_views import ProtectedView
from apps.tareas.models import TareaEnProceso

from .forms import BaseImportForm


class BaseAsyncImportView(ProtectedView, FormView):
    """Vista base de importación asíncrona (Celery). Página normal, no modal.

    La validación superficial (extensión .csv, no vacío, peso máximo y
    codificación UTF-8) la hace BaseImportForm, que además deja el texto en
    cleaned_data["contenido"]. Aquí NO se valida el contenido de las filas ni
    se persiste nada: eso ocurre dentro del worker. Esta vista solo registra
    la TareaEnProceso y encola.

    Attributes:
        title (str): Título de la página.
        validator_class: Validator de la entidad. Solo se usa para pintar los
            encabezados esperados en el formulario; quien lo ejecuta es el
            importador, dentro del worker.
        view_url: URL de esta misma vista (destino del form).
        example_export_url: URL de la plantilla descargable.
        back_url: URL del listado de la sección (botón "Volver").
        import_task: Tarea @background_task de la entidad. Obligatoria.
        origin (str): Slug del proceso, p. ej. "importacion_clientes".
        process_name (str): Nombre visible en la vista /procesos/.
    """

    template_name = "common/imports/import_form.html"
    form_class = BaseImportForm

    title = "Importación"
    validator_class = None
    view_url = None
    example_export_url = None
    back_url = None

    import_task = None
    origin = ""
    process_name = ""

    def get_context_data(self, **kwargs):
        """Agrega al contexto lo que necesita import_form.html.

        Returns:
            dict: El contexto con título, urls y los encabezados esperados.
        """
        context = super().get_context_data(**kwargs)
        context["import_title"] = self.title
        context["view_url"] = self.view_url
        context["example_export_url"] = self.example_export_url
        context["back_url"] = self.back_url
        if self.validator_class:
            context["import_fields"] = self.validator_class.get_headers()
        return context

    def form_valid(self, form):
        """Registra la tarea, la encola y redirige al monitor de procesos.

        Args:
            form (BaseImportForm): Formulario ya validado, con el texto del
                CSV en cleaned_data["contenido"].

        Returns:
            HttpResponseRedirect: Redirección a /procesos/ con un mensaje.
        """
        tarea = TareaEnProceso.objects.create(
            nombre_proceso=self.process_name,
            origen=self.origin,
            user_id=self.request.user.id,
            datos_entrada={"contenido": form.cleaned_data["contenido"]},
        )

        resultado = self.import_task.delay(tarea.id)
        tarea.celery_task_id = resultado.id
        tarea.save(update_fields=["celery_task_id", "modified"])

        messages.success(self.request, f"{self.process_name} iniciada.")
        return redirect("tasks")
