from apps.services.imports import CategoryAsyncImporter, ServiceAsyncImporter
from apps.tareas.decorators import background_task


@background_task
def import_services(tarea, user):
    """Importa servicios desde el CSV que la vista dejó en la tarea.

    La encola ServiceImportView al subir el archivo. Solo conecta la tarea con
    su importador: toda la lógica vive en ServiceAsyncImporter.

    Args:
        tarea (TareaEnProceso): Fila de seguimiento, la inyecta el decorador
            a partir del id que viaja por Redis.
        user: Usuario que disparó la importación, lo inyecta el decorador.
    """
    ServiceAsyncImporter(user=user, task=tarea).run()


@background_task
def import_categories(tarea, user):
    """Importa categorías desde el CSV que la vista dejó en la tarea.

    La encola CategoryImportView al subir el archivo. Solo conecta la tarea con
    su importador: toda la lógica vive en CategoryAsyncImporter.

    Args:
        tarea (TareaEnProceso): Fila de seguimiento, la inyecta el decorador
            a partir del id que viaja por Redis.
        user: Usuario que disparó la importación, lo inyecta el decorador.
    """
    CategoryAsyncImporter(user=user, task=tarea).run()
