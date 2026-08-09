from apps.clients.models.cliente import Cliente
from apps.common.imports.importers import BaseAsyncImporter

from .validators import ClientAsyncImportValidator


class ClientAsyncImporter(BaseAsyncImporter):
    """Importación masiva de clientes. El proceso completo vive en BaseAsyncImporter."""

    validator_class = ClientAsyncImportValidator
    model = Cliente
    success_message = "{count} clientes importados correctamente."
