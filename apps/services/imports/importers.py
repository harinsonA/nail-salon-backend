from apps.common.imports.importers import BaseAsyncImporter
from apps.services.models.categoria import Categoria
from apps.services.models.servicio import Servicio

from .validators import CategoryAsyncImportValidator, ServiceAsyncImportValidator


class ServiceAsyncImporter(BaseAsyncImporter):
    """Importación masiva de servicios. El proceso vive en BaseAsyncImporter."""

    validator_class = ServiceAsyncImportValidator
    model = Servicio
    success_message = "{count} servicios importados correctamente."


class CategoryAsyncImporter(BaseAsyncImporter):
    """Importación masiva de categorías. El proceso vive en BaseAsyncImporter."""

    validator_class = CategoryAsyncImportValidator
    model = Categoria
    success_message = "{count} categorías importadas correctamente."
