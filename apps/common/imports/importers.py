from simple_history.utils import bulk_create_with_history

from apps.tareas.models import TareaEnProceso


class BaseAsyncImporter:
    """Esqueleto de una importación asíncrona. Corre dentro del worker.

    Orquesta el proceso completo: valida el contenido de la tarea con el
    validator_class de la entidad, persiste con bulk_create_with_history y
    reporta el avance. Es todo-o-nada: si alguna fila tiene errores no se
    importa nada y la tarea queda FALLIDO con el detalle en
    resultado_metadata["errors"].

    Cada entidad declara su subclase con lo mínimo:

        class ClientAsyncImporter(BaseAsyncImporter):
            validator_class = ClientAsyncImportValidator
            model = Cliente
            success_message = "{count} clientes importados correctamente."

    Attributes:
        validator_class: Subclase de BaseAsyncImportValidator de la entidad.
            Obligatoria.
        model: Modelo destino de la importación. Obligatorio.
        batch_size (int): Filas por lote al persistir. Marca también cada
            cuánto se actualiza la barra de progreso.
        max_stored_errors (int): Tope de errores que se persisten en la
            metadata de la tarea; el total real queda en total_errors.
        success_message (str): Plantilla del mensaje final; recibe {count}.
            Cada entidad la redefine para respetar el género del sustantivo
            ("clientes importados" / "categorías importadas").
        user: Usuario que disparó la importación; queda como autor en el
            historial de simple_history.
        task (TareaEnProceso): Fila de seguimiento que se va actualizando.
        validator (BaseAsyncImportValidator): Instancia del validator; None
            hasta que run() la crea. Tras validate() expone rows_ok,
            rows_error y errors.
        validation_result (Result): Resultado de validate(); None hasta que
            run() lo ejecuta.
    """

    validator_class = None
    model = None
    batch_size = 10
    max_stored_errors = 200
    success_message = "{count} registros importados correctamente."

    def __init__(self, user, task: TareaEnProceso):
        if self.validator_class is None or self.model is None:
            raise NotImplementedError(
                f"{type(self).__name__} debe definir 'validator_class' y 'model'."
            )
        self.user = user
        self.task = task
        self.validator = None
        self.validation_result = None

    def _must_stop(self):
        """Corta la importación si la validación dejó errores.

        Persiste en resultado_metadata la muestra de errores (acotada a
        max_stored_errors), el total real y el resumen por filas, para que el
        detalle del proceso pueda pintarlos.

        Returns:
            bool: True si hubo errores, en cuyo caso la tarea ya quedó
                marcada como FALLIDO. False si se puede continuar.
        """
        if self.validation_result.is_ok():
            return False

        errors = self.validation_result.value
        total_errors = len(errors)
        error_detail = (
            f"{self.validator.rows_error} fila(s) con error "
            f"({total_errors} error(es) en total): no se importó nada."
        )
        if total_errors > self.max_stored_errors:
            error_detail += f" Mostrando los primeros {self.max_stored_errors}."

        self.task.fallar(
            error=error_detail,
            errors=errors[: self.max_stored_errors],
            total_errors=total_errors,
            rows_ok=self.validator.rows_ok,
            rows_error=self.validator.rows_error,
        )
        return True

    def save(self, data: list) -> int:
        """Persiste por lotes, reportando el avance después de cada uno.

        Las entidades importables son auditadas (simple_history) y
        bulk_create normal NO crea los registros históricos: se usa
        bulk_create_with_history con el usuario que disparó la importación.

        Cada lote es su propia transacción, a propósito: envolver todo en un
        único atomic dejaría las escrituras de progreso sin commitear hasta el
        final, y la barra no se movería. La contrapartida es que un fallo a
        mitad deja insertados los lotes anteriores.

        Args:
            data (list[dict]): Filas limpias a persistir.

        Returns:
            int: Cantidad de registros creados.
        """
        saved = 0
        for start in range(0, len(data), self.batch_size):
            objects = [
                self.model(**item) for item in data[start : start + self.batch_size]
            ]
            bulk_create_with_history(
                objects,
                self.model,
                batch_size=self.batch_size,
                default_user=self.user,
            )
            saved += len(objects)
            self.task.avanzar(saved)
        return saved

    def run(self):
        """Ejecuta la importación completa y deja la tarea en su estado final.

        Valida todas las filas antes de guardar nada. Si alguna falla, la
        tarea queda FALLIDO con los errores en resultado_metadata["errors"]
        y no se inserta ningún registro. Si todas pasan, guarda por lotes
        moviendo la barra de progreso y cierra la tarea como COMPLETADO.
        """
        self.validator = self.validator_class(task=self.task)
        self.validation_result = self.validator.validate()
        if self._must_stop():
            return

        cleaned_data = self.validation_result.value
        total = len(cleaned_data)
        self.task.iniciar(total=total)
        self.task.avanzar(max(1, total // 100))

        saved = self.save(cleaned_data)
        self.task.completar(mensaje=self.success_message.format(count=saved))
