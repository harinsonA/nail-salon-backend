from django.urls import reverse_lazy

from apps.clients.imports import ClientAsyncImportValidator
from apps.clients.tasks import import_clients
from apps.common.imports.async_views import BaseAsyncImportView
from apps.common.imports.views import BaseExampleExportView


class ClientImportView(BaseAsyncImportView):
    title = "Importación de clientes"
    validator_class = ClientAsyncImportValidator
    view_url = reverse_lazy("client_import")
    example_export_url = reverse_lazy("client_example_export")
    back_url = reverse_lazy("clients")

    import_task = import_clients
    origin = "importacion_clientes"
    process_name = "Importación de clientes"


class ClientExampleExportView(BaseExampleExportView):
    validator_class = ClientAsyncImportValidator
    filename = "plantilla_clientes"
    example_rows = [
        [
            "María",
            "González",
            "+56912345678",
            "maria@ejemplo.cl",
            "activo",
            "Clienta frecuente",
        ],
    ]
