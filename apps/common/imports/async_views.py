from django.contrib import messages
from django.shortcuts import redirect

from apps.tareas.models import TareaEnProceso

from .views import BaseImportView


class BaseAsyncImportView(BaseImportView):
    """Vista base de importación ASÍNCRONA (Celery).

    Hereda de BaseImportView el formulario, el template y el contexto (título,
    encabezados esperados, plantilla descargable). La validación superficial
    (extensión .csv, no vacío, peso máximo y codificación UTF-8) la hace
    BaseImportForm con is_async=True, que además deja el texto en
    cleaned_data["contenido"]. Aquí NO se valida el contenido de las filas ni
    se persiste nada: eso ocurre dentro del worker. Esta vista solo registra
    la TareaEnProceso y encola.

    Los atributos model, batch_size y error_template_name dejan de usarse
    (persistencia y errores son del worker), pero no estorban.

    Attributes:
        import_task: Tarea @background_task de la entidad. Obligatoria.
        origin (str): Slug del proceso, p. ej. "importacion_clientes".
        process_name (str): Nombre visible en la vista /procesos/.
    """

    import_task = None
    origin = ""
    process_name = ""

    def get_form_kwargs(self):
        """Activa el modo asíncrono del formulario.

        Returns:
            dict: Los kwargs de BaseImportView más is_async=True, que hace que
                BaseImportForm valide UTF-8 y exponga cleaned_data["contenido"].
        """
        kwargs = super().get_form_kwargs()
        kwargs["is_async"] = True
        return kwargs

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
