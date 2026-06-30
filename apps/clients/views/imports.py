from django.db import transaction
from django.urls import reverse_lazy
from simple_history.utils import bulk_create_with_history

from apps.common.imports.views import BaseImportView, BaseExampleExportView
from apps.clients.imports import ClientImportValidator
from apps.clients.models.cliente import Cliente


class ClientImportView(BaseImportView):
    title = "Importación de clientes"
    validator_class = ClientImportValidator
    model = Cliente
    view_url = reverse_lazy("client_import")
    example_export_url = reverse_lazy("client_example_export")
    success_url = reverse_lazy("clients")

    @transaction.atomic
    def save(self, data: list) -> int:
        """Override: Cliente es auditado (simple_history) y ``bulk_create`` normal
        NO crea los registros históricos. Usamos ``bulk_create_with_history``,
        registrando además al usuario que realizó la importación.
        """
        objetos = [self.model(**item) for item in data]
        creados = bulk_create_with_history(
            objetos,
            self.model,
            batch_size=self.batch_size,
            default_user=self.request.user,
        )
        return len(creados)


class ClientExampleExportView(BaseExampleExportView):
    validator_class = ClientImportValidator
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
