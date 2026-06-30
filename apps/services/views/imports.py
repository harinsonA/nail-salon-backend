from django.db import transaction
from django.urls import reverse_lazy
from simple_history.utils import bulk_create_with_history

from apps.common.imports.views import BaseImportView, BaseExampleExportView
from apps.services.imports import ServiceImportValidator, CategoryImportValidator
from apps.services.models.servicio import Servicio
from apps.services.models.categoria import Categoria


class ServiceImportView(BaseImportView):
    title = "Importación de servicios"
    validator_class = ServiceImportValidator
    model = Servicio
    view_url = reverse_lazy("service_import")
    example_export_url = reverse_lazy("service_example_export")
    success_url = reverse_lazy("services")

    @transaction.atomic
    def save(self, data: list) -> int:
        """Override: Servicio es auditado (simple_history) y ``bulk_create`` normal
        NO crea los registros históricos. Usamos ``bulk_create_with_history``,
        registrando además al usuario que realizó la importación (crítico para la
        auditoría de precios).
        """
        objetos = [self.model(**item) for item in data]
        creados = bulk_create_with_history(
            objetos,
            self.model,
            batch_size=self.batch_size,
            default_user=self.request.user,
        )
        return len(creados)


class ServiceExampleExportView(BaseExampleExportView):
    validator_class = ServiceImportValidator
    filename = "plantilla_servicios"
    example_rows = [
        [
            "Manicure Clásica",
            "1",
            "Esmaltado permanente con limado y cutícula",
            "15000",
            "30",
            "activo",
        ],
    ]


class CategoryImportView(BaseImportView):
    title = "Importación de categorías"
    validator_class = CategoryImportValidator
    model = Categoria
    view_url = reverse_lazy("category_import")
    example_export_url = reverse_lazy("category_example_export")
    success_url = reverse_lazy("categories")

    @transaction.atomic
    def save(self, data: list) -> int:
        """Override: Categoria es auditada (simple_history) y ``bulk_create`` normal
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


class CategoryExampleExportView(BaseExampleExportView):
    validator_class = CategoryImportValidator
    filename = "plantilla_categorias"
    example_rows = [
        [
            "Manicure",
            "Servicios de manicure y esmaltado",
            "activo",
        ],
    ]
