from apps.clients.imports import ClientAsyncImporter
from apps.tareas.decorators import background_task


@background_task
def import_clients(tarea, user):
    """Importa clientes desde el CSV que la vista dejó en la tarea.

    La encola ClientImportView al subir el archivo. Solo conecta la tarea con
    su importador: toda la lógica vive en ClientAsyncImporter.

    Args:
        tarea (TareaEnProceso): Fila de seguimiento, la inyecta el decorador
            a partir del id que viaja por Redis.
        user: Usuario que disparó la importación, lo inyecta el decorador.
    """
    ClientAsyncImporter(user=user, task=tarea).run()
